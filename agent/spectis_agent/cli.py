"""Spectis CLI -- Typer application for the endpoint scanner agent."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from spectis_agent import __version__

app = typer.Typer(
    name="spectis-agent",
    help="Spectis Endpoint Scanner -- detect MCP servers, AI agent configs, and shadow agents.",
    no_args_is_help=True,
)
console = Console()


def _setup_logging(verbose: bool) -> None:
    """Configure root logger."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def _run_scan(
    orchestrator_url: str | None,
    api_key: str | None,
    output_dir: Path | None,
    approved_servers_path: Path | None,
    workspace_root: Path | None,
    workspace_depth: int,
    discover_tools: bool = False,
) -> list[dict]:
    """Execute all scanners, score findings, and report results."""
    from spectis_agent.platforms import get_mcp_configs
    from spectis_agent.reporters.file_reporter import save_report
    from spectis_agent.scanners.config_scanner import scan_all_configs
    from spectis_agent.scanners.network_scanner import scan_network_listeners
    from spectis_agent.scanners.process_scanner import scan_processes
    from spectis_agent.scanners.workspace_scanner import scan_workspace
    from spectis_agent.scoring import load_approved_servers, score_findings

    # Load approved server list
    approved = load_approved_servers(approved_servers_path)
    if approved:
        console.print(f"[dim]Loaded {len(approved)} approved server(s)[/dim]")

    all_findings: list[dict] = []

    # Phase 1: Config scan
    console.print("[bold]Phase 1:[/bold] Scanning AI client MCP configurations...")
    configs = get_mcp_configs()
    config_findings = scan_all_configs(configs)
    all_findings.extend(config_findings)
    console.print(f"  Found {len(config_findings)} server(s) in config files")

    # Phase 2: Workspace scan
    console.print("[bold]Phase 2:[/bold] Scanning workspace directories...")
    ws_findings = scan_workspace(root=workspace_root, max_depth=workspace_depth)
    all_findings.extend(ws_findings)
    console.print(f"  Found {len(ws_findings)} server(s) in workspace configs")

    # Phase 3: Process scan
    console.print("[bold]Phase 3:[/bold] Scanning running processes...")
    proc_findings = scan_processes()
    all_findings.extend(proc_findings)
    console.print(f"  Found {len(proc_findings)} MCP-related process(es)")

    # Phase 4: Network scan
    console.print("[bold]Phase 4:[/bold] Scanning network listeners...")
    net_findings = scan_network_listeners()
    all_findings.extend(net_findings)
    console.print(f"  Found {len(net_findings)} MCP network listener(s)")

    # Phase 5: Tool discovery (admin-controlled)
    if discover_tools:
        from spectis_agent.scanners.tool_prober import probe_all_servers

        console.print("[bold]Phase 5:[/bold] Discovering MCP server tools (admin-enabled)...")
        probe_results = probe_all_servers(config_findings)
        # Attach tools + probe status to their config findings
        total_tools = 0
        for f in config_findings:
            sname = f.get("server_name", "")
            if sname in probe_results:
                pr = probe_results[sname]
                f["tools"] = pr.tools
                f["probe_status"] = pr.status
                f["probe_reason"] = pr.reason
                total_tools += len(pr.tools)
            else:
                f["probe_status"] = "not_probed"
                f["probe_reason"] = "Server not probed"
        probed_ok = sum(1 for pr in probe_results.values() if pr.status == "discovered")
        console.print(f"  Discovered {total_tools} tool(s) across {probed_ok} server(s)")
    else:
        for f in config_findings:
            f["probe_status"] = "not_probed"
            f["probe_reason"] = "Tool discovery not enabled — run with --discover-tools"

    # Score
    console.print("[bold]Scoring findings...[/bold]")
    score_findings(all_findings, approved)

    # Display summary table
    _print_summary(all_findings)

    # File report (always)
    report_path = save_report(all_findings, output_dir)
    console.print(f"\n[dim]Report saved to {report_path}[/dim]")

    # API report (if orchestrator URL provided)
    if orchestrator_url:
        from spectis_agent.reporters.api_reporter import report_to_orchestrator

        console.print(f"[dim]Reporting to orchestrator at {orchestrator_url}...[/dim]")
        ok = report_to_orchestrator(all_findings, orchestrator_url, api_key)
        if ok:
            console.print("[green]Orchestrator accepted the report.[/green]")
        else:
            console.print("[yellow]Warning: could not reach orchestrator.[/yellow]")

    return all_findings


def _print_summary(findings: list[dict]) -> None:
    """Print a Rich table summarizing the scan findings."""
    if not findings:
        console.print("\n[green]No MCP findings detected.[/green]")
        return

    high = sum(1 for f in findings if f.get("risk_level") == "high")
    medium = sum(1 for f in findings if f.get("risk_level") == "medium")
    low = sum(1 for f in findings if f.get("risk_level") == "low")

    console.print(f"\n[bold]Total findings: {len(findings)}[/bold]  ", end="")
    console.print(f"[red]High: {high}[/red]  [yellow]Medium: {medium}[/yellow]  [green]Low: {low}[/green]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Scanner", style="cyan", width=10)
    table.add_column("Risk", width=8)
    table.add_column("Name / PID", width=20)
    table.add_column("Details", no_wrap=False)

    for f in findings:
        scanner = f.get("scanner", "?")
        risk = f.get("risk_level", "?")

        risk_style = {"high": "[red]", "medium": "[yellow]", "low": "[green]"}.get(risk, "")
        risk_display = f"{risk_style}{risk.upper()}[/{risk_style.strip('[')}]" if risk_style else risk

        if scanner == "config":
            name = f.get("server_name", "?")
            details = f"{f.get('client_name', '?')} | {f.get('transport', '?')} | {f.get('command_or_url', '')[:60]}"
        elif scanner == "process":
            name = str(f.get("pid", "?"))
            details = f"{f.get('name', '?')} | pattern: {f.get('matched_pattern', '?')}"
        elif scanner == "network":
            name = str(f.get("pid", "?"))
            details = f":{f.get('port', '?')} on {f.get('address', '?')} | {f.get('process_name', '?')}"
        else:
            name = f.get("server_name", str(f.get("pid", "?")))
            details = str(f)[:80]

        table.add_row(scanner, risk_display, name, details)

    console.print(table)


@app.command()
def scan(
    orchestrator_url: Annotated[
        Optional[str],
        typer.Option("--orchestrator-url", "-u", help="Orchestrator base URL (e.g. http://localhost:3000)"),
    ] = None,
    api_key: Annotated[
        Optional[str],
        typer.Option("--api-key", "-k", help="API key for orchestrator auth (Bearer aw_...)"),
    ] = None,
    output_dir: Annotated[
        Optional[Path],
        typer.Option("--output-dir", "-o", help="Directory for JSON report files"),
    ] = None,
    approved_servers: Annotated[
        Optional[Path],
        typer.Option("--approved-servers", "-a", help="Path to approved-servers.json"),
    ] = None,
    workspace_root: Annotated[
        Optional[Path],
        typer.Option("--workspace-root", "-w", help="Root directory for workspace scanning"),
    ] = None,
    workspace_depth: Annotated[
        int,
        typer.Option("--workspace-depth", help="Directory depth for workspace scanning"),
    ] = 3,
    discover_tools: Annotated[
        bool,
        typer.Option("--discover-tools", help="Probe MCP servers for tool lists (admin-controlled)"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable debug logging"),
    ] = False,
) -> None:
    """Run all scanners, score findings, and generate a report."""
    _setup_logging(verbose)
    console.print(f"[bold]Spectis Endpoint Scanner v{__version__}[/bold]\n")

    findings = _run_scan(
        orchestrator_url=orchestrator_url,
        api_key=api_key,
        output_dir=output_dir,
        approved_servers_path=approved_servers,
        workspace_root=workspace_root,
        workspace_depth=workspace_depth,
        discover_tools=discover_tools,
    )

    # Exit code reflects risk level
    if any(f.get("risk_level") == "high" for f in findings):
        raise typer.Exit(code=2)
    if any(f.get("risk_level") == "medium" for f in findings):
        raise typer.Exit(code=1)


@app.command()
def watch(
    interval: Annotated[
        int,
        typer.Option("--interval", "-i", help="Seconds between scans"),
    ] = 300,
    orchestrator_url: Annotated[
        Optional[str],
        typer.Option("--orchestrator-url", "-u", help="Orchestrator base URL"),
    ] = None,
    api_key: Annotated[
        Optional[str],
        typer.Option("--api-key", "-k", help="API key for orchestrator auth"),
    ] = None,
    output_dir: Annotated[
        Optional[Path],
        typer.Option("--output-dir", "-o", help="Directory for JSON report files"),
    ] = None,
    approved_servers: Annotated[
        Optional[Path],
        typer.Option("--approved-servers", "-a", help="Path to approved-servers.json"),
    ] = None,
    workspace_root: Annotated[
        Optional[Path],
        typer.Option("--workspace-root", "-w", help="Root directory for workspace scanning"),
    ] = None,
    workspace_depth: Annotated[
        int,
        typer.Option("--workspace-depth", help="Directory depth for workspace scanning"),
    ] = 3,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable debug logging"),
    ] = False,
) -> None:
    """Continuous monitoring mode -- run scans on a recurring interval."""
    _setup_logging(verbose)
    console.print(f"[bold]Spectis Endpoint Scanner v{__version__} -- Watch Mode[/bold]")
    console.print(f"Scanning every {interval} seconds. Press Ctrl+C to stop.\n")

    scan_count = 0
    try:
        while True:
            scan_count += 1
            console.rule(f"[bold]Scan #{scan_count}[/bold]")
            _run_scan(
                orchestrator_url=orchestrator_url,
                api_key=api_key,
                output_dir=output_dir,
                approved_servers_path=approved_servers,
                workspace_root=workspace_root,
                workspace_depth=workspace_depth,
            )
            console.print(f"\n[dim]Next scan in {interval}s...[/dim]\n")
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[bold]Watch mode stopped.[/bold]")
        raise typer.Exit(code=0)


@app.command()
def version() -> None:
    """Print the agent version."""
    console.print(f"spectis-agent v{__version__}")


if __name__ == "__main__":
    app()

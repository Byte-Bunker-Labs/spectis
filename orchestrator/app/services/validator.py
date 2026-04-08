"""Command validation service.

Validates PowerShell/CLI commands against agent permissions.
Fixes known issue #3: strips quoted strings before regex matching
to prevent false positives on strings like "=== ACTIVE Global Admins ===".
"""

import re

# Default blocked verbs — any cmdlet starting with these is denied
DEFAULT_BLOCKED_VERBS = [
    "Set-", "Remove-", "New-", "Add-", "Delete-", "Update-",
    "Disable-", "Enable-", "Grant-", "Revoke-", "Start-", "Stop-",
    "Clear-", "Reset-", "Invoke-",
]

# Regex to match PowerShell cmdlet pattern: Verb-Noun (e.g., Get-DlpCompliancePolicy)
CMDLET_PATTERN = re.compile(r"[A-Z][a-z]+-[A-Za-z]+")

# Pattern to strip quoted strings (single and double) before validation
QUOTED_STRING_PATTERN = re.compile(r"""(?:"[^"]*"|'[^']*')""")


def strip_quoted_strings(command: str) -> str:
    """Remove quoted string literals so their contents don't trigger cmdlet detection."""
    return QUOTED_STRING_PATTERN.sub("", command)


def extract_cmdlets(command: str) -> list[str]:
    """Extract cmdlet-like patterns from a command, ignoring quoted strings."""
    cleaned = strip_quoted_strings(command)
    return CMDLET_PATTERN.findall(cleaned)


def validate_command(
    command: str,
    allowed_commands: list[str] | None = None,
    blocked_verbs: list[str] | None = None,
) -> tuple[bool, str | None, list[str]]:
    """Validate a command against allowed commands and blocked verbs.

    Returns:
        (is_valid, blocked_reason, matched_blocked_verbs)
    """
    if blocked_verbs is None:
        blocked_verbs = DEFAULT_BLOCKED_VERBS

    cmdlets = extract_cmdlets(command)
    if not cmdlets:
        return True, None, []

    # Check for blocked verbs
    matched_blocked = []
    for cmdlet in cmdlets:
        for verb in blocked_verbs:
            if cmdlet.startswith(verb):
                matched_blocked.append(cmdlet)
                break

    if matched_blocked:
        return (
            False,
            f"Blocked verb(s) detected: {', '.join(matched_blocked)}",
            matched_blocked,
        )

    # If allowed_commands is set, enforce allowlist
    if allowed_commands:
        disallowed = [c for c in cmdlets if c not in allowed_commands]
        if disallowed:
            return (
                False,
                f"Command(s) not in allowlist: {', '.join(disallowed)}",
                disallowed,
            )

    return True, None, []

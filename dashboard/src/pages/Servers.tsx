import { useEffect, useState, useCallback } from 'react';
import { apiClient } from '../api/client';
import type { McpServer, McpTool } from '../types';

function Servers() {
  const [servers, setServers] = useState<McpServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchServers = useCallback(async () => {
    try {
      const data = await apiClient.getServers();
      setServers(data);
      setError('');
    } catch {
      setError('Failed to load MCP servers');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchServers();
  }, [fetchServers]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-ui-text-secondary">Loading servers...</div>
      </div>
    );
  }

  const withTools = servers.filter((s) => s.tool_count > 0);
  const totalTools = servers.reduce((sum, s) => sum + s.tool_count, 0);
  const localCount = servers.filter((s) => s.locality === 'local').length;
  const remoteCount = servers.filter((s) => s.locality === 'remote').length;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-2xl font-bold text-phthalo-deep">MCP Servers</h2>
        <p className="mt-1 text-sm text-ui-text-secondary">
          All discovered MCP servers, their tools, and which endpoints have them
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {/* Summary pills */}
      <div className="flex flex-wrap gap-3">
        <Pill label="Servers" value={servers.length} />
        <Pill label="With Tools" value={withTools.length} />
        <Pill label="Total Tools" value={totalTools} />
        <Pill label="Local" value={localCount} color="text-green-700" />
        <Pill label="Remote" value={remoteCount} color="text-red-700" />
      </div>

      {servers.length === 0 ? (
        <div className="flex h-48 items-center justify-center rounded-xl border border-ui-border bg-white">
          <p className="text-sm text-ui-text-secondary">No MCP servers discovered yet</p>
        </div>
      ) : (
        <div className="space-y-2">
          {servers.map((server) => (
            <ServerCard
              key={server.id}
              server={server}
              isExpanded={expandedId === server.id}
              onToggle={() => setExpandedId(expandedId === server.id ? null : server.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function Pill({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-ui-border bg-white px-3 py-1.5">
      <span className={`text-lg font-bold ${color ?? 'text-phthalo'}`}>{value}</span>
      <span className="text-xs text-ui-text-secondary">{label}</span>
    </div>
  );
}

function ServerCard({ server, isExpanded, onToggle }: { server: McpServer; isExpanded: boolean; onToggle: () => void }) {
  return (
    <div className="rounded-xl border border-ui-border bg-white overflow-hidden">
      {/* Header row */}
      <button onClick={onToggle} className="flex w-full items-center gap-3 px-5 py-3.5 text-left transition-colors hover:bg-phthalo-ghost">
        <svg className={`h-4 w-4 shrink-0 text-ui-text-tertiary transition-transform ${isExpanded ? 'rotate-90' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
        </svg>

        <span className="font-display text-sm font-semibold text-phthalo-deep">{server.server_name}</span>

        <span className="rounded bg-phthalo-wash px-1.5 py-0.5 text-[10px] text-phthalo">{server.runtime}</span>
        <span className="rounded bg-phthalo-wash px-1.5 py-0.5 text-[10px] text-phthalo">{server.transport}</span>
        {server.locality === 'remote' ? (
          <span className="rounded bg-red-50 px-1.5 py-0.5 text-[10px] font-medium text-red-700">REMOTE</span>
        ) : (
          <span className="rounded bg-green-50 px-1.5 py-0.5 text-[10px] text-green-700">local</span>
        )}
        {server.has_credentials && (
          <span className="rounded bg-red-50 px-1.5 py-0.5 text-[10px] text-red-700">CREDS</span>
        )}

        <span className="ml-auto flex items-center gap-3">
          <ProbeStatusBadge status={server.probe_status} />
          {server.tool_count > 0 && (
            <span className="font-display text-xs font-semibold text-phthalo-mid">{server.tool_count} tools</span>
          )}
          <span className="text-xs text-ui-text-tertiary">{server.endpoints_seen?.length ?? 0} endpoint(s)</span>
        </span>
      </button>

      {/* Expanded detail */}
      {isExpanded && (
        <div className="border-t border-ui-border">
          {/* Server info + deployment */}
          <div className="grid grid-cols-1 gap-6 p-5 lg:grid-cols-3">
            {/* Left: metadata */}
            <div className="space-y-3">
              <SectionLabel>Server Details</SectionLabel>
              <div className="space-y-1.5">
                {server.package && <MetaRow label="Package" value={server.package} />}
                {server.version && <MetaRow label="Version" value={server.version} />}
                {server.endpoint && <MetaRow label="Endpoint" value={server.endpoint} accent />}
                <MetaRow label="Runtime" value={server.runtime} />
                <MetaRow label="Transport" value={server.transport} />
                <MetaRow label="Locality" value={server.locality} />
              </div>

              {server.env_var_names.length > 0 && (
                <div>
                  <span className="text-[10px] text-ui-text-tertiary uppercase">Env vars</span>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {server.env_var_names.map((name) => (
                      <span key={name} className={`rounded px-1.5 py-0.5 font-mono text-[10px] ${
                        isCredName(name) ? 'bg-red-50 text-red-700' : 'bg-cream text-ui-text-secondary border border-ui-border'
                      }`}>{name}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Probe status reason */}
              {server.probe_reason && server.probe_status !== 'discovered' && (
                <div className="rounded-lg border border-yellow-200 bg-yellow-50 px-3 py-2 text-xs text-yellow-800">
                  {server.probe_reason}
                </div>
              )}
            </div>

            {/* Middle: who has it */}
            <div className="space-y-3">
              <SectionLabel>Deployed On</SectionLabel>
              <div className="space-y-2">
                {(server.endpoints_seen ?? []).map((ep) => (
                  <div key={ep} className="flex items-center gap-2 rounded-lg border border-ui-border bg-cream px-3 py-2">
                    <svg className="h-4 w-4 text-phthalo-mid" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25m18 0A2.25 2.25 0 0018.75 3H5.25A2.25 2.25 0 003 5.25m18 0V12" />
                    </svg>
                    <span className="text-xs text-ui-text">{ep}</span>
                  </div>
                ))}
              </div>

              <SectionLabel>AI Clients</SectionLabel>
              <div className="space-y-1.5">
                {(server.clients ?? []).map((c) => (
                  <div key={c} className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-phthalo-mid" />
                    <span className="text-xs text-ui-text">{c}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Right: tools */}
            <div className="space-y-3 lg:col-span-1">
              <SectionLabel>Tools ({server.tool_count})</SectionLabel>
              {server.tool_count > 0 ? (
                <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                  {server.tools.map((tool) => (
                    <ToolCard key={tool.name} tool={tool} />
                  ))}
                </div>
              ) : (
                <p className="text-xs text-ui-text-tertiary italic">
                  {server.probe_status === 'discovered'
                    ? 'Server reports no tools'
                    : server.probe_status === 'not_probed'
                    ? 'Run agent with --discover-tools'
                    : 'Unavailable — see probe status'}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ToolCard({ tool }: { tool: McpTool }) {
  const params = tool.input_schema?.properties
    ? Object.keys(tool.input_schema.properties as Record<string, unknown>)
    : [];
  const required = (tool.input_schema?.required ?? []) as string[];

  return (
    <div className="rounded-lg border border-ui-border bg-white p-2.5">
      <div className="font-display text-xs font-semibold text-phthalo-deep">{tool.name}</div>
      {tool.description && (
        <p className="mt-0.5 text-[11px] text-ui-text-secondary leading-relaxed">
          {tool.description.slice(0, 100)}{tool.description.length > 100 ? '...' : ''}
        </p>
      )}
      {params.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {params.map((p) => (
            <span key={p} className={`rounded px-1 py-0.5 font-mono text-[9px] ${
              required.includes(p)
                ? 'bg-phthalo-wash text-phthalo font-medium'
                : 'bg-cream text-ui-text-tertiary border border-ui-border'
            }`}>{p}{required.includes(p) ? '*' : ''}</span>
          ))}
        </div>
      )}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h4 className="font-display text-[10px] font-semibold uppercase tracking-widest text-phthalo-mid">
      {children}
    </h4>
  );
}

function ProbeStatusBadge({ status }: { status: string | null }) {
  if (!status) return null;
  const styles: Record<string, string> = {
    discovered: 'bg-green-50 text-green-700',
    skipped_http: 'bg-yellow-50 text-yellow-700',
    skipped_docker: 'bg-yellow-50 text-yellow-700',
    failed_timeout: 'bg-orange-50 text-orange-700',
    failed_auth: 'bg-red-50 text-red-700',
    failed_error: 'bg-red-50 text-red-700',
    not_probed: 'bg-gray-100 text-gray-500',
  };
  const labels: Record<string, string> = {
    discovered: 'probed',
    skipped_http: 'needs auth',
    skipped_docker: 'docker',
    failed_timeout: 'timeout',
    failed_auth: 'needs creds',
    failed_error: 'error',
    not_probed: 'not probed',
  };
  return (
    <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${styles[status] || styles.not_probed}`}>
      {labels[status] || status}
    </span>
  );
}

function MetaRow({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-ui-text-tertiary w-16 shrink-0">{label}</span>
      <span className={`font-mono text-xs ${accent ? 'text-phthalo-mid' : 'text-ui-text'}`}>{value}</span>
    </div>
  );
}

function isCredName(name: string): boolean {
  const lower = name.toLowerCase();
  return ['token', 'secret', 'key', 'password', 'credential', 'bearer', 'auth'].some(
    (kw) => lower.includes(kw)
  );
}

export default Servers;

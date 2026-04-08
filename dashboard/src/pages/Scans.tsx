import { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { ScanResult, ScanResultDetail } from '../types';

type FindingTab = 'configured' | 'running';

function Scans() {
  const [searchParams] = useSearchParams();
  const tabParam = searchParams.get('tab');

  const [scans, setScans] = useState<ScanResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedScan, setExpandedScan] = useState<ScanResultDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [activeTab, setActiveTab] = useState<FindingTab>(
    tabParam === 'running' ? 'running' : 'configured'
  );
  const [autoExpanded, setAutoExpanded] = useState(false);

  const fetchScans = useCallback(async () => {
    try {
      const data = await apiClient.getScans();
      setScans(data);
      setError('');
    } catch {
      setError('Failed to load scan results');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScans();
  }, [fetchScans]);

  // Auto-expand first scan when navigated from Overview with ?tab=
  useEffect(() => {
    if (tabParam && scans.length > 0 && !autoExpanded) {
      setAutoExpanded(true);
      handleExpand(scans[0]);
    }
  }, [tabParam, scans, autoExpanded]);

  const handleExpand = async (scan: ScanResult) => {
    if (expandedScan?.id === scan.id) {
      setExpandedScan(null);
      return;
    }
    setLoadingDetail(true);
    try {
      const detail = await apiClient.getScanDetail(scan.id);
      setExpandedScan(detail);
    } catch {
      setError('Failed to load scan details');
    } finally {
      setLoadingDetail(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-ui-text-secondary">Loading scan results...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-2xl font-bold text-phthalo-deep">Scan Results</h2>
        <p className="mt-1 text-sm text-ui-text-secondary">
          Endpoint MCP configuration scans — click a row to view discovered servers
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {scans.length === 0 ? (
        <div className="flex h-48 items-center justify-center rounded-xl border border-ui-border bg-white">
          <div className="text-center">
            <p className="text-sm text-ui-text-secondary">No scan results yet</p>
            <p className="mt-2 text-xs text-ui-text-tertiary">Run the endpoint agent:</p>
            <code className="mt-1 block text-xs text-phthalo-mid">
              spectis-agent scan --orchestrator-url http://localhost:8000
            </code>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {scans.map((scan) => (
            <div key={scan.id} className="rounded-xl border border-ui-border bg-white">
              {/* Summary row */}
              <button
                onClick={() => handleExpand(scan)}
                className="flex w-full items-center justify-between px-5 py-4 text-left transition-colors hover:bg-phthalo-ghost"
              >
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-lg font-medium text-ui-text">{scan.hostname}</span>
                  <span className="rounded bg-cream px-2 py-0.5 text-xs text-ui-text-secondary border border-ui-border">
                    {scan.os_platform}
                  </span>
                  {scan.username && (
                    <span className="text-sm text-ui-text-secondary">{scan.username}</span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <span className="rounded bg-phthalo-wash px-2 py-0.5 text-xs text-phthalo">
                    {scan.config_count ?? '?'} configured
                  </span>
                  <span className="rounded bg-phthalo-ghost px-2 py-0.5 text-xs text-phthalo-mid">
                    {scan.process_count ?? '?'} running
                  </span>
                  {scan.high_risk_count > 0 && (
                    <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
                      {scan.high_risk_count} high
                    </span>
                  )}
                  {scan.medium_risk_count > 0 && (
                    <span className="rounded-full bg-yellow-50 px-2 py-0.5 text-xs font-medium text-yellow-700">
                      {scan.medium_risk_count} med
                    </span>
                  )}
                  <span className="text-xs text-ui-text-tertiary">
                    {new Date(scan.scanned_at).toLocaleString()}
                  </span>
                  <svg
                    className={`h-5 w-5 text-ui-text-tertiary transition-transform ${expandedScan?.id === scan.id ? 'rotate-180' : ''}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                  </svg>
                </div>
              </button>

              {/* Expanded detail with tabs */}
              {expandedScan?.id === scan.id && (
                <div className="border-t border-ui-border">
                  {loadingDetail ? (
                    <div className="px-5 py-5">
                      <p className="text-sm text-ui-text-secondary">Loading details...</p>
                    </div>
                  ) : (
                    <>
                      {/* Tabs */}
                      <div className="flex border-b border-ui-border">
                        <button
                          onClick={(e) => { e.stopPropagation(); setActiveTab('configured'); }}
                          className={`px-5 py-3 text-sm font-medium transition-colors ${
                            activeTab === 'configured'
                              ? 'border-b-2 border-phthalo text-phthalo'
                              : 'text-ui-text-secondary hover:text-ui-text'
                          }`}
                        >
                          Configured Servers ({expandedScan.config_findings.length})
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); setActiveTab('running'); }}
                          className={`px-5 py-3 text-sm font-medium transition-colors ${
                            activeTab === 'running'
                              ? 'border-b-2 border-phthalo text-phthalo'
                              : 'text-ui-text-secondary hover:text-ui-text'
                          }`}
                        >
                          Running Processes ({expandedScan.process_findings.length})
                        </button>
                      </div>

                      {/* Tab content */}
                      <div className="px-5 py-5 space-y-3">
                        {activeTab === 'configured' && (
                          <>
                            {expandedScan.config_findings.length === 0 ? (
                              <p className="text-sm text-ui-text-secondary">No configured MCP servers found</p>
                            ) : (
                              expandedScan.config_findings.map((f, i) => (
                                <ConfigFindingCard key={i} finding={f} />
                              ))
                            )}
                            {expandedScan.workspace_findings.length > 0 && (
                              <div className="mt-4">
                                <h4 className="font-display text-xs font-semibold uppercase tracking-widest text-phthalo-mid mb-2">
                                  Workspace Configs ({expandedScan.workspace_findings.length})
                                </h4>
                                {expandedScan.workspace_findings.map((f, i) => (
                                  <ConfigFindingCard key={`ws-${i}`} finding={f} />
                                ))}
                              </div>
                            )}
                          </>
                        )}

                        {activeTab === 'running' && (
                          <>
                            {expandedScan.process_findings.length === 0 ? (
                              <p className="text-sm text-ui-text-secondary">No running MCP processes found</p>
                            ) : (
                              expandedScan.process_findings.map((f, i) => (
                                <ProcessFindingCard key={i} finding={f} />
                              ))
                            )}
                            {expandedScan.network_findings.length > 0 && (
                              <div className="mt-4">
                                <h4 className="font-display text-xs font-semibold uppercase tracking-widest text-phthalo-mid mb-2">
                                  Network Listeners ({expandedScan.network_findings.length})
                                </h4>
                                {expandedScan.network_findings.map((f, i) => (
                                  <GenericFindingCard key={`net-${i}`} finding={f} />
                                ))}
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


function RiskBorder({ level }: { level: string }) {
  const colors: Record<string, string> = {
    high: 'border-l-red-500',
    medium: 'border-l-yellow-500',
    low: 'border-l-green-500',
  };
  return <span className={`absolute inset-y-0 left-0 w-1 rounded-l ${colors[level] || 'border-l-gray-500'}`} />;
}

function RiskBadge({ level }: { level: string }) {
  const styles: Record<string, string> = {
    high: 'bg-red-50 text-red-700',
    medium: 'bg-yellow-50 text-yellow-700',
    low: 'bg-green-50 text-green-700',
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[level] || 'bg-gray-100 text-gray-500'}`}>
      {level}
    </span>
  );
}

function ConfigFindingCard({ finding }: { finding: Record<string, unknown> }) {
  const serverName = String(finding.server_name ?? 'unknown');
  const clientName = String(finding.client_name ?? '');
  const transport = String(finding.transport ?? '');
  const runtime = String(finding.runtime ?? '');
  const locality = String(finding.locality ?? 'local');
  const packageName = String(finding.package ?? '');
  const version = finding.version ? String(finding.version) : null;
  const endpoint = finding.endpoint ? String(finding.endpoint) : null;
  const risk = String(finding.risk_level ?? 'low');
  const envVarNames = (finding.env_var_names ?? []) as string[];
  const hasCreds = Boolean(finding.has_credentials);

  const isCredName = (name: string) => {
    const lower = name.toLowerCase();
    return ['token', 'secret', 'key', 'password', 'credential', 'bearer', 'auth'].some(
      (kw) => lower.includes(kw)
    );
  };

  return (
    <div className="relative rounded-lg border border-ui-border bg-phthalo-ghost pl-4 pr-4 py-4 overflow-hidden">
      <RiskBorder level={risk} />

      {/* Header: server name + badges */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span className="text-base font-semibold text-ui-text">{serverName}</span>
        <RiskBadge level={risk} />
        <span className="rounded bg-cream px-2 py-0.5 text-xs text-ui-text-secondary border border-ui-border">{clientName}</span>
        <span className="rounded bg-phthalo-wash px-2 py-0.5 text-xs text-phthalo">{transport}</span>
        {runtime === 'docker' && (
          <span className="rounded bg-phthalo-wash px-2 py-0.5 text-xs text-phthalo">docker</span>
        )}
        {locality === 'remote' ? (
          <span className="rounded bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">REMOTE</span>
        ) : (
          <span className="rounded bg-green-50 px-2 py-0.5 text-xs text-green-700">local</span>
        )}
        {hasCreds && (
          <span className="rounded bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
            CREDENTIALS
          </span>
        )}
      </div>

      {/* Package + Version + Endpoint */}
      <div className="space-y-1.5 mb-2">
        {packageName && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-ui-text-tertiary w-16 shrink-0">Package</span>
            <span className="font-mono text-xs text-ui-text">{packageName}</span>
            {version && <span className="text-xs text-ui-text-tertiary">v{version}</span>}
          </div>
        )}
        {endpoint && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-ui-text-tertiary w-16 shrink-0">Endpoint</span>
            <span className="font-mono text-xs text-phthalo-mid">{endpoint}</span>
          </div>
        )}
      </div>

      {/* Env var names */}
      {envVarNames.length > 0 && (
        <div>
          <span className="text-xs text-ui-text-tertiary">Env vars (names only):</span>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {envVarNames.map((name) => (
              <span
                key={name}
                className={`rounded px-2 py-0.5 font-mono text-xs ${
                  isCredName(name)
                    ? 'bg-red-50 text-red-700'
                    : 'bg-cream text-ui-text-secondary border border-ui-border'
                }`}
              >
                {name}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ProcessFindingCard({ finding }: { finding: Record<string, unknown> }) {
  const serverName = String(finding.server_name ?? 'unknown');
  const processName = String(finding.process_name ?? '');
  const pid = String(finding.pid ?? '');
  const endpoint = finding.endpoint ? String(finding.endpoint) : null;
  const hasCreds = Boolean(finding.has_credentials);
  const risk = String(finding.risk_level ?? 'low');

  return (
    <div className="relative rounded-lg border border-ui-border bg-phthalo-ghost pl-4 pr-4 py-3 overflow-hidden">
      <RiskBorder level={risk} />
      <div className="flex flex-wrap items-center gap-2 mb-1">
        <span className="font-medium text-ui-text">{serverName}</span>
        <RiskBadge level={risk} />
        <span className="rounded bg-cream px-2 py-0.5 text-xs text-ui-text-secondary border border-ui-border">{processName}</span>
        <span className="rounded bg-cream px-2 py-0.5 text-xs text-ui-text-secondary border border-ui-border">PID {pid}</span>
        {hasCreds && (
          <span className="rounded bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
            CREDENTIALS IN ARGS
          </span>
        )}
      </div>
      {endpoint && (
        <p className="font-mono text-xs text-phthalo-mid mt-1">{endpoint}</p>
      )}
    </div>
  );
}

function GenericFindingCard({ finding }: { finding: Record<string, unknown> }) {
  const risk = String(finding.risk_level ?? 'low');
  return (
    <div className="relative rounded-lg border border-ui-border bg-phthalo-ghost pl-4 pr-4 py-3 overflow-hidden">
      <RiskBorder level={risk} />
      <pre className="text-xs text-ui-text-secondary whitespace-pre-wrap break-all">
        {JSON.stringify(finding, null, 2)}
      </pre>
    </div>
  );
}

export default Scans;

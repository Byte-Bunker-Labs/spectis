import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { Stats, AuditLogEntry, ScanResult } from '../types';

const REFRESH_INTERVAL = 30_000;

function Overview() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [scans, setScans] = useState<ScanResult[]>([]);
  const [recentActivity, setRecentActivity] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    try {
      const [statsData, historyData, scanData] = await Promise.all([
        apiClient.getStats(),
        apiClient.getHistory({ limit: 10 }),
        apiClient.getScans(),
      ]);
      setStats(statsData);
      setRecentActivity(historyData);
      setScans(scanData);
      setError('');
    } catch {
      setError('Failed to load dashboard stats');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-ui-text-secondary">Loading dashboard...</div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-red-700">{error || 'No data available'}</div>
      </div>
    );
  }

  // Endpoint summary from scans
  const totalEndpoints = new Set(scans.map((s) => s.hostname)).size;
  const uniqueServers = new Set(scans.flatMap((s) => s.unique_server_names ?? [])).size;
  const configEntries = scans.reduce((sum, s) => sum + (s.config_count ?? 0), 0);
  const runningProcesses = scans.reduce((sum, s) => sum + (s.process_count ?? 0), 0);
  const localServers = scans.reduce((sum, s) => sum + (s.local_count ?? 0), 0);
  const remoteServers = scans.reduce((sum, s) => sum + (s.remote_count ?? 0), 0);
  const dockerServers = scans.reduce((sum, s) => sum + (s.docker_count ?? 0), 0);
  const totalHighRisk = scans.reduce((sum, s) => sum + s.high_risk_count, 0);
  const allClients = [...new Set(scans.flatMap((s) => s.clients_detected ?? []))];

  const riskHigh = stats.risk_breakdown?.high ?? 0;
  const riskMedium = stats.risk_breakdown?.medium ?? 0;
  const riskLow = stats.risk_breakdown?.low ?? 0;
  const riskTotal = riskHigh + riskMedium + riskLow || 1;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-2xl font-bold text-phthalo-deep">Overview</h2>
        <p className="mt-1 text-sm text-ui-text-secondary">
          Platform-wide AI agent and endpoint observability
        </p>
      </div>

      {/* Endpoint Discovery Summary */}
      <div>
        <h3 className="font-display mb-3 text-xs font-semibold uppercase tracking-widest text-phthalo-mid">
          MCP Server Discovery
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Endpoints Scanned" value={totalEndpoints} color="text-phthalo-mid" onClick={() => navigate('/scans')} />
          <StatCard label="Unique MCP Servers" value={uniqueServers} color="text-phthalo-light" onClick={() => navigate('/scans?tab=configured')} />
          <StatCard label="Running MCP Processes" value={runningProcesses} color="text-phthalo-mid" onClick={() => navigate('/scans?tab=running')} />
          <StatCard label="High Risk" value={totalHighRisk} color="text-red-700" onClick={() => navigate('/scans')} />
        </div>
      </div>

      {/* Locality + Runtime + Clients */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Local vs Remote */}
        <div className="rounded-xl border border-ui-border bg-white p-5">
          <h3 className="font-display mb-4 text-lg font-semibold text-phthalo-deep">
            Data Exfiltration Risk
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full bg-green-500" />
                <span className="text-sm text-ui-text-secondary">Local (Docker / stdio)</span>
              </div>
              <span className="text-2xl font-bold text-green-700">{localServers}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full bg-red-500" />
                <span className="text-sm text-ui-text-secondary">Remote (external endpoints)</span>
              </div>
              <span className="text-2xl font-bold text-red-700">{remoteServers}</span>
            </div>
            {remoteServers > 0 && (
              <p className="mt-2 text-xs text-red-600">
                Remote MCP servers connect to external endpoints — potential data exfiltration vector
              </p>
            )}
          </div>
        </div>

        {/* Runtime breakdown */}
        <div className="rounded-xl border border-ui-border bg-white p-5">
          <h3 className="font-display mb-4 text-lg font-semibold text-phthalo-deep">Runtime</h3>
          <div className="space-y-3">
            <RuntimeRow label="Docker containers" count={dockerServers} color="text-phthalo-mid" />
            <RuntimeRow label="NPX / UVX packages" count={uniqueServers - dockerServers} color="text-yellow-700" />
            <RuntimeRow label="Config entries (across clients)" count={configEntries} color="text-ui-text-secondary" />
          </div>
        </div>

        {/* AI Clients detected */}
        <div className="rounded-xl border border-ui-border bg-white p-5">
          <h3 className="font-display mb-4 text-lg font-semibold text-phthalo-deep">AI Clients</h3>
          {allClients.length === 0 ? (
            <p className="text-sm text-ui-text-secondary">No clients detected</p>
          ) : (
            <div className="space-y-2">
              {allClients.map((client) => (
                <div key={client} className="flex items-center gap-2 rounded-lg bg-phthalo-ghost px-4 py-2.5">
                  <span className="h-2 w-2 rounded-full bg-green-500" />
                  <span className="text-sm text-ui-text">{client}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Orchestrator Activity */}
      <div>
        <h3 className="font-display mb-3 text-xs font-semibold uppercase tracking-widest text-phthalo-mid">
          Orchestrator Activity
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Total Events" value={stats.total_events} color="text-phthalo-mid" onClick={() => navigate('/feed')} />
          <StatCard label="Events Today" value={stats.events_today} color="text-phthalo-light" onClick={() => navigate('/feed')} />
          <StatCard label="Blocked Commands" value={stats.blocked_commands} color="text-red-700" onClick={() => navigate('/feed')} />
          <StatCard label="Registered Agents" value={stats.active_agents} color="text-phthalo" onClick={() => navigate('/agents')} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Risk breakdown */}
        <div className="rounded-xl border border-ui-border bg-white p-5">
          <h3 className="font-display mb-4 text-lg font-semibold text-phthalo-deep">Risk Breakdown</h3>
          <div className="space-y-4">
            <RiskBar label="High" count={riskHigh} total={riskTotal} color="bg-red-500" />
            <RiskBar label="Medium" count={riskMedium} total={riskTotal} color="bg-yellow-500" />
            <RiskBar label="Low" count={riskLow} total={riskTotal} color="bg-green-500" />
          </div>
        </div>

        {/* Scanned endpoints */}
        <div className="rounded-xl border border-ui-border bg-white p-5">
          <h3 className="font-display mb-4 text-lg font-semibold text-phthalo-deep">Scanned Endpoints</h3>
          {scans.length === 0 ? (
            <p className="text-sm text-ui-text-secondary">No endpoints scanned yet</p>
          ) : (
            <div className="space-y-2">
              {scans.slice(0, 5).map((scan) => (
                <div
                  key={scan.id}
                  className="flex items-center justify-between rounded-lg bg-phthalo-ghost px-4 py-2.5"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-ui-text">{scan.hostname}</span>
                    <span className="rounded bg-phthalo-wash px-1.5 py-0.5 text-[10px] text-ui-text-tertiary">
                      {scan.os_platform}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {scan.high_risk_count > 0 && (
                      <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-700">
                        {scan.high_risk_count} high
                      </span>
                    )}
                    {scan.medium_risk_count > 0 && (
                      <span className="rounded-full bg-yellow-50 px-2 py-0.5 text-xs text-yellow-700">
                        {scan.medium_risk_count} med
                      </span>
                    )}
                    <span className="text-xs text-ui-text-tertiary">
                      {scan.total_findings} total
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Top Agents + Recent Activity side by side */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Top agents */}
        <div className="rounded-xl border border-ui-border bg-white p-5">
          <h3 className="font-display mb-4 text-lg font-semibold text-phthalo-deep">Top Agents</h3>
          {stats.top_agents.length === 0 ? (
            <p className="text-sm text-ui-text-secondary">No agent activity yet</p>
          ) : (
            <div className="space-y-2">
              {stats.top_agents.map((agent, i) => (
                <div
                  key={agent.name}
                  className="flex items-center justify-between rounded-lg bg-phthalo-ghost px-4 py-2.5"
                >
                  <span className="text-sm text-ui-text">
                    <span className="mr-2 text-ui-text-tertiary">{i + 1}.</span>
                    {agent.name}
                  </span>
                  <span className="text-sm font-medium text-phthalo-mid">
                    {agent.event_count.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent activity */}
        <div className="rounded-xl border border-ui-border bg-white p-5">
          <h3 className="font-display mb-4 text-lg font-semibold text-phthalo-deep">Recent Activity</h3>
          {recentActivity.length === 0 ? (
            <p className="text-sm text-ui-text-secondary">No recent activity</p>
          ) : (
            <div className="space-y-2">
              {recentActivity.slice(0, 8).map((entry) => (
                <div
                  key={entry.id}
                  className="flex items-center justify-between rounded-lg bg-phthalo-ghost px-4 py-2"
                >
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-mono text-xs text-phthalo-mid">{entry.action}</span>
                    <span className="text-ui-text-secondary">{entry.agent_name ?? entry.username ?? '—'}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={entry.status} />
                    <span className="text-[10px] text-ui-text-tertiary">
                      {new Date(entry.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function RuntimeRow({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-ui-text-secondary">{label}</span>
      <span className={`text-2xl font-bold ${color}`}>{count}</span>
    </div>
  );
}

function StatCard({ label, value, color, onClick }: { label: string; value: number; color: string; onClick?: () => void }) {
  return (
    <div
      onClick={onClick}
      className={`rounded-xl border border-ui-border bg-white p-5 transition-colors ${onClick ? 'cursor-pointer hover:border-phthalo-mid hover:bg-phthalo-ghost' : ''}`}
    >
      <p className="text-sm font-medium text-ui-text-secondary">{label}</p>
      <p className={`mt-2 text-3xl font-bold ${color}`}>{value.toLocaleString()}</p>
    </div>
  );
}

function RiskBar({ label, count, total, color }: { label: string; count: number; total: number; color: string }) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="text-ui-text-secondary">{label}</span>
        <span className="text-ui-text-tertiary">{count.toLocaleString()}</span>
      </div>
      <div className="h-2.5 w-full rounded-full bg-phthalo-wash">
        <div className={`h-2.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    success: 'bg-green-50 text-green-700',
    blocked: 'bg-red-50 text-red-700',
    queued: 'bg-yellow-50 text-yellow-700',
    error: 'bg-red-50 text-red-700',
  };
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status] || 'bg-phthalo-wash text-ui-text-tertiary'}`}>
      {status}
    </span>
  );
}

export default Overview;

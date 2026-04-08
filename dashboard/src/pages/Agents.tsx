import { useEffect, useState, useCallback, FormEvent } from 'react';
import { apiClient } from '../api/client';
import type { Agent } from '../types';

function Agents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);

  const fetchAgents = useCallback(async () => {
    try {
      const data = await apiClient.getAgents();
      setAgents(data);
      setError('');
    } catch {
      setError('Failed to load agents');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const handleStatusChange = async (id: string, status: string) => {
    try {
      await apiClient.updateAgent(id, { status });
      await fetchAgents();
      setSelectedAgent(null);
    } catch {
      setError('Failed to update agent status');
    }
  };

  const handleCreate = async (data: Record<string, unknown>) => {
    try {
      await apiClient.createAgent(data);
      await fetchAgents();
      setShowForm(false);
    } catch {
      setError('Failed to register agent');
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-ui-text-secondary">Loading agents...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-display text-2xl font-bold text-phthalo-deep">Agent Registry</h2>
          <p className="mt-1 text-sm text-ui-text-secondary">
            Manage registered AI agents and their approval status
          </p>
        </div>
        <button
          onClick={() => { setShowForm(true); setSelectedAgent(null); }}
          className="rounded-lg bg-phthalo px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-phthalo-deep"
        >
          Register Agent
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {showForm && (
        <AgentFormModal onClose={() => setShowForm(false)} onSubmit={handleCreate} />
      )}

      {selectedAgent && (
        <AgentDetailModal
          agent={selectedAgent}
          onClose={() => setSelectedAgent(null)}
          onStatusChange={handleStatusChange}
        />
      )}

      {agents.length === 0 ? (
        <div className="flex h-48 items-center justify-center rounded-xl border border-ui-border bg-white">
          <p className="text-sm text-ui-text-secondary">No agents registered</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-ui-border bg-white">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-ui-border text-ui-text-secondary">
                <th className="px-5 py-3 font-medium">Name</th>
                <th className="px-5 py-3 font-medium">Type</th>
                <th className="px-5 py-3 font-medium">Owner</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Version</th>
                <th className="px-5 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ui-border">
              {agents.map((agent) => (
                <tr
                  key={agent.id}
                  onClick={() => setSelectedAgent(agent)}
                  className="cursor-pointer text-ui-text-secondary transition-colors hover:bg-phthalo-ghost"
                >
                  <td className="px-5 py-3 font-medium text-ui-text">{agent.name}</td>
                  <td className="px-5 py-3">{agent.agent_type}</td>
                  <td className="px-5 py-3">{agent.owner}</td>
                  <td className="px-5 py-3"><AgentStatusBadge status={agent.status} /></td>
                  <td className="px-5 py-3 font-mono text-xs text-phthalo-mid">{agent.version}</td>
                  <td className="px-5 py-3 text-ui-text-tertiary">
                    {new Date(agent.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function AgentStatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    approved: 'bg-green-50 text-green-700',
    pending_review: 'bg-yellow-50 text-yellow-700',
    blocked: 'bg-red-50 text-red-700',
    retired: 'bg-gray-100 text-gray-500',
  };
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status] || styles.retired}`}>
      {status.replace('_', ' ')}
    </span>
  );
}

function AgentDetailModal({
  agent, onClose, onStatusChange,
}: {
  agent: Agent;
  onClose: () => void;
  onStatusChange: (id: string, status: string) => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-xl border border-ui-border bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-ui-border px-6 py-4">
          <h3 className="font-display text-lg font-semibold text-phthalo-deep">{agent.name}</h3>
          <button onClick={onClose} className="text-ui-text-tertiary hover:text-ui-text">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-4 px-6 py-4">
          <DetailRow label="ID" value={agent.id} />
          <DetailRow label="Type" value={agent.agent_type} />
          <DetailRow label="Owner" value={agent.owner} />
          <DetailRow label="Version" value={agent.version} />
          <DetailRow label="Description" value={agent.description || '—'} />
          <DetailRow label="Status" value={<AgentStatusBadge status={agent.status} />} />
          <DetailRow
            label="Allowed Cmds"
            value={agent.allowed_commands.length > 0 ? agent.allowed_commands.join(', ') : 'None'}
          />
          <DetailRow
            label="Blocked Verbs"
            value={agent.blocked_verbs.length > 0 ? agent.blocked_verbs.join(', ') : 'None'}
          />
          <DetailRow label="Created" value={new Date(agent.created_at).toLocaleString()} />
          <DetailRow label="Updated" value={new Date(agent.updated_at).toLocaleString()} />
        </div>

        <div className="flex justify-end gap-3 border-t border-ui-border px-6 py-4">
          {agent.status !== 'approved' && (
            <button onClick={() => onStatusChange(agent.id, 'approved')}
              className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-700">
              Approve
            </button>
          )}
          {agent.status !== 'blocked' && (
            <button onClick={() => onStatusChange(agent.id, 'blocked')}
              className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700">
              Block
            </button>
          )}
          {agent.status !== 'retired' && (
            <button onClick={() => onStatusChange(agent.id, 'retired')}
              className="rounded-lg border border-ui-border bg-cream px-4 py-2 text-sm font-medium text-ui-text-secondary transition-colors hover:bg-phthalo-ghost">
              Retire
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:gap-4">
      <span className="w-28 shrink-0 text-sm font-medium text-ui-text-secondary">{label}</span>
      <span className="text-sm text-ui-text break-all">{value}</span>
    </div>
  );
}

function AgentFormModal({
  onClose, onSubmit,
}: {
  onClose: () => void;
  onSubmit: (data: Record<string, unknown>) => void;
}) {
  const [name, setName] = useState('');
  const [agentType, setAgentType] = useState('');
  const [owner, setOwner] = useState('');
  const [version, setVersion] = useState('1.0.0');
  const [description, setDescription] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit({ name, agent_type: agentType, owner, version, description });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-xl border border-ui-border bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-ui-border px-6 py-4">
          <h3 className="font-display text-lg font-semibold text-phthalo-deep">Register Agent</h3>
          <button onClick={onClose} className="text-ui-text-tertiary hover:text-ui-text">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-4">
          <FormField label="Name" required>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} required
              className="w-full rounded-lg border border-ui-border bg-cream px-3 py-2 text-sm text-ui-text placeholder-ui-text-tertiary outline-none focus:border-phthalo-mid focus:ring-1 focus:ring-phthalo-mid"
              placeholder="e.g. dlp-agent" />
          </FormField>
          <FormField label="Type" required>
            <select value={agentType} onChange={(e) => setAgentType(e.target.value)} required
              className="w-full rounded-lg border border-ui-border bg-cream px-3 py-2 text-sm text-ui-text outline-none focus:border-phthalo-mid focus:ring-1 focus:ring-phthalo-mid">
              <option value="">Select type</option>
              <option value="dlp">DLP</option>
              <option value="entra">Entra ID</option>
              <option value="security">Security</option>
              <option value="custom">Custom</option>
            </select>
          </FormField>
          <FormField label="Owner" required>
            <input type="text" value={owner} onChange={(e) => setOwner(e.target.value)} required
              className="w-full rounded-lg border border-ui-border bg-cream px-3 py-2 text-sm text-ui-text placeholder-ui-text-tertiary outline-none focus:border-phthalo-mid focus:ring-1 focus:ring-phthalo-mid"
              placeholder="e.g. security-team@company.com" />
          </FormField>
          <FormField label="Version">
            <input type="text" value={version} onChange={(e) => setVersion(e.target.value)}
              className="w-full rounded-lg border border-ui-border bg-cream px-3 py-2 text-sm text-ui-text placeholder-ui-text-tertiary outline-none focus:border-phthalo-mid focus:ring-1 focus:ring-phthalo-mid" />
          </FormField>
          <FormField label="Description">
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3}
              className="w-full rounded-lg border border-ui-border bg-cream px-3 py-2 text-sm text-ui-text placeholder-ui-text-tertiary outline-none focus:border-phthalo-mid focus:ring-1 focus:ring-phthalo-mid"
              placeholder="Describe the agent's purpose" />
          </FormField>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="rounded-lg border border-phthalo text-phthalo px-4 py-2 text-sm font-medium transition-colors hover:bg-phthalo-wash">
              Cancel
            </button>
            <button type="submit"
              className="rounded-lg bg-phthalo px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-phthalo-deep">
              Register
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function FormField({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-ui-text">
        {label}{required && <span className="ml-1 text-red-500">*</span>}
      </label>
      {children}
    </div>
  );
}

export default Agents;

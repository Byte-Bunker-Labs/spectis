import { useState, useMemo } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import type { AuditLogEntry } from '../types';

function LiveFeed() {
  const { events, connected, clearEvents } = useWebSocket();
  const [actionFilter, setActionFilter] = useState('');
  const [agentFilter, setAgentFilter] = useState('');

  // Derive unique values for filter dropdowns
  const actionTypes = useMemo(() => {
    const set = new Set(events.map((e) => e.action));
    return Array.from(set).sort();
  }, [events]);

  const agentNames = useMemo(() => {
    const set = new Set(events.map((e) => e.agent_name));
    return Array.from(set).sort();
  }, [events]);

  // Apply filters
  const filtered = useMemo(() => {
    return events.filter((e) => {
      if (actionFilter && e.action !== actionFilter) return false;
      if (agentFilter && e.agent_name !== agentFilter) return false;
      return true;
    });
  }, [events, actionFilter, agentFilter]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-display text-2xl font-bold text-phthalo-deep">Live Feed</h2>
          <p className="mt-1 text-sm text-ui-text-secondary">
            Real-time agent activity stream
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`flex items-center gap-2 text-sm ${
              connected ? 'text-green-700' : 'text-red-700'
            }`}
          >
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                connected ? 'bg-green-500' : 'bg-red-500'
              }`}
            />
            {connected ? 'Connected' : 'Disconnected'}
          </span>
          <button
            onClick={clearEvents}
            className="rounded-lg border border-ui-border bg-white px-3 py-1.5 text-sm text-ui-text-secondary transition-colors hover:border-phthalo-mid hover:bg-phthalo-ghost"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="rounded-lg border border-ui-border bg-white px-3 py-2 text-sm text-ui-text outline-none focus:border-phthalo-mid"
        >
          <option value="">All Actions</option>
          {actionTypes.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>

        <select
          value={agentFilter}
          onChange={(e) => setAgentFilter(e.target.value)}
          className="rounded-lg border border-ui-border bg-white px-3 py-2 text-sm text-ui-text outline-none focus:border-phthalo-mid"
        >
          <option value="">All Agents</option>
          {agentNames.map((a) => (
            <option key={a ?? 'none'} value={a ?? ''}>
              {a ?? '(none)'}
            </option>
          ))}
        </select>

        <span className="flex items-center text-xs text-ui-text-tertiary">
          {filtered.length} event{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Event list */}
      <div className="space-y-2">
        {filtered.length === 0 ? (
          <div className="flex h-48 items-center justify-center rounded-xl border border-ui-border bg-white">
            <p className="text-sm text-ui-text-secondary">
              {events.length === 0
                ? 'Waiting for events...'
                : 'No events match current filters'}
            </p>
          </div>
        ) : (
          filtered.map((event, idx) => (
            <EventRow key={`${event.id}-${idx}`} event={event} />
          ))
        )}
      </div>
    </div>
  );
}

function EventRow({ event }: { event: AuditLogEntry }) {
  const statusStyles: Record<string, string> = {
    success: 'border-l-green-500 bg-green-50',
    blocked: 'border-l-red-500 bg-red-50',
    queued: 'border-l-yellow-500 bg-yellow-50',
    error: 'border-l-red-500 bg-red-50',
  };

  const statusBadge: Record<string, string> = {
    success: 'bg-green-50 text-green-700',
    blocked: 'bg-red-50 text-red-700',
    queued: 'bg-yellow-50 text-yellow-700',
    error: 'bg-red-50 text-red-700',
  };

  return (
    <div
      className={`rounded-lg border border-ui-border border-l-4 p-4 ${
        statusStyles[event.status] || ''
      }`}
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-xs text-ui-text-tertiary">
            {new Date(event.timestamp).toLocaleTimeString()}
          </span>
          <span className="font-medium text-ui-text">{event.agent_name}</span>
          <span className="text-sm text-ui-text-secondary">{event.username}</span>
        </div>
        <span
          className={`inline-block self-start rounded-full px-2.5 py-0.5 text-xs font-medium ${
            statusBadge[event.status] || statusBadge.error
          }`}
        >
          {event.status}
        </span>
      </div>
      <div className="mt-2">
        <span className="mr-2 rounded bg-phthalo-wash px-2 py-0.5 font-mono text-xs text-phthalo-mid">
          {event.action}
        </span>
        {event.command && (
          <span className="text-sm text-ui-text-secondary">{event.command}</span>
        )}
      </div>
    </div>
  );
}

export default LiveFeed;

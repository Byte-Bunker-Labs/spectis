export interface Agent {
  id: string;
  name: string;
  agent_type: string;
  owner: string;
  status: 'approved' | 'pending_review' | 'blocked' | 'retired';
  version: string;
  description: string;
  allowed_commands: string[];
  blocked_verbs: string[];
  allowed_mcp_tools: string[];
  keywords: string[];
  created_at: string;
  updated_at: string;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  agent_id: string | null;
  agent_name: string | null;
  username: string | null;
  action: string;
  command: string | null;
  prompt: string | null;
  status: string;
  risk_level: string | null;
  source_ip: string | null;
  session_id: string | null;
}

export interface ScanResult {
  id: string;
  hostname: string;
  os_platform: string;
  username: string | null;
  agent_version: string | null;
  unique_server_count: number;
  unique_server_names: string[];
  config_count: number;
  process_count: number;
  network_count: number;
  workspace_count: number;
  local_count: number;
  remote_count: number;
  docker_count: number;
  clients_detected: string[];
  total_findings: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  unapproved_count: number;
  scanned_at: string;
}

export interface ScanResultDetail extends ScanResult {
  config_findings: Record<string, unknown>[];
  process_findings: Record<string, unknown>[];
  network_findings: Record<string, unknown>[];
  workspace_findings: Record<string, unknown>[];
}

export interface Stats {
  total_events: number;
  events_today: number;
  blocked_commands: number;
  active_agents: number;
  active_sessions: number;
  risk_breakdown: Record<string, number>;
  top_agents: { name: string; event_count: number }[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
  role: string;
}

export interface HistoryFilters {
  agent_name?: string;
  username?: string;
  action?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

export interface McpServer {
  id: string;
  server_name: string;
  package: string;
  transport: string;
  runtime: string;
  locality: string;
  endpoint: string | null;
  tools: McpTool[];
  tool_count: number;
  clients: string[];
  endpoints_seen: string[];
  risk_level: string | null;
  has_credentials: boolean;
  env_var_names: string[];
  probe_status: string | null;
  probe_reason: string | null;
  version: string | null;
  first_seen: string;
  last_seen: string;
}

export interface McpTool {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
}

export interface InventoryUser {
  username: string;
  hostname: string;
  os_platform: string;
  client_count: number;
  clients: InventoryClient[];
}

export interface InventoryClient {
  client_name: string;
  server_count: number;
  servers: InventoryServer[];
}

export interface InventoryServer {
  server_name: string;
  package: string;
  transport: string;
  runtime: string;
  locality: string;
  endpoint: string | null;
  version: string | null;
  risk_level: string | null;
  has_credentials: boolean;
  env_var_names: string[];
  probe_status: string | null;
  probe_reason: string | null;
  tool_count: number;
  tools: McpTool[];
}

import type {
  Agent,
  AuditLogEntry,
  Stats,
  ScanResult,
  ScanResultDetail,
  TokenResponse,
  HistoryFilters,
  McpServer,
  InventoryUser,
} from '../types';

const BASE_URL = '/api';

class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('spectis_token');
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...options.headers,
    },
  });

  if (response.status === 401) {
    localStorage.removeItem('spectis_token');
    window.location.reload();
    throw new ApiError('Unauthorized', 401);
  }

  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(body || response.statusText, response.status);
  }

  return response.json();
}

export const apiClient = {
  async login(username: string, password: string): Promise<TokenResponse> {
    const response = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const body = await response.text();
      throw new ApiError(body || 'Login failed', response.status);
    }

    const data: TokenResponse = await response.json();
    localStorage.setItem('spectis_token', data.access_token);
    return data;
  },

  async getStats(): Promise<Stats> {
    return request<Stats>('/stats');
  },

  async getHistory(filters?: HistoryFilters): Promise<AuditLogEntry[]> {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== '') {
          params.append(key, String(value));
        }
      });
    }
    const query = params.toString();
    const path = query ? `/history?${query}` : '/history';
    return request<AuditLogEntry[]>(path);
  },

  async getAgents(): Promise<Agent[]> {
    return request<Agent[]>('/agents');
  },

  async createAgent(data: Record<string, unknown>): Promise<Agent> {
    return request<Agent>('/agents', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateAgent(id: string, data: Record<string, unknown>): Promise<Agent> {
    return request<Agent>(`/agents/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async getScans(): Promise<ScanResult[]> {
    return request<ScanResult[]>('/scans');
  },

  async getScanDetail(id: string): Promise<ScanResultDetail> {
    return request<ScanResultDetail>(`/scans/${id}`);
  },

  async getServers(): Promise<McpServer[]> {
    return request<McpServer[]>('/servers');
  },

  async getInventory(): Promise<InventoryUser[]> {
    return request<InventoryUser[]>('/servers/inventory');
  },
};

export { ApiError };
export default apiClient;

const API = "/api";

function getToken(): string | null {
  return localStorage.getItem("admin_token");
}

async function request<T>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API}${path}`, {
    method: opts.method || "GET",
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });

  if (res.status === 401) {
    localStorage.removeItem("admin_token");
    window.location.href = "/login";
    throw new Error("Session expired");
  }
  if (res.status === 403) throw new Error("Acces superadmin requis");
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return {} as T;
  return res.json();
}

export const auth = {
  login: (data: { email: string; password: string }) =>
    request<{ access_token: string }>("/v1/auth/login", { method: "POST", body: data }),
  me: () => request<any>("/v1/auth/me"),
};

export const admin = {
  // Overview
  overview: () => request<any>("/admin/overview"),
  health: () => request<any>("/admin/health"),

  // Tenants
  tenants: () => request<any[]>("/admin/tenants"),
  tenant: (id: string) => request<any>(`/admin/tenants/${id}`),
  suspendTenant: (id: string) => request<any>(`/admin/tenants/${id}/suspend`, { method: "POST" }),
  activateTenant: (id: string) => request<any>(`/admin/tenants/${id}/activate`, { method: "POST" }),

  // Users
  users: (search?: string) => request<any[]>(`/admin/users${search ? `?search=${search}` : ""}`),
  toggleUser: (id: string) => request<any>(`/admin/users/${id}/toggle`, { method: "POST" }),
  resetPassword: (id: string, password: string) =>
    request<any>(`/admin/users/${id}/reset-password`, { method: "POST", body: { password } }),

  // Agents
  agentStats: () => request<any>("/admin/agents/stats"),
  agentRuns: (limit?: number, agentName?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set("limit", String(limit));
    if (agentName) params.set("agent_name", agentName);
    return request<any[]>(`/admin/agents/recent?${params}`);
  },
  agentRegistry: () => request<any[]>("/admin/agents/registry"),

  // Moderation
  moderationStats: () => request<any>("/admin/moderation/stats"),
  flaggedPosts: () => request<any[]>("/admin/moderation/flagged-posts"),
  escalations: () => request<any[]>("/admin/moderation/escalations"),

  // Content
  allPosts: (limit?: number, status?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set("limit", String(limit));
    if (status) params.set("status", status);
    return request<any[]>(`/admin/content/posts?${params}`);
  },
  allImages: (limit?: number) => request<any[]>(`/admin/content/images${limit ? `?limit=${limit}` : ""}`),
  allDocuments: () => request<any[]>("/admin/content/documents"),
  allConnections: () => request<any[]>("/admin/content/connections"),

  // Audit
  auditEvents: (limit?: number, action?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set("limit", String(limit));
    if (action) params.set("action", action);
    return request<any[]>(`/admin/audit/events?${params}`);
  },

  // Config
  config: () => request<any>("/admin/config/current"),
  agentsConfig: () => request<any>("/admin/config/agents"),

  // System
  websockets: () => request<any>("/admin/system/websockets"),
  queue: () => request<any>("/admin/system/queue"),
  storage: () => request<any>("/admin/system/storage"),

  // Billing
  billingPlans: () => request<any[]>("/admin/billing/plans"),
  billingSubscriptions: () => request<any[]>("/admin/billing/subscriptions"),
  billingMrr: () => request<any>("/admin/billing/mrr"),
  billingUsage: () => request<any[]>("/admin/billing/usage"),

  // Notifications
  broadcast: (data: { title: string; message: string; target_tenant_id?: string; level: string }) =>
    request<any>("/admin/notifications/broadcast", { method: "POST", body: data }),
  notificationHistory: () => request<any[]>("/admin/notifications/history"),

  // Feature Flags
  featureFlags: () => request<any[]>("/admin/feature-flags"),
  createFlag: (data: { name: string; description: string; enabled_globally: boolean }) =>
    request<any>("/admin/feature-flags", { method: "POST", body: data }),
  updateFlag: (id: string, data: any) =>
    request<any>(`/admin/feature-flags/${id}`, { method: "PUT", body: data }),
  deleteFlag: (id: string) =>
    request<any>(`/admin/feature-flags/${id}`, { method: "DELETE" }),
};

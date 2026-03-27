/**
 * OptimusAI API client — all backend calls go through here.
 * Features: env-based URL, auto-retry with exponential backoff, 401 redirect.
 */

const API_BASE = import.meta.env.VITE_API_BASE || "/api/v1";
const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 1000;

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T>(path: string, opts: { method?: string; body?: unknown; retries?: number } = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const maxRetries = opts.retries ?? (opts.method && opts.method !== "GET" ? 0 : MAX_RETRIES);

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const res = await fetch(`${API_BASE}${path}`, {
        method: opts.method || "GET",
        headers,
        body: opts.body ? JSON.stringify(opts.body) : undefined,
      });

      // Auto-redirect to login on 401
      if (res.status === 401 && typeof window !== "undefined" && !path.includes("/auth/")) {
        localStorage.removeItem("token");
        window.location.href = "/auth";
        throw new ApiError(401, "unauthorized", "Session expired");
      }

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const msg = data.error?.message || data.detail || `HTTP ${res.status}`;
        const err = new ApiError(res.status, data.error?.code || "unknown", msg);

        // Don't retry client errors (4xx) except 429 (rate limit)
        if (res.status >= 400 && res.status < 500 && res.status !== 429) throw err;

        // Retry on server errors (5xx) and 429
        if (attempt < maxRetries) {
          await new Promise((r) => setTimeout(r, RETRY_DELAY_MS * Math.pow(2, attempt)));
          continue;
        }
        throw err;
      }

      if (res.status === 204) return {} as T;
      return res.json();
    } catch (err) {
      if (err instanceof ApiError) throw err;
      // Network error — retry
      if (attempt < maxRetries) {
        await new Promise((r) => setTimeout(r, RETRY_DELAY_MS * Math.pow(2, attempt)));
        continue;
      }
      throw new ApiError(0, "network", "Erreur reseau — verifiez votre connexion");
    }
  }

  throw new ApiError(0, "network", "Erreur reseau apres plusieurs tentatives");
}

// ── Types ──

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  phone?: string;
  is_active: boolean;
  avatar_url?: string;
  tenant_id: string;
}

export interface Brand {
  id: string;
  name: string;
  description?: string;
  industry?: string;
  tone: string;
  language: string;
  target_country: string;
  colors: Record<string, string>;
  guidelines: Record<string, any>;
  logo_url?: string;
  created_at: string;
}

export interface Post {
  id: string;
  brand_id: string;
  content_text?: string;
  hashtags: string[];
  status: string;
  channel_variants: Record<string, string>;
  target_channels: { channel: string }[];
  assets: PostAsset[];
  ai_generated: boolean;
  ai_confidence_score?: number;
  scheduled_at?: string;
  published_at?: string;
  created_at: string;
  created_by: string;
}

export interface PostAsset {
  id: string;
  asset_type: string;
  file_url: string;
  thumbnail_url?: string;
  alt_text?: string;
  ai_generated: boolean;
}

export interface Conversation {
  id: string;
  customer_name?: string;
  platform: string;
  status: string;
  message_count: number;
  last_message_at?: string;
  sentiment?: string;
  assigned_to?: string;
  tags: string[];
  created_at: string;
}

export interface Message {
  id: string;
  direction: "inbound" | "outbound";
  content: string;
  content_type: string;
  is_ai_generated: boolean;
  ai_confidence_score?: number;
  sent_by?: string;
  status: string;
  sources: string[];
  created_at: string;
}

export interface KnowledgeDoc {
  id: string;
  brand_id: string;
  title: string;
  doc_type: string;
  source_url?: string;
  file_url?: string;
  status: string;
  chunk_count: number;
  language: string;
  created_at: string;
}

export interface Approval {
  id: string;
  post_id: string;
  requested_by: string;
  status: string;
  created_at: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  settings: Record<string, any>;
  created_at: string;
}

export interface Member {
  id: string;
  email: string;
  full_name: string;
  phone?: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

// ── Endpoints ──

export const auth = {
  register: (data: { email: string; password: string; full_name: string; company_name: string }) =>
    request<{ access_token: string; refresh_token: string }>("/auth/register", { method: "POST", body: data }),
  login: (data: { email: string; password: string }) =>
    request<{ access_token: string; refresh_token: string }>("/auth/login", { method: "POST", body: data }),
  me: () => request<User>("/auth/me"),
};

export interface BrandProfile {
  id: string;
  brand_id: string;
  default_tone: string;
  tone_by_channel: Record<string, string>;
  tone_description: string | null;
  primary_language: string;
  products: { name: string; description?: string; price?: string; category?: string }[];
  services: { name: string; description?: string; zones?: string[] }[];
  response_rules: { trigger: string; rule: string }[];
  banned_words: string[];
  banned_topics: string[];
  sensitive_topics: string[];
  example_posts: { channel: string; content: string; approved?: boolean }[];
  channel_profiles: Record<string, any>;
  business_hours: Record<string, any>;
  contact_info: Record<string, any>;
  greeting_style?: string;
  closing_style?: string;
}

export interface BrandProfileUpdate {
  default_tone?: string;
  tone_by_channel?: Record<string, string>;
  products?: { name: string; description?: string; price?: string; category?: string }[];
  greeting_style?: string;
  closing_style?: string;
  banned_words?: string[];
  banned_topics?: string[];
  example_posts?: { channel: string; content: string; approved?: boolean }[];
  channel_profiles?: Record<string, any>;
}

export interface CommerceProduct {
  id: string;
  brand_id: string;
  name: string;
  description: string | null;
  price: number;
  currency: string;
  category: string | null;
  image_url: string | null;
  in_stock: boolean;
  sku: string | null;
}

export const brands = {
  list: () => request<Brand[]>("/brands"),
  create: (data: Partial<Brand>) => request<Brand>("/brands", { method: "POST", body: data }),
  get: (id: string) => request<Brand>(`/brands/${id}`),
  update: (id: string, data: Partial<Brand>) => request<Brand>(`/brands/${id}`, { method: "PUT", body: data }),
  getProfile: (id: string) => request<BrandProfile>(`/brands/${id}/profile`),
  updateProfile: (id: string, data: BrandProfileUpdate) => request<BrandProfile>(`/brands/${id}/profile`, { method: "PUT", body: data }),
  getContext: (id: string) => request<any>(`/brands/${id}/context`),
};

export interface CommerceOrder {
  id: string;
  customer_name: string;
  customer_phone: string;
  items: { product_id: string; product_name: string; quantity: number; unit_price: number }[];
  total: number;
  currency: string;
  status: string;
  created_at: string;
}

export interface CommerceStats {
  total_revenue: number;
  orders_count: number;
  average_order_value: number;
  currency: string;
  top_products: { name: string; revenue: number; quantity: number }[];
}

export const commerce = {
  listProducts: (brandId?: string, search?: string, category?: string) => {
    const params = new URLSearchParams();
    if (brandId) params.set("brand_id", brandId);
    if (search) params.set("search", search);
    if (category) params.set("category", category);
    const qs = params.toString();
    return request<CommerceProduct[]>(`/commerce/products${qs ? `?${qs}` : ""}`);
  },
  createProduct: (data: { brand_id?: string; name: string; description?: string; price: number; currency?: string; category?: string; image_url?: string; in_stock?: boolean; sku?: string }) =>
    request<CommerceProduct>("/commerce/products", { method: "POST", body: data }),
  updateProduct: (id: string, data: Partial<{ name: string; description: string; price: number; category: string; image_url: string; in_stock: boolean; sku: string }>) =>
    request<CommerceProduct>(`/commerce/products/${id}`, { method: "PUT", body: data }),
  deleteProduct: (id: string) => request<void>(`/commerce/products/${id}`, { method: "DELETE" }),
  promoteProduct: (id: string, data: { channels?: string[]; generate_poster?: boolean; generate_story?: boolean }) =>
    request<any>(`/commerce/products/${id}/promote`, { method: 'POST', body: data }),
  orders: (status?: string) =>
    request<CommerceOrder[]>(`/commerce/orders${status ? `?status=${status}` : ""}`),
  updateOrderStatus: (id: string, status: string) =>
    request<CommerceOrder>(`/commerce/orders/${id}/status`, { method: "PUT", body: { status } }),
  stats: () => request<CommerceStats>("/commerce/stats"),
};

export const posts = {
  list: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<Post[]>(`/posts${qs}`);
  },
  generate: (data: { brand_id: string; brief: string; channels: string[]; language?: string }) =>
    request<Post>("/posts/generate", { method: "POST", body: data }),
  create: (data: { brand_id: string; content_text: string; hashtags?: string[]; target_channels: { channel: string }[]; scheduled_at?: string }) =>
    request<Post>("/posts", { method: "POST", body: data }),
  get: (id: string) => request<Post>(`/posts/${id}`),
  update: (id: string, data: Partial<Post>) => request<Post>(`/posts/${id}`, { method: "PUT", body: data }),
  delete: (id: string) => request<void>(`/posts/${id}`, { method: "DELETE" }),
  submitReview: (id: string) => request<any>(`/posts/${id}/submit-review`, { method: "POST" }),
  publish: (id: string) => request<any>(`/posts/${id}/publish`, { method: "POST" }),
  generateImage: (data: { media_suggestion: string; brand_id?: string; aspect_ratio?: string; post_id?: string }) =>
    request<{ success: boolean; image_url?: string; prompt?: string; error?: string; attached_to_post?: string }>("/posts/image", { method: "POST", body: data }),
  attachImage: (postId: string, data: { image_url: string; s3_key?: string; prompt?: string }) =>
    request<{ id: string; file_url: string; post_id: string }>(`/posts/${postId}/attach-image`, { method: "POST", body: data }),
  generatePoster: (data: { brief: string; brand_id?: string; aspect_ratio?: string }) =>
    request<{ success: boolean; image_url?: string; poster_plan?: any; error?: string }>("/posts/poster", { method: "POST", body: data }),
};

export const approvals = {
  list: (status?: string) => request<Approval[]>(`/approvals${status ? `?status=${status}` : ""}`),
  approve: (id: string, note?: string) =>
    request<any>(`/approvals/${id}/approve`, { method: "POST", body: note ? { note } : {} }),
  reject: (id: string, note: string) =>
    request<any>(`/approvals/${id}/reject`, { method: "POST", body: { note } }),
};

export const conversations = {
  list: (status?: string) => request<Conversation[]>(`/conversations${status ? `?status=${status}` : ""}`),
  get: (id: string) => request<Conversation>(`/conversations/${id}`),
  messages: (id: string) => request<Message[]>(`/conversations/${id}/messages`),
  sendMessage: (id: string, content: string) =>
    request<any>(`/conversations/${id}/messages`, { method: "POST", body: { content } }),
  close: (id: string) => request<any>(`/conversations/${id}/close`, { method: "POST" }),
  escalate: (id: string) => request<any>(`/conversations/${id}/escalate`, { method: "POST" }),
};

export const knowledge = {
  list: (brandId?: string) => request<KnowledgeDoc[]>(`/knowledge/documents${brandId ? `?brand_id=${brandId}` : ""}`),
  create: (data: { brand_id: string; title: string; doc_type: string; raw_content?: string; source_url?: string; language?: string }) =>
    request<KnowledgeDoc>("/knowledge/documents", { method: "POST", body: data }),
  get: (id: string) => request<KnowledgeDoc>(`/knowledge/documents/${id}`),
  delete: (id: string) => request<void>(`/knowledge/documents/${id}`, { method: "DELETE" }),
  createFromUrl: (brand_id: string, url: string, title?: string) =>
    request<any>('/knowledge/documents/from-url', { method: 'POST', body: { brand_id, url, title } }),
  reindex: (id: string) => request<KnowledgeDoc>(`/knowledge/documents/${id}/reindex`, { method: "POST" }),
  search: (data: { query: string; brand_id: string; min_score?: number }) =>
    request<{ results: { chunk_id: string; document_id: string; document_title: string; content: string; section_title?: string; score: number }[]; total: number }>("/knowledge/search", { method: "POST", body: data }),
};

export interface GalleryImage {
  id: string;
  prompt: string;
  technical_prompt?: string;
  image_url: string;
  aspect_ratio: string;
  metadata: Record<string, any>;
  created_at: string;
}

export const gallery = {
  list: (mediaType?: string) => request<any[]>(`/gallery/images${mediaType ? `?media_type=${mediaType}` : ''}`),
  delete: (id: string) => request<void>(`/gallery/images/${id}`, { method: "DELETE" }),
};

export interface SocialAccount {
  id: string;
  brand_id: string;
  platform: string;
  account_name: string;
  platform_account_id: string;
  is_active: boolean;
  token_expires_at?: string;
  scopes: string[];
  capabilities: Record<string, boolean>;
  created_at: string;
}

export const socialAccounts = {
  list: () => request<SocialAccount[]>("/social-accounts"),
  facebookAuthUrl: (brandId: string) =>
    request<{ auth_url: string }>(`/social-accounts/facebook/auth-url?brand_id=${brandId}`),
  facebookCallback: (data: { code: string; brand_id: string }) =>
    request<{ connected: string[]; total_pages: number }>("/social-accounts/facebook/callback", { method: "POST", body: data }),
  connectWhatsApp: (data: { phone_number_id: string; access_token: string; business_name: string; brand_id: string }) =>
    request<SocialAccount>("/social-accounts/whatsapp/connect", { method: "POST", body: data }),
  disconnect: (id: string) => request<void>(`/social-accounts/${id}`, { method: "DELETE" }),
  toggle: (id: string) => request<{ id: string; is_active: boolean }>(`/social-accounts/${id}/toggle`, { method: "POST" }),
};

export interface DesignTemplateItem {
  id: string;
  brand_id: string;
  name: string;
  image_url: string;
  analysis_status: string;
  design_dna: Record<string, any>;
  is_primary: boolean;
  weight: number;
  created_at: string;
}

export const designTemplates = {
  list: (brandId?: string) =>
    request<DesignTemplateItem[]>(`/design-templates${brandId ? `?brand_id=${brandId}` : ""}`),
  upload: async (file: File, brandId: string, name?: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("brand_id", brandId);
    if (name) form.append("name", name);
    const token = localStorage.getItem("token");
    const res = await fetch(`${API_BASE}/design-templates/upload`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new ApiError(res.status, "upload_failed", data.detail || `HTTP ${res.status}`);
    }
    return res.json() as Promise<DesignTemplateItem>;
  },
  status: (id: string) =>
    request<{ id: string; analysis_status: string; analysis_error?: string; design_dna: Record<string, any> }>(`/design-templates/${id}/status`),
  reanalyze: (id: string) =>
    request<DesignTemplateItem>(`/design-templates/${id}/reanalyze`, { method: "POST" }),
  delete: (id: string) =>
    request<void>(`/design-templates/${id}`, { method: "DELETE" }),
  brandDna: (brandId: string) =>
    request<{ brand_id: string; merged_dna: Record<string, any>; template_count: number; preferred_fonts: string[]; color_palette: any[]; layout_preferences: string[]; mood_keywords: string[] }>(`/design-templates/brand-dna/${brandId}`),
};

export const chat = {
  history: (limit = 50) => request<any[]>(`/chat/history?limit=${limit}`),
  send: (message: string) => request<any>("/chat/send", { method: "POST", body: { message } }),
  sendVoice: async (audio: Blob) => {
    const fd = new FormData();
    fd.append("audio", audio, "voice.webm");
    const token = localStorage.getItem("token");
    const res = await fetch(`${API_BASE}/chat/send-voice`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: fd,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new ApiError(res.status, "voice_failed", data.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },
  tts: async (text: string) => {
    const token = localStorage.getItem("token");
    const res = await fetch(`${API_BASE}/chat/tts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new ApiError(res.status, "tts_failed", data.detail || `HTTP ${res.status}`);
    }
    return res.blob();
  },
};

export const intelligence = {
  strategy: (data: { brand_id: string; period?: string }) =>
    request<any>("/intelligence/strategy", { method: "POST", body: data }),
  timing: (data: { platform: string; target_country?: string; content_type?: string }) =>
    request<any>("/intelligence/timing", { method: "POST", body: data }),
  sentiment: (data: { messages: any[]; analysis_type?: string }) =>
    request<any>("/intelligence/sentiment", { method: "POST", body: data }),
  analytics: (data: { report_type?: string; posts?: any[]; conversations?: any[] }) =>
    request<any>("/intelligence/analytics", { method: "POST", body: data }),
  followup: (data: { followup_type: string; customer_profile: any; brand_context?: any; channel?: string }) =>
    request<any>("/intelligence/followup", { method: "POST", body: data }),
  customers: () => request<any[]>("/intelligence/customers"),
};

export const stories = {
  plan: (brief: string, brand_id: string, platform: string = "instagram") =>
    request<any>('/stories/plan', { method: 'POST', body: { brief, brand_id, platform } }),
  render: (story_plan: any, brand_id: string, slide_index?: number) =>
    request<any>('/stories/render', { method: 'POST', body: { story_plan, brand_id, slide_index } }),
  video: (story_plan: any) =>
    request<any>('/stories/video', { method: 'POST', body: { story_plan } }),
  list: () => request<any[]>('/stories'),
  get: (id: string) => request<any>(`/stories/${id}`),
  delete: (id: string) => request<any>(`/stories/${id}`, { method: 'DELETE' }),
};

export const coach = {
  suggestions: () => request<{ suggestions: any[]; health_score: number; summary: string }>("/coach/suggestions"),
};

export const tenant = {
  current: () => request<Tenant>("/tenants/current"),
  updateSettings: (settings: Record<string, any>) =>
    request<Tenant>("/tenants/current/settings", { method: "PUT", body: { settings } }),
  usage: () => request<{ usage: Record<string, { used: number; limit: number; remaining: number; percentage: number }> }>("/tenants/current/usage"),
  members: () => request<Member[]>("/tenants/current/members"),
  inviteMember: (data: { email: string; full_name: string; role: string }) =>
    request<Member>("/tenants/current/members", { method: "POST", body: data }),
};

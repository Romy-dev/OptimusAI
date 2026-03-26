import { useEffect, useState } from "react";
import { admin } from "@/lib/api";
import { toast } from "sonner";
import {
  FileText, Image, BookOpen, Link2, MessageCircle,
  Sparkles, Clock, AlertTriangle, CheckCircle, XCircle, Loader2, Phone, Globe,
} from "lucide-react";

const tabs = [
  { key: "posts", label: "Posts", icon: FileText },
  { key: "images", label: "Images", icon: Image },
  { key: "documents", label: "Documents", icon: BookOpen },
  { key: "connections", label: "Connexions", icon: Link2 },
] as const;

type Tab = (typeof tabs)[number]["key"];

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    published: "bg-emerald-500/10 text-emerald-400",
    scheduled: "bg-sky-500/10 text-sky-400",
    draft: "bg-gray-700/50 text-gray-400",
    failed: "bg-red-500/10 text-red-400",
    pending: "bg-amber-500/10 text-amber-400",
    approved: "bg-emerald-500/10 text-emerald-400",
    rejected: "bg-red-500/10 text-red-400",
  };
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold ${colors[status] || "bg-gray-700/50 text-gray-400"}`}>
      {status}
    </span>
  );
}

function PlatformIcon({ platform }: { platform: string }) {
  const p = platform?.toLowerCase();
  if (p === "facebook" || p === "facebook_page")
    return <Globe className="h-4 w-4 text-blue-500" />;
  if (p === "whatsapp")
    return <MessageCircle className="h-4 w-4 text-green-500" />;
  if (p === "instagram")
    return <Image className="h-4 w-4 text-pink-500" />;
  return <Link2 className="h-4 w-4 text-gray-500" />;
}

function platformColor(platform: string): string {
  const p = platform?.toLowerCase();
  if (p === "facebook" || p === "facebook_page") return "border-blue-500/30";
  if (p === "whatsapp") return "border-green-500/30";
  if (p === "instagram") return "border-pink-500/30";
  return "border-gray-800";
}

function daysUntil(dateStr: string): number {
  return Math.ceil((new Date(dateStr).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
}

/* ─── Posts Tab ─── */
function PostsTab() {
  const [posts, setPosts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    admin.allPosts(50).then(setPosts).catch((e: any) => toast.error(e.message)).finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading />;
  if (posts.length === 0) return <Empty label="Aucun post" />;

  return (
    <div className="space-y-2">
      {posts.map((p) => (
        <div key={p.id} className="rounded-xl bg-gray-900 border border-gray-800 px-5 py-4 flex items-start gap-4">
          <div className="flex-1 min-w-0">
            <p className="text-sm text-white line-clamp-2">{p.content || p.generated_content || "—"}</p>
            <div className="flex items-center gap-3 mt-2 flex-wrap">
              <StatusBadge status={p.status} />
              {p.ai_generated && (
                <span className="inline-flex items-center gap-1 text-[10px] text-purple-400 font-medium">
                  <Sparkles className="h-3 w-3" /> IA
                </span>
              )}
              {p.tenant_name && <span className="text-[10px] text-gray-600">{p.tenant_name}</span>}
            </div>
          </div>
          <span className="text-[10px] text-gray-600 whitespace-nowrap flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {new Date(p.created_at).toLocaleDateString("fr-FR")}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ─── Images Tab ─── */
function ImagesTab() {
  const [images, setImages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    admin.allImages(60).then(setImages).catch((e: any) => toast.error(e.message)).finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading />;
  if (images.length === 0) return <Empty label="Aucune image" />;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {images.map((img) => (
        <div key={img.id} className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden group">
          <div className="aspect-square bg-gray-800 relative">
            {img.url || img.image_url ? (
              <img
                src={img.url || img.image_url}
                alt={img.prompt || "image"}
                className="w-full h-full object-cover"
                loading="lazy"
              />
            ) : (
              <div className="flex items-center justify-center h-full">
                <Image className="h-8 w-8 text-gray-700" />
              </div>
            )}
          </div>
          <div className="p-3">
            {img.prompt && <p className="text-[11px] text-gray-400 line-clamp-2">{img.prompt}</p>}
            {img.tenant_name && <p className="text-[10px] text-gray-600 mt-1">{img.tenant_name}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ─── Documents Tab ─── */
function DocumentsTab() {
  const [docs, setDocs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    admin.allDocuments().then(setDocs).catch((e: any) => toast.error(e.message)).finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading />;
  if (docs.length === 0) return <Empty label="Aucun document" />;

  return (
    <div className="space-y-2">
      {docs.map((d) => (
        <div key={d.id} className="rounded-xl bg-gray-900 border border-gray-800 px-5 py-4 flex items-center gap-4">
          <div className="rounded-lg bg-rose-500/10 p-2">
            <BookOpen className="h-4 w-4 text-rose-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{d.title || d.filename || "Sans titre"}</p>
            <div className="flex items-center gap-3 mt-1">
              {d.doc_type && <span className="text-[10px] text-gray-500 bg-gray-800 rounded px-1.5 py-0.5">{d.doc_type}</span>}
              <StatusBadge status={d.status || "active"} />
              {d.chunks_count !== undefined && (
                <span className="text-[10px] text-gray-600">{d.chunks_count} chunks</span>
              )}
            </div>
          </div>
          {d.tenant_name && <span className="text-[10px] text-gray-600">{d.tenant_name}</span>}
        </div>
      ))}
    </div>
  );
}

/* ─── Connexions Tab ─── */
function ConnectionsTab() {
  const [conns, setConns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    admin.allConnections().then(setConns).catch((e: any) => toast.error(e.message)).finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading />;
  if (conns.length === 0) return <Empty label="Aucune connexion" />;

  return (
    <div className="space-y-2">
      {conns.map((c) => {
        const expiryDays = c.token_expires_at ? daysUntil(c.token_expires_at) : null;
        const expiryWarning = expiryDays !== null && expiryDays < 7;
        return (
          <div key={c.id} className={`rounded-xl bg-gray-900 border px-5 py-4 flex items-center gap-4 ${platformColor(c.platform)}`}>
            <PlatformIcon platform={c.platform} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-white truncate">{c.account_name || c.page_name || c.platform}</p>
                <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${c.is_active ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
                  {c.is_active ? <><CheckCircle className="h-2.5 w-2.5" /> Actif</> : <><XCircle className="h-2.5 w-2.5" /> Inactif</>}
                </span>
              </div>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-[10px] text-gray-500 capitalize">{c.platform}</span>
                {expiryWarning && (
                  <span className="inline-flex items-center gap-1 text-[10px] text-amber-400 font-medium">
                    <AlertTriangle className="h-3 w-3" />
                    Token expire {expiryDays <= 0 ? "aujourd'hui" : `dans ${expiryDays}j`}
                  </span>
                )}
                {!expiryWarning && expiryDays !== null && (
                  <span className="text-[10px] text-gray-600">Token expire dans {expiryDays}j</span>
                )}
              </div>
            </div>
            {c.tenant_name && <span className="text-[10px] text-gray-600">{c.tenant_name}</span>}
          </div>
        );
      })}
    </div>
  );
}

/* ─── Shared components ─── */
function Loading() {
  return (
    <div className="flex items-center justify-center py-16">
      <Loader2 className="h-5 w-5 animate-spin text-gray-600" />
    </div>
  );
}

function Empty({ label }: { label: string }) {
  return (
    <div className="text-center py-16 text-gray-600 text-sm">{label}</div>
  );
}

/* ─── Main Page ─── */
export default function ContentPage() {
  const [tab, setTab] = useState<Tab>("posts");

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Contenu</h1>
        <p className="text-sm text-gray-500 mt-1">Posts, images, documents et connexions de tous les tenants</p>
      </div>

      {/* Tab bar */}
      <div className="flex items-center gap-1 rounded-xl bg-gray-900 border border-gray-800 p-1 w-fit">
        {tabs.map((t) => {
          const Icon = t.icon;
          const active = tab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-gray-800 text-white"
                  : "text-gray-500 hover:text-gray-300 hover:bg-gray-800/50"
              }`}
            >
              <Icon className="h-4 w-4" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      {tab === "posts" && <PostsTab />}
      {tab === "images" && <ImagesTab />}
      {tab === "documents" && <DocumentsTab />}
      {tab === "connections" && <ConnectionsTab />}
    </div>
  );
}

import { useState } from "react";
import { Link } from "react-router-dom";
import {
  MessageSquare, FileText, CheckCircle, ArrowRight, Zap,
  BookOpen, Palette, Clock, TrendingUp, BarChart3, Link2,
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar,
} from "recharts";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/auth-context";
import { useApi } from "@/hooks/use-api";
import { posts, approvals, conversations, tenant, brands as brandsApi, coach } from "@/lib/api";
import { OnboardingWizard } from "@/components/onboarding-wizard";

// Mock weekly data (will be replaced with real analytics endpoint)
const weeklyData = [
  { day: "Lun", posts: 2, messages: 8 },
  { day: "Mar", posts: 1, messages: 12 },
  { day: "Mer", posts: 3, messages: 6 },
  { day: "Jeu", posts: 0, messages: 15 },
  { day: "Ven", posts: 4, messages: 9 },
  { day: "Sam", posts: 2, messages: 4 },
  { day: "Dim", posts: 1, messages: 2 },
];

function StatCard({ label, value, change, icon: Icon, iconBg, href }: {
  label: string; value: string | number; change?: string;
  icon: React.ElementType; iconBg: string; href: string;
}) {
  return (
    <Link to={href} className="surface-interactive p-5 group">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[13px] font-medium text-gray-500">{label}</p>
          <p className="mt-1.5 text-2xl font-bold text-gray-900">{value}</p>
          {change && <p className="mt-1 text-xs font-semibold text-emerald-600">{change}</p>}
        </div>
        <div className={cn("rounded-xl p-2.5", iconBg)}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <div className="mt-3 flex items-center gap-1 text-[12px] font-medium text-gray-400 group-hover:text-brand-600 transition-colors">
        Voir details <ArrowRight className="h-3 w-3" />
      </div>
    </Link>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { data: postList } = useApi(() => posts.list(), []);
  const { data: approvalList } = useApi(() => approvals.list(), []);
  const { data: convList } = useApi(() => conversations.list(), []);
  const { data: usageData } = useApi(() => tenant.usage(), []);
  const { data: brandList, refetch: refetchBrands } = useApi(() => brandsApi.list(), []);
  const { data: coachData } = useApi(() => coach.suggestions(), []);

  const [showOnboarding, setShowOnboarding] = useState(false);

  // Show onboarding if no brands exist and not dismissed
  const needsOnboarding = brandList !== null && brandList.length === 0 && !localStorage.getItem("onboarding_done");

  const inboxCount = convList?.filter(c => c.status !== "resolved" && c.status !== "closed").length ?? 0;
  const approvalCount = approvalList?.length ?? 0;
  const publishedCount = postList?.filter(p => p.status === "published").length ?? 0;
  const totalPosts = postList?.length ?? 0;

  const greeting = user ? `Bonjour, ${user.full_name.split(" ")[0]}` : "Bonjour";

  if (needsOnboarding || showOnboarding) {
    return <OnboardingWizard onComplete={() => { setShowOnboarding(false); refetchBrands(); }} />;
  }

  return (
    <div className="space-y-8 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{greeting}</h1>
        <p className="mt-1 text-sm text-gray-500">
          Voici un resume de votre activite.
          {inboxCount > 0 && (
            <> Vous avez <span className="font-semibold text-brand-600">{inboxCount} message{inboxCount > 1 ? "s" : ""}</span> en attente.</>
          )}
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Messages en attente" value={inboxCount} icon={MessageSquare} iconBg="bg-brand-50 text-brand-600" href="/inbox" />
        <StatCard label="Posts a valider" value={approvalCount} icon={CheckCircle} iconBg="bg-amber-50 text-amber-600" href="/approvals" />
        <StatCard label="Posts crees" value={totalPosts} change={publishedCount > 0 ? `${publishedCount} publies` : undefined} icon={FileText} iconBg="bg-emerald-50 text-emerald-600" href="/posts" />
        <StatCard label="Documents KB" value={usageData?.usage?.documents?.used ?? 0} icon={BookOpen} iconBg="bg-sky-50 text-sky-600" href="/knowledge" />
      </div>

      {/* Coach Suggestions */}
      {coachData?.suggestions && coachData.suggestions.length > 0 && (
        <div className="surface p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-amber-500" />
              <h2 className="text-sm font-semibold text-gray-900">Suggestions IA</h2>
              <span className="text-xs font-medium text-gray-400">Score sante : {coachData.health_score}/100</span>
            </div>
            <div className="flex items-center gap-1">
              <div className={cn(
                "h-2 w-2 rounded-full",
                coachData.health_score >= 70 ? "bg-emerald-500" :
                coachData.health_score >= 40 ? "bg-amber-500" : "bg-red-500"
              )} />
              <span className="text-xs text-gray-500">{coachData.summary}</span>
            </div>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {coachData.suggestions.slice(0, 6).map((s: any, i: number) => (
              <Link
                key={i}
                to={s.action === "navigate" ? s.action_params?.page || "/dashboard" : "/posts"}
                className="flex items-start gap-3 rounded-xl border border-gray-100 p-3 hover:bg-gray-50 transition-colors"
              >
                <div className={cn(
                  "rounded-lg p-1.5 shrink-0 mt-0.5",
                  s.priority === "high" ? "bg-red-50 text-red-500" :
                  s.priority === "medium" ? "bg-amber-50 text-amber-500" : "bg-gray-100 text-gray-400"
                )}>
                  <Zap className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">{s.title}</p>
                  <p className="mt-0.5 text-xs text-gray-400 line-clamp-2">{s.description}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Activity chart */}
        <div className="surface p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="h-4 w-4 text-brand-500" />
            <h2 className="text-sm font-semibold text-gray-900">Activite de la semaine</h2>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={weeklyData}>
              <defs>
                <linearGradient id="colorPosts" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0D9488" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#0D9488" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#9ca3af" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ borderRadius: 12, border: "1px solid #e5e7eb", fontSize: 12 }}
                labelStyle={{ fontWeight: 600 }}
              />
              <Area type="monotone" dataKey="posts" stroke="#0D9488" fill="url(#colorPosts)" strokeWidth={2} name="Posts" />
              <Area type="monotone" dataKey="messages" stroke="#0EA5E9" fill="transparent" strokeWidth={2} strokeDasharray="4 4" name="Messages" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Usage chart */}
        <div className="surface p-5">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="h-4 w-4 text-sky-500" />
            <h2 className="text-sm font-semibold text-gray-900">Utilisation du forfait</h2>
          </div>
          {usageData?.usage ? (
            <div className="space-y-3">
              {Object.entries(usageData.usage).slice(0, 6).map(([key, val]) => {
                const labels: Record<string, string> = {
                  ai_generations: "Generations IA",
                  posts_per_month: "Posts / mois",
                  support_conversations: "Conversations",
                  documents: "Documents",
                  storage_mb: "Stockage (MB)",
                  users: "Utilisateurs",
                  brands: "Marques",
                  social_accounts: "Comptes sociaux",
                  whatsapp_messages: "Messages WhatsApp",
                };
                const pct = val.limit > 0 ? Math.round((val.used / val.limit) * 100) : 0;
                return (
                  <div key={key}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-gray-600">{labels[key] || key}</span>
                      <span className="text-xs font-semibold text-gray-800">{val.used} / {val.limit}</span>
                    </div>
                    <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
                      <div
                        className={cn("h-full rounded-full transition-all", pct > 80 ? "bg-red-500" : pct > 50 ? "bg-amber-500" : "bg-brand-500")}
                        style={{ width: `${Math.min(pct, 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="flex items-center justify-center h-[200px] text-gray-300 text-sm">Chargement...</div>
          )}
        </div>
      </div>

      {/* Quick actions */}
      <div>
        <p className="section-label mb-3">Actions rapides</p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {[
            { label: "Creer un post IA", desc: "Generer du contenu", icon: Zap, href: "/posts?action=generate", primary: true },
            { label: "Voir l'inbox", desc: `${inboxCount} conversations`, icon: MessageSquare, href: "/inbox" },
            { label: "Ajouter un document", desc: "Nourrir la base IA", icon: BookOpen, href: "/knowledge" },
            { label: "Configurer la marque", desc: "Ton, couleurs, produits", icon: Palette, href: "/brands" },
            { label: "Connexions", desc: "Reseaux sociaux", icon: Link2, href: "/connections" },
          ].map((a) => (
            <Link
              key={a.href}
              to={a.href}
              className={cn(
                "flex items-start gap-3 rounded-2xl p-4 transition-all duration-200 group",
                a.primary
                  ? "bg-brand-500 text-white shadow-md shadow-brand-500/15 hover:shadow-lg hover:bg-brand-600"
                  : "surface-hover",
              )}
            >
              <div className={cn("rounded-xl p-2 shrink-0", a.primary ? "bg-white/20" : "bg-brand-50 text-brand-600")}>
                <a.icon className="h-4 w-4" />
              </div>
              <div>
                <p className={cn("text-sm font-semibold", a.primary ? "text-white" : "text-gray-800")}>{a.label}</p>
                <p className={cn("mt-0.5 text-xs", a.primary ? "text-white/70" : "text-gray-400")}>{a.desc}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Recent posts */}
      {postList && postList.length > 0 && (
        <div className="surface">
          <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-gray-400" />
              <h2 className="text-sm font-semibold text-gray-900">Derniers contenus</h2>
            </div>
            <Link to="/posts" className="text-xs font-medium text-brand-600 hover:text-brand-700">Tout voir</Link>
          </div>
          <div className="divide-y divide-gray-50">
            {postList.slice(0, 5).map((post) => (
              <div key={post.id} className="flex items-center gap-4 px-5 py-3.5 hover:bg-gray-50/50 transition-colors">
                <div className={cn("rounded-lg p-2 shrink-0", post.status === "published" ? "bg-emerald-50 text-emerald-600" : "bg-gray-100 text-gray-500")}>
                  <FileText className="h-4 w-4" />
                </div>
                <p className="flex-1 text-sm text-gray-700 truncate">{post.content_text || "Post sans contenu"}</p>
                <span className="badge bg-gray-100 text-gray-500 shrink-0">{post.status}</span>
                <span className="shrink-0 text-xs text-gray-400">
                  {new Date(post.created_at).toLocaleDateString("fr-FR", { day: "numeric", month: "short" })}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent conversations */}
      {convList && convList.length > 0 && (
        <div className="surface">
          <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-gray-400" />
              <h2 className="text-sm font-semibold text-gray-900">Dernieres conversations</h2>
            </div>
            <Link to="/inbox" className="text-xs font-medium text-brand-600 hover:text-brand-700">Voir l'inbox</Link>
          </div>
          <div className="divide-y divide-gray-50">
            {convList.slice(0, 5).map((conv) => (
              <Link key={conv.id} to="/inbox" className="flex items-center gap-4 px-5 py-3.5 hover:bg-gray-50/50 transition-colors">
                <div className={cn("rounded-lg p-2 shrink-0", conv.status === "escalated" ? "bg-red-50 text-red-500" : conv.status === "ai_handling" ? "bg-brand-50 text-brand-600" : "bg-gray-100 text-gray-500")}>
                  <MessageSquare className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-700 truncate">{conv.customer_name || "Client"} · {conv.platform}</p>
                </div>
                <span className={cn("badge shrink-0", conv.status === "escalated" ? "bg-red-50 text-red-600" : conv.status === "ai_handling" ? "bg-brand-50 text-brand-600" : "bg-gray-100 text-gray-500")}>{conv.status}</span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

import { useState } from "react";
import {
  BarChart3, TrendingUp, MessageSquare, Users, Eye, Heart, Share2, ArrowUpRight,
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { cn } from "@/lib/utils";

// ── Mock data ──

const PERIODS = [
  { label: "7j", days: 7 },
  { label: "30j", days: 30 },
  { label: "90j", days: 90 },
] as const;

const kpis = [
  { label: "Posts publiés", value: 47, change: "+12%", icon: BarChart3, iconBg: "bg-teal-50 text-teal-600" },
  { label: "Engagement total", value: "2.4k", change: "+8.3%", icon: Heart, iconBg: "bg-sky-50 text-sky-600" },
  { label: "Conversations", value: 128, change: "+23%", icon: MessageSquare, iconBg: "bg-amber-50 text-amber-600" },
  { label: "Taux de résolution", value: "87%", change: "+5%", icon: Users, iconBg: "bg-emerald-50 text-emerald-600" },
];

// Posts per day (last 30 days)
const postsPerDay = Array.from({ length: 30 }, (_, i) => {
  const d = new Date();
  d.setDate(d.getDate() - (29 - i));
  return {
    date: d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" }),
    posts: Math.floor(Math.random() * 5) + 1,
    engagement: Math.floor(Math.random() * 120) + 20,
  };
});

const engagementByChannel = [
  { channel: "Facebook", likes: 820, comments: 245, shares: 132 },
  { channel: "Instagram", likes: 1340, comments: 410, shares: 89 },
  { channel: "WhatsApp", likes: 0, comments: 0, shares: 0, messages: 456 },
];

const contentTypeDistribution = [
  { name: "Image", value: 38, color: "#0D9488" },
  { name: "Vidéo", value: 15, color: "#0EA5E9" },
  { name: "Texte", value: 27, color: "#F59E0B" },
  { name: "Carrousel", value: 12, color: "#EF4444" },
  { name: "Story", value: 8, color: "#8B5CF6" },
];

const topPosts = [
  { id: "1", content: "Découvrez notre nouvelle gamme de produits bio 100% naturels...", channel: "Instagram", engagement: 342, published: "2026-03-22" },
  { id: "2", content: "Promo flash ! -30% sur toute la boutique ce weekend seulement...", channel: "Facebook", engagement: 287, published: "2026-03-20" },
  { id: "3", content: "Les coulisses de notre atelier de fabrication artisanale...", channel: "Instagram", engagement: 215, published: "2026-03-18" },
  { id: "4", content: "Merci à nos 10 000 abonnés ! Un concours spécial pour fêter ça...", channel: "Facebook", engagement: 198, published: "2026-03-15" },
  { id: "5", content: "Notre engagement pour l'environnement : emballages 100% recyclables...", channel: "Instagram", engagement: 176, published: "2026-03-12" },
];

const recentConversations = [
  { id: "1", customer: "Aminata Ouédraogo", platform: "WhatsApp", sentiment: "positive", lastMessage: "Merci beaucoup pour votre aide !", date: "2026-03-25" },
  { id: "2", customer: "Ibrahim Konaté", platform: "Messenger", sentiment: "neutral", lastMessage: "D'accord, je vais vérifier de mon côté.", date: "2026-03-25" },
  { id: "3", customer: "Fatou Diallo", platform: "WhatsApp", sentiment: "negative", lastMessage: "Je n'ai toujours pas reçu ma commande...", date: "2026-03-24" },
  { id: "4", customer: "Moussa Traoré", platform: "Messenger", sentiment: "positive", lastMessage: "Le produit est excellent, je recommande !", date: "2026-03-24" },
  { id: "5", customer: "Aïssata Bamba", platform: "WhatsApp", sentiment: "neutral", lastMessage: "Est-ce que vous livrez à Bobo-Dioulasso ?", date: "2026-03-23" },
];

// ── Component ──

function KpiCard({ label, value, change, icon: Icon, iconBg }: typeof kpis[number]) {
  return (
    <div className="surface p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[13px] font-medium text-gray-500">{label}</p>
          <p className="mt-1.5 text-2xl font-bold text-gray-900">{value}</p>
          {change && (
            <p className="mt-1 flex items-center gap-0.5 text-xs font-semibold text-emerald-600">
              <ArrowUpRight className="h-3 w-3" /> {change}
            </p>
          )}
        </div>
        <div className={cn("rounded-xl p-2.5", iconBg)}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

const sentimentColors: Record<string, { bg: string; text: string; label: string }> = {
  positive: { bg: "bg-emerald-50", text: "text-emerald-600", label: "Positif" },
  neutral: { bg: "bg-gray-100", text: "text-gray-500", label: "Neutre" },
  negative: { bg: "bg-red-50", text: "text-red-600", label: "Négatif" },
};

export default function AnalyticsPage() {
  const [period, setPeriod] = useState<number>(30);

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="mt-1 text-sm text-gray-500">Vue d'ensemble de vos performances marketing et support.</p>
        </div>
        <div className="flex items-center gap-1 rounded-xl bg-gray-100 p-1">
          {PERIODS.map((p) => (
            <button
              key={p.days}
              onClick={() => setPeriod(p.days)}
              className={cn(
                "rounded-lg px-4 py-1.5 text-xs font-semibold transition-all",
                period === p.days ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700",
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kpi) => (
          <KpiCard key={kpi.label} {...kpi} />
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Posts per day — Area Chart */}
        <div className="surface p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="h-4 w-4 text-teal-500" />
            <h2 className="text-sm font-semibold text-gray-900">Posts par jour</h2>
            <span className="text-xs text-gray-400 ml-auto">Derniers {period} jours</span>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={postsPerDay.slice(-period)}>
              <defs>
                <linearGradient id="colorPostsAnalytics" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0D9488" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#0D9488" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#9ca3af" }} axisLine={false} tickLine={false} interval={Math.floor(period / 7)} />
              <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e5e7eb", fontSize: 12 }} labelStyle={{ fontWeight: 600 }} />
              <Area type="monotone" dataKey="posts" stroke="#0D9488" fill="url(#colorPostsAnalytics)" strokeWidth={2} name="Posts" />
              <Area type="monotone" dataKey="engagement" stroke="#0EA5E9" fill="transparent" strokeWidth={2} strokeDasharray="4 4" name="Engagement" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Engagement by channel — Bar Chart */}
        <div className="surface p-5">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="h-4 w-4 text-sky-500" />
            <h2 className="text-sm font-semibold text-gray-900">Engagement par canal</h2>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={engagementByChannel}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="channel" tick={{ fontSize: 11, fill: "#9ca3af" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e5e7eb", fontSize: 12 }} labelStyle={{ fontWeight: 600 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="likes" name="Likes" fill="#0D9488" radius={[4, 4, 0, 0]} />
              <Bar dataKey="comments" name="Commentaires" fill="#0EA5E9" radius={[4, 4, 0, 0]} />
              <Bar dataKey="shares" name="Partages" fill="#F59E0B" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Pie chart + Top posts row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Pie chart: Content type distribution */}
        <div className="surface p-5">
          <div className="flex items-center gap-2 mb-4">
            <Eye className="h-4 w-4 text-amber-500" />
            <h2 className="text-sm font-semibold text-gray-900">Types de contenu</h2>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie
                data={contentTypeDistribution}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={85}
                paddingAngle={3}
                dataKey="value"
                nameKey="name"
              >
                {contentTypeDistribution.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e5e7eb", fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Top 5 performing posts */}
        <div className="surface lg:col-span-2">
          <div className="flex items-center gap-2 border-b border-gray-100 px-5 py-4">
            <TrendingUp className="h-4 w-4 text-teal-500" />
            <h2 className="text-sm font-semibold text-gray-900">Top 5 posts performants</h2>
          </div>
          <div className="divide-y divide-gray-50">
            {topPosts.map((post, i) => (
              <div key={post.id} className="flex items-center gap-4 px-5 py-3.5 hover:bg-gray-50/50 transition-colors">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-teal-50 text-xs font-bold text-teal-600 shrink-0">
                  {i + 1}
                </span>
                <p className="flex-1 text-sm text-gray-700 truncate">{post.content}</p>
                <span className="badge bg-gray-100 text-gray-500 shrink-0">{post.channel}</span>
                <div className="flex items-center gap-1 shrink-0">
                  <Heart className="h-3.5 w-3.5 text-red-400" />
                  <span className="text-xs font-semibold text-gray-700">{post.engagement}</span>
                </div>
                <span className="text-xs text-gray-400 shrink-0">
                  {new Date(post.published).toLocaleDateString("fr-FR", { day: "numeric", month: "short" })}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent conversations with sentiment */}
      <div className="surface">
        <div className="flex items-center gap-2 border-b border-gray-100 px-5 py-4">
          <MessageSquare className="h-4 w-4 text-gray-400" />
          <h2 className="text-sm font-semibold text-gray-900">Conversations récentes</h2>
        </div>
        <div className="divide-y divide-gray-50">
          {recentConversations.map((conv) => {
            const s = sentimentColors[conv.sentiment] ?? sentimentColors.neutral;
            return (
              <div key={conv.id} className="flex items-center gap-4 px-5 py-3.5 hover:bg-gray-50/50 transition-colors">
                <div className="rounded-lg p-2 bg-gray-100 text-gray-500 shrink-0">
                  <MessageSquare className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800">{conv.customer}</p>
                  <p className="text-xs text-gray-400 truncate">{conv.lastMessage}</p>
                </div>
                <span className="badge bg-gray-100 text-gray-500 shrink-0">{conv.platform}</span>
                <span className={cn("badge shrink-0", s.bg, s.text)}>{s.label}</span>
                <span className="text-xs text-gray-400 shrink-0">
                  {new Date(conv.date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" })}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

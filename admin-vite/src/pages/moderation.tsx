import { useEffect, useState } from "react";
import { admin } from "@/lib/api";
import { toast } from "sonner";
import {
  ShieldAlert, MessageSquareWarning, Clock, FileWarning, AlertTriangle,
  Building2, Calendar, Eye, Loader2,
} from "lucide-react";

function StatCard({ label, value, icon: Icon, color }: { label: string; value: number | string; icon: any; color: string }) {
  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-500 font-medium">{label}</p>
          <p className="mt-1 text-2xl font-bold text-white">{value}</p>
        </div>
        <div className={`rounded-lg p-2.5 ${color}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const p = priority?.toLowerCase();
  if (p === "high" || p === "haute")
    return <span className="rounded-full px-2.5 py-0.5 text-[10px] font-bold bg-red-500/10 text-red-400">Haute</span>;
  if (p === "medium" || p === "moyenne")
    return <span className="rounded-full px-2.5 py-0.5 text-[10px] font-bold bg-amber-500/10 text-amber-400">Moyenne</span>;
  return <span className="rounded-full px-2.5 py-0.5 text-[10px] font-bold bg-gray-700/50 text-gray-400">Basse</span>;
}

export default function ModerationPage() {
  const [stats, setStats] = useState<any>(null);
  const [flaggedPosts, setFlaggedPosts] = useState<any[]>([]);
  const [escalations, setEscalations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const [s, fp, esc] = await Promise.all([
          admin.moderationStats(),
          admin.flaggedPosts(),
          admin.escalations(),
        ]);
        setStats(s);
        setFlaggedPosts(fp);
        setEscalations(esc);
      } catch (err: any) {
        toast.error(err.message || "Erreur lors du chargement de la moderation");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-gray-500" />
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Moderation</h1>
        <p className="text-sm text-gray-500 mt-1">Contenus signales et escalations</p>
      </div>

      {/* Stats row */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard
            label="Posts rejetes"
            value={stats.rejected_posts ?? 0}
            icon={FileWarning}
            color="bg-red-500/10 text-red-400"
          />
          <StatCard
            label="Conversations escaladees"
            value={stats.escalated_conversations ?? 0}
            icon={MessageSquareWarning}
            color="bg-amber-500/10 text-amber-400"
          />
          <StatCard
            label="En attente de revue"
            value={stats.pending_review ?? 0}
            icon={Clock}
            color="bg-sky-500/10 text-sky-400"
          />
        </div>
      )}

      {/* Flagged posts section */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
        <div className="flex items-center gap-2 mb-4">
          <ShieldAlert className="h-4 w-4 text-red-400" />
          <h2 className="text-sm font-semibold text-white">Posts rejetes</h2>
          <span className="ml-auto rounded-full bg-red-500/10 px-2.5 py-0.5 text-[10px] font-bold text-red-400">
            {flaggedPosts.length}
          </span>
        </div>

        {flaggedPosts.length === 0 ? (
          <div className="py-8 text-center">
            <ShieldAlert className="h-8 w-8 text-gray-700 mx-auto mb-2" />
            <p className="text-sm text-gray-500">Aucun post rejete</p>
          </div>
        ) : (
          <div className="space-y-3">
            {flaggedPosts.map((post, i) => (
              <div key={post.id || i} className="rounded-lg bg-gray-800/50 p-4 hover:bg-gray-800 transition-colors">
                <div className="flex items-start gap-4">
                  {/* Content preview */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-300 line-clamp-2">
                      {post.content || post.text || post.body || "Contenu non disponible"}
                    </p>
                    <div className="flex items-center gap-4 mt-2">
                      <div className="flex items-center gap-1.5">
                        <Building2 className="h-3 w-3 text-gray-600" />
                        <span className="text-xs text-gray-500">{post.tenant_name || post.tenant_id?.slice(0, 8)}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Calendar className="h-3 w-3 text-gray-600" />
                        <span className="text-xs text-gray-500">
                          {post.created_at ? new Date(post.created_at).toLocaleDateString("fr-FR") : "—"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Confidence score */}
                  <div className="shrink-0 text-right">
                    {post.confidence !== undefined && post.confidence !== null && (
                      <div className="flex items-center gap-1.5">
                        <Eye className="h-3 w-3 text-gray-500" />
                        <span className={`text-xs font-bold ${
                          post.confidence >= 0.8 ? "text-red-400" :
                          post.confidence >= 0.5 ? "text-amber-400" : "text-gray-400"
                        }`}>
                          {(post.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    )}
                    {post.reason && (
                      <p className="text-[10px] text-gray-500 mt-1 max-w-[140px] text-right">{post.reason}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Escalations section */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="h-4 w-4 text-amber-400" />
          <h2 className="text-sm font-semibold text-white">Escalations actives</h2>
          <span className="ml-auto rounded-full bg-amber-500/10 px-2.5 py-0.5 text-[10px] font-bold text-amber-400">
            {escalations.length}
          </span>
        </div>

        {escalations.length === 0 ? (
          <div className="py-8 text-center">
            <AlertTriangle className="h-8 w-8 text-gray-700 mx-auto mb-2" />
            <p className="text-sm text-gray-500">Aucune escalation active</p>
          </div>
        ) : (
          <div className="space-y-3">
            {escalations.map((esc, i) => (
              <div key={esc.id || i} className="rounded-lg bg-gray-800/50 p-4 hover:bg-gray-800 transition-colors">
                <div className="flex items-center gap-4">
                  {/* Reason */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-300">
                      {esc.reason || esc.message || "Escalation sans motif"}
                    </p>
                    <div className="flex items-center gap-4 mt-2">
                      <div className="flex items-center gap-1.5">
                        <Building2 className="h-3 w-3 text-gray-600" />
                        <span className="text-xs text-gray-500">{esc.tenant_name || esc.tenant_id?.slice(0, 8)}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Calendar className="h-3 w-3 text-gray-600" />
                        <span className="text-xs text-gray-500">
                          {esc.created_at ? new Date(esc.created_at).toLocaleDateString("fr-FR") : "—"}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Priority badge */}
                  <div className="shrink-0">
                    <PriorityBadge priority={esc.priority || "low"} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

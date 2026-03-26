import { useEffect, useState } from "react";
import { admin } from "@/lib/api";
import {
  Users, FileText, MessageSquare, Image, BookOpen, UserCheck,
  Server, Database, Cpu, HardDrive, CheckCircle, XCircle, AlertCircle,
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

function HealthBadge({ status }: { status: string }) {
  if (status === "ok") return <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-400"><CheckCircle className="h-3 w-3" /> OK</span>;
  if (status === "down") return <span className="inline-flex items-center gap-1 text-xs font-medium text-red-400"><XCircle className="h-3 w-3" /> Down</span>;
  return <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-400"><AlertCircle className="h-3 w-3" /> {status}</span>;
}

export default function OverviewPage() {
  const [data, setData] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    admin.overview().then(setData).catch(() => {});
    admin.health().then(setHealth).catch(() => {});
  }, []);

  return (
    <div className="space-y-8 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Vue d'ensemble</h1>
        <p className="text-sm text-gray-500 mt-1">Metriques globales de la plateforme</p>
      </div>

      {/* Stats grid */}
      {data && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Tenants" value={data.totals.tenants} icon={Users} color="bg-brand-500/10 text-brand-400" />
          <StatCard label="Utilisateurs" value={data.totals.users} icon={UserCheck} color="bg-sky-500/10 text-sky-400" />
          <StatCard label="Posts" value={data.totals.posts} icon={FileText} color="bg-purple-500/10 text-purple-400" />
          <StatCard label="Conversations" value={data.totals.conversations} icon={MessageSquare} color="bg-emerald-500/10 text-emerald-400" />
          <StatCard label="Images" value={data.totals.images} icon={Image} color="bg-amber-500/10 text-amber-400" />
          <StatCard label="Documents KB" value={data.totals.documents} icon={BookOpen} color="bg-rose-500/10 text-rose-400" />
          <StatCard label="Profils clients" value={data.totals.customer_profiles} icon={Users} color="bg-indigo-500/10 text-indigo-400" />
          <StatCard label="Inscriptions 7j" value={data.recent_signups_7d} icon={UserCheck} color="bg-green-500/10 text-green-400" />
        </div>
      )}

      {/* Posts by status */}
      {data && Object.keys(data.posts_by_status).length > 0 && (
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Posts par statut</h2>
          <div className="flex flex-wrap gap-3">
            {Object.entries(data.posts_by_status).map(([status, count]) => (
              <div key={status} className="rounded-lg bg-gray-800 px-4 py-2">
                <p className="text-xs text-gray-500">{status}</p>
                <p className="text-lg font-bold text-white">{count as number}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* System health */}
      {health && (
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Server className="h-4 w-4 text-gray-500" />
            <h2 className="text-sm font-semibold text-white">Sante systeme</h2>
            <span className={`ml-auto rounded-full px-3 py-1 text-xs font-bold ${health.status === "healthy" ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400"}`}>
              {health.status}
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {Object.entries(health.checks).map(([name, check]: [string, any]) => (
              <div key={name} className="rounded-lg bg-gray-800/50 p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-gray-400 capitalize">{name}</span>
                  <HealthBadge status={check.status} />
                </div>
                {check.models && <p className="text-[10px] text-gray-500 mt-1">{check.models.join(", ")}</p>}
                {check.used_memory_human && <p className="text-[10px] text-gray-500 mt-1">RAM: {check.used_memory_human}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { admin } from "@/lib/api";
import { toast } from "sonner";
import { CreditCard, DollarSign, Users, BarChart3 } from "lucide-react";

const tabs = ["Plans", "Abonnements", "Utilisation"] as const;
type Tab = (typeof tabs)[number];

export default function BillingPage() {
  const [mrr, setMrr] = useState<any>(null);
  const [plans, setPlans] = useState<any[]>([]);
  const [subscriptions, setSubscriptions] = useState<any[]>([]);
  const [usage, setUsage] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>("Plans");

  useEffect(() => {
    admin.billingMrr().then(setMrr).catch(() => {});
    admin.billingPlans().then(setPlans).catch(() => {});
    admin.billingSubscriptions().then(setSubscriptions).catch(() => {});
    admin.billingUsage().then(setUsage).catch(() => {});
  }, []);

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Facturation</h1>
        <p className="text-sm text-gray-500 mt-1">Gestion des plans, abonnements et usage</p>
      </div>

      {/* MRR Card */}
      <div className="rounded-xl bg-gray-900 border border-gray-800 p-6">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-500/10 text-brand-400">
            <DollarSign className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wider">Revenu mensuel recurrent (MRR)</p>
            <p className="text-3xl font-bold text-white mt-1">
              {mrr?.amount != null ? Number(mrr.amount).toLocaleString("fr-FR") : "—"}{" "}
              <span className="text-lg text-gray-400">XOF</span>
            </p>
          </div>
          {mrr?.active_subscriptions != null && (
            <div className="ml-auto text-right">
              <p className="text-xs text-gray-500">Abonnements actifs</p>
              <p className="text-xl font-bold text-emerald-400">{mrr.active_subscriptions}</p>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-gray-900 border border-gray-800 p-1">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab
                ? "bg-brand-500/10 text-brand-400"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Plans Tab */}
      {activeTab === "Plans" && (
        <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Nom</th>
                <th className="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Prix (XOF)</th>
                <th className="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Fonctionnalites</th>
                <th className="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Statut</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {plans.map((p) => (
                <tr key={p.id} className="hover:bg-gray-800/50 transition-colors">
                  <td className="px-5 py-4">
                    <div className="flex items-center gap-3">
                      <CreditCard className="h-4 w-4 text-brand-400" />
                      <span className="text-sm font-medium text-white">{p.name}</span>
                    </div>
                  </td>
                  <td className="px-5 py-4 text-sm text-gray-300">{Number(p.price).toLocaleString("fr-FR")}</td>
                  <td className="px-5 py-4">
                    <div className="flex flex-wrap gap-1.5">
                      {(p.features || []).slice(0, 3).map((f: string, i: number) => (
                        <span key={i} className="rounded bg-gray-800 px-2 py-0.5 text-[10px] text-gray-400">{f}</span>
                      ))}
                      {(p.features || []).length > 3 && (
                        <span className="rounded bg-gray-800 px-2 py-0.5 text-[10px] text-gray-500">+{p.features.length - 3}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-5 py-4">
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                      p.is_active ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
                    }`}>
                      {p.is_active ? "Actif" : "Inactif"}
                    </span>
                  </td>
                </tr>
              ))}
              {plans.length === 0 && (
                <tr><td colSpan={4} className="px-5 py-8 text-center text-sm text-gray-500">Aucun plan configure</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Subscriptions Tab */}
      {activeTab === "Abonnements" && (
        <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Tenant</th>
                <th className="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Plan</th>
                <th className="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Statut</th>
                <th className="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Debut</th>
                <th className="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Fin</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {subscriptions.map((s) => (
                <tr key={s.id} className="hover:bg-gray-800/50 transition-colors">
                  <td className="px-5 py-4">
                    <div className="flex items-center gap-3">
                      <Users className="h-4 w-4 text-brand-400" />
                      <span className="text-sm font-medium text-white">{s.tenant_name || s.tenant_id}</span>
                    </div>
                  </td>
                  <td className="px-5 py-4 text-sm text-gray-300">{s.plan_name || s.plan_id}</td>
                  <td className="px-5 py-4">
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                      s.status === "active" ? "bg-emerald-500/10 text-emerald-400"
                        : s.status === "cancelled" ? "bg-red-500/10 text-red-400"
                        : "bg-amber-500/10 text-amber-400"
                    }`}>
                      {s.status}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-xs text-gray-400">{s.start_date ? new Date(s.start_date).toLocaleDateString("fr-FR") : "—"}</td>
                  <td className="px-5 py-4 text-xs text-gray-400">{s.end_date ? new Date(s.end_date).toLocaleDateString("fr-FR") : "—"}</td>
                </tr>
              ))}
              {subscriptions.length === 0 && (
                <tr><td colSpan={5} className="px-5 py-8 text-center text-sm text-gray-500">Aucun abonnement</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Usage Tab */}
      {activeTab === "Utilisation" && (
        <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Fonctionnalite</th>
                <th className="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Usage total</th>
                <th className="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Tenants</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {usage.map((u, i) => (
                <tr key={i} className="hover:bg-gray-800/50 transition-colors">
                  <td className="px-5 py-4">
                    <div className="flex items-center gap-3">
                      <BarChart3 className="h-4 w-4 text-brand-400" />
                      <span className="text-sm font-medium text-white">{u.feature_name || u.feature}</span>
                    </div>
                  </td>
                  <td className="px-5 py-4 text-sm text-gray-300">{Number(u.total_usage).toLocaleString("fr-FR")}</td>
                  <td className="px-5 py-4 text-sm text-gray-300">{u.tenant_count}</td>
                </tr>
              ))}
              {usage.length === 0 && (
                <tr><td colSpan={3} className="px-5 py-8 text-center text-sm text-gray-500">Aucune donnee d'utilisation</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

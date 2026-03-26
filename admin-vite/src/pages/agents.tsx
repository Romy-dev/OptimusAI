import { useEffect, useState } from "react";
import { admin } from "@/lib/api";
import {
  Bot, Clock, Zap, CheckCircle, XCircle, Activity, Hash,
} from "lucide-react";

export default function AgentsPage() {
  const [stats, setStats] = useState<any>(null);
  const [registry, setRegistry] = useState<any[]>([]);
  const [runs, setRuns] = useState<any[]>([]);
  const [filterAgent, setFilterAgent] = useState("");

  useEffect(() => {
    admin.agentStats().then(setStats).catch(() => {});
    admin.agentRegistry().then(setRegistry).catch(() => {});
    admin.agentRuns(30).then(setRuns).catch(() => {});
  }, []);

  const filteredRuns = filterAgent ? runs.filter((r) => r.agent_name === filterAgent) : runs;

  return (
    <div className="space-y-8 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Agents IA</h1>
        <p className="text-sm text-gray-500 mt-1">{registry.length} agents enregistres dans le systeme</p>
      </div>

      {/* Agent registry */}
      <div>
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Registre des agents</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {registry.map((a) => (
            <div key={a.name} className="rounded-xl bg-gray-900 border border-gray-800 p-4 hover:border-gray-700 transition-colors cursor-pointer"
              onClick={() => setFilterAgent(filterAgent === a.name ? "" : a.name)}>
              <div className="flex items-center gap-2 mb-2">
                <Bot className={`h-4 w-4 ${filterAgent === a.name ? "text-brand-400" : "text-gray-500"}`} />
                <span className="text-sm font-bold text-white">{a.name}</span>
              </div>
              <p className="text-[11px] text-gray-500 line-clamp-2">{a.description}</p>
              <div className="flex items-center gap-3 mt-3 text-[10px] text-gray-600">
                <span>Retries: {a.max_retries}</span>
                <span>Seuil: {(a.confidence_threshold * 100).toFixed(0)}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      {stats && stats.agents?.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Performance</h2>
          <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500">Agent</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">Executions</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">Latence moy.</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-gray-500">Tokens total</th>
                </tr>
              </thead>
              <tbody>
                {stats.agents.map((a: any) => (
                  <tr key={a.agent_name} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                    <td className="px-4 py-3 text-white font-medium">{a.agent_name}</td>
                    <td className="px-4 py-3 text-right text-gray-400">{a.total_runs}</td>
                    <td className="px-4 py-3 text-right text-gray-400">{a.avg_latency_ms}ms</td>
                    <td className="px-4 py-3 text-right text-gray-400">{a.total_tokens.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recent runs */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
            Executions recentes {filterAgent && <span className="text-brand-400 normal-case">· {filterAgent}</span>}
          </h2>
          {filterAgent && (
            <button onClick={() => setFilterAgent("")} className="text-xs text-gray-500 hover:text-gray-300">Voir tout</button>
          )}
        </div>
        <div className="space-y-2">
          {filteredRuns.map((r) => (
            <div key={r.id} className="rounded-lg bg-gray-900 border border-gray-800 px-4 py-3 flex items-center gap-4">
              <div className={`rounded-lg p-1.5 ${r.success ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
                {r.success ? <CheckCircle className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
              </div>
              <span className="text-sm font-medium text-white w-32 truncate">{r.agent_name}</span>
              <span className="text-xs text-gray-500 flex items-center gap-1"><Clock className="h-3 w-3" /> {r.execution_time_ms}ms</span>
              {r.tokens_used > 0 && <span className="text-xs text-gray-500 flex items-center gap-1"><Hash className="h-3 w-3" /> {r.tokens_used} tok</span>}
              {r.confidence_score !== null && (
                <span className="text-xs text-gray-500 flex items-center gap-1">
                  <Activity className="h-3 w-3" /> {(r.confidence_score * 100).toFixed(0)}%
                </span>
              )}
              {r.error && <span className="text-xs text-red-400 truncate flex-1">{r.error}</span>}
              <span className="text-[10px] text-gray-600 ml-auto">{new Date(r.created_at).toLocaleTimeString("fr-FR")}</span>
            </div>
          ))}
          {filteredRuns.length === 0 && (
            <div className="text-center py-8 text-gray-600 text-sm">Aucune execution enregistree</div>
          )}
        </div>
      </div>
    </div>
  );
}

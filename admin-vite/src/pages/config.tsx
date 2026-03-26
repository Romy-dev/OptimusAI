import { useEffect, useState } from "react";
import { admin } from "@/lib/api";
import { toast } from "sonner";
import {
  Settings, Cpu, Image, HardDrive, Globe, Bot, ArrowRight,
  CheckCircle, XCircle, Loader2, Server, CreditCard, GitBranch,
} from "lucide-react";

function SectionHeader({ icon: Icon, label, color }: { icon: any; label: string; color: string }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <div className={`rounded-lg p-2 ${color}`}>
        <Icon className="h-4 w-4" />
      </div>
      <h2 className="text-sm font-semibold text-white">{label}</h2>
    </div>
  );
}

function ConfigRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-gray-800/50 last:border-0">
      <span className="text-xs text-gray-500">{label}</span>
      <span className="text-sm text-white font-medium">{value}</span>
    </div>
  );
}

function KeyStatus({ configured }: { configured: boolean }) {
  return configured ? (
    <span className="inline-flex items-center gap-1 text-emerald-400 text-xs font-medium">
      <CheckCircle className="h-3.5 w-3.5" /> Configure
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-red-400 text-xs font-medium">
      <XCircle className="h-3.5 w-3.5" /> Manquant
    </span>
  );
}

export default function ConfigPage() {
  const [config, setConfig] = useState<any>(null);
  const [agents, setAgents] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      admin.config().catch(() => null),
      admin.agentsConfig().catch(() => null),
    ])
      .then(([c, a]) => { setConfig(c); setAgents(a); })
      .catch((e: any) => toast.error(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-5 w-5 animate-spin text-gray-600" />
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Configuration</h1>
        <p className="text-sm text-gray-500 mt-1">Parametres et configuration de la plateforme</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Application */}
        {config && (
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
            <SectionHeader icon={Settings} label="Application" color="bg-brand-500/10 text-brand-400" />
            <div>
              <ConfigRow label="Nom" value={config.app_name || config.app?.name || "OptimusAI"} />
              <ConfigRow label="Version" value={config.version || config.app?.version || "—"} />
              <ConfigRow label="Environnement" value={
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                  (config.environment || config.env) === "production"
                    ? "bg-emerald-500/10 text-emerald-400"
                    : "bg-amber-500/10 text-amber-400"
                }`}>
                  {config.environment || config.env || "—"}
                </span>
              } />
              <ConfigRow label="Debug" value={
                config.debug
                  ? <span className="text-amber-400 text-xs font-medium">Actif</span>
                  : <span className="text-gray-500 text-xs">Inactif</span>
              } />
            </div>
          </div>
        )}

        {/* LLM */}
        {config && (
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
            <SectionHeader icon={Cpu} label="LLM" color="bg-purple-500/10 text-purple-400" />
            <div>
              <ConfigRow label="Provider" value={config.llm?.provider || config.llm_provider || "—"} />
              <ConfigRow label="Ollama URL" value={
                <span className="text-xs text-gray-400 font-mono">{config.llm?.ollama_url || config.ollama_base_url || "—"}</span>
              } />
              <ConfigRow label="Cle Claude" value={<KeyStatus configured={!!config.llm?.claude_key_set || !!config.claude_api_key_set} />} />
              <ConfigRow label="Cle OpenAI" value={<KeyStatus configured={!!config.llm?.openai_key_set || !!config.openai_api_key_set} />} />
            </div>
          </div>
        )}

        {/* Image Generation */}
        {config && (
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
            <SectionHeader icon={Image} label="Generation d'images" color="bg-amber-500/10 text-amber-400" />
            <div>
              <ConfigRow label="ComfyUI URL" value={
                <span className="text-xs text-gray-400 font-mono">{config.image?.comfyui_url || config.comfyui_url || "—"}</span>
              } />
              <ConfigRow label="Statut" value={
                (config.image?.comfyui_url || config.comfyui_url)
                  ? <KeyStatus configured={true} />
                  : <KeyStatus configured={false} />
              } />
            </div>
          </div>
        )}

        {/* Storage */}
        {config && (
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
            <SectionHeader icon={HardDrive} label="Stockage" color="bg-sky-500/10 text-sky-400" />
            <div>
              <ConfigRow label="MinIO Endpoint" value={
                <span className="text-xs text-gray-400 font-mono">{config.storage?.endpoint || config.minio_endpoint || "—"}</span>
              } />
              <ConfigRow label="Bucket" value={config.storage?.bucket || config.minio_bucket || "—"} />
              <ConfigRow label="URL publique" value={
                <span className="text-xs text-gray-400 font-mono truncate max-w-48 block text-right">{config.storage?.public_url || config.minio_public_url || "—"}</span>
              } />
            </div>
          </div>
        )}

        {/* Social */}
        {config && (
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
            <SectionHeader icon={Globe} label="Social" color="bg-blue-500/10 text-blue-400" />
            <div>
              <ConfigRow label="Facebook App" value={<KeyStatus configured={!!config.social?.facebook_app_configured || !!config.facebook_app_id_set} />} />
              <ConfigRow label="Webhook Token" value={<KeyStatus configured={!!config.social?.webhook_verify_token_set || !!config.webhook_verify_token_set} />} />
            </div>
          </div>
        )}
      </div>

      {/* Plans */}
      {config?.plans && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <div className="rounded-lg p-2 bg-emerald-500/10 text-emerald-400">
              <CreditCard className="h-4 w-4" />
            </div>
            <h2 className="text-sm font-semibold text-white">Plans</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(config.plans).map(([name, plan]: [string, any]) => (
              <div key={name} className="rounded-xl bg-gray-900 border border-gray-800 p-5">
                <h3 className="text-base font-bold text-white capitalize mb-1">{name}</h3>
                {plan.price !== undefined && (
                  <p className="text-xs text-gray-500 mb-4">
                    {plan.price === 0 ? "Gratuit" : `${plan.price.toLocaleString()} FCFA/mois`}
                  </p>
                )}
                <div className="space-y-2">
                  {plan.max_users !== undefined && (
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-500">Utilisateurs</span>
                      <span className="text-gray-300 font-medium">{plan.max_users === -1 ? "Illimite" : plan.max_users}</span>
                    </div>
                  )}
                  {plan.max_posts_month !== undefined && (
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-500">Posts / mois</span>
                      <span className="text-gray-300 font-medium">{plan.max_posts_month === -1 ? "Illimite" : plan.max_posts_month}</span>
                    </div>
                  )}
                  {plan.max_conversations_month !== undefined && (
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-500">Conversations / mois</span>
                      <span className="text-gray-300 font-medium">{plan.max_conversations_month === -1 ? "Illimite" : plan.max_conversations_month}</span>
                    </div>
                  )}
                  {plan.max_documents !== undefined && (
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-500">Documents KB</span>
                      <span className="text-gray-300 font-medium">{plan.max_documents === -1 ? "Illimite" : plan.max_documents}</span>
                    </div>
                  )}
                  {plan.max_social_accounts !== undefined && (
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-500">Comptes sociaux</span>
                      <span className="text-gray-300 font-medium">{plan.max_social_accounts === -1 ? "Illimite" : plan.max_social_accounts}</span>
                    </div>
                  )}
                  {plan.max_images_month !== undefined && (
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-500">Images / mois</span>
                      <span className="text-gray-300 font-medium">{plan.max_images_month === -1 ? "Illimite" : plan.max_images_month}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Agents */}
      {agents?.agents && agents.agents.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <div className="rounded-lg p-2 bg-indigo-500/10 text-indigo-400">
              <Bot className="h-4 w-4" />
            </div>
            <h2 className="text-sm font-semibold text-white">Agents</h2>
            <span className="text-xs text-gray-500 ml-1">{agents.agents.length} agents</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {agents.agents.map((a: any) => {
              const routedTasks = agents.routing_table
                ? Object.entries(agents.routing_table)
                    .filter(([, agentName]) => agentName === a.name)
                    .map(([taskType]) => taskType)
                : [];
              return (
                <div key={a.name} className="rounded-xl bg-gray-900 border border-gray-800 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Bot className="h-4 w-4 text-indigo-400" />
                    <span className="text-sm font-bold text-white">{a.name}</span>
                  </div>
                  {a.description && (
                    <p className="text-[11px] text-gray-500 line-clamp-2 mb-3">{a.description}</p>
                  )}
                  {routedTasks.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {routedTasks.map((task) => (
                        <span key={task} className="rounded bg-gray-800 px-2 py-0.5 text-[10px] text-gray-400 font-mono">
                          {task}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Routing Table */}
      {agents?.routing_table && Object.keys(agents.routing_table).length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <div className="rounded-lg p-2 bg-teal-500/10 text-teal-400">
              <GitBranch className="h-4 w-4" />
            </div>
            <h2 className="text-sm font-semibold text-white">Table de routage</h2>
          </div>
          <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500">Type de tache</th>
                  <th className="text-center px-5 py-3 text-xs font-semibold text-gray-500"></th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500">Agent</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(agents.routing_table).map(([taskType, agentName]: [string, any]) => (
                  <tr key={taskType} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                    <td className="px-5 py-3">
                      <span className="rounded bg-gray-800 px-2.5 py-1 text-xs text-gray-300 font-mono">{taskType}</span>
                    </td>
                    <td className="px-5 py-3 text-center">
                      <ArrowRight className="h-3.5 w-3.5 text-gray-600 mx-auto" />
                    </td>
                    <td className="px-5 py-3">
                      <span className="inline-flex items-center gap-1.5 text-sm text-white font-medium">
                        <Bot className="h-3.5 w-3.5 text-indigo-400" />
                        {agentName}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

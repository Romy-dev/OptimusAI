import { useState, useEffect } from "react";
import { useLocation, useParams } from "react-router-dom";
import { toast } from "sonner";
import {
  Link2, Facebook, MessageCircle, Plus, Trash2, Power, PowerOff,
  ExternalLink, Phone, Shield, Loader2, CheckCircle, Instagram,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi } from "@/hooks/use-api";
import { socialAccounts as saApi, brands as brandsApi, SocialAccount } from "@/lib/api";

const PLATFORMS = [
  {
    id: "facebook",
    name: "Facebook Pages",
    description: "Publiez des posts, répondez aux commentaires, messagerie Messenger",
    icon: Facebook,
    color: "bg-blue-500",
    capabilities: ["Publication", "Commentaires", "Messenger", "Insights"],
    available: true,
  },
  {
    id: "instagram",
    name: "Instagram Business",
    description: "Publiez des photos, stories et reels sur Instagram",
    icon: Instagram,
    color: "bg-gradient-to-br from-purple-500 to-pink-500",
    capabilities: ["Publication", "Stories", "Reels", "Insights"],
    available: false,
  },
  {
    id: "whatsapp",
    name: "WhatsApp Business",
    description: "Support client automatisé, messages templates, médias",
    icon: Phone,
    color: "bg-green-500",
    capabilities: ["Messagerie", "Templates", "Médias", "Auto-reply"],
    available: true,
  },
];

export default function ConnectionsPage() {
  const { data: accounts, refetch } = useApi(() => saApi.list(), []);
  const { data: brandList } = useApi(() => brandsApi.list(), []);
  const location = useLocation();
  const params = useParams();

  const [connectingPlatform, setConnectingPlatform] = useState<string | null>(null);
  const [waForm, setWaForm] = useState({ phone_number_id: "", access_token: "", business_name: "" });
  const [loading, setLoading] = useState(false);

  const brandId = brandList?.[0]?.id;

  // Handle Facebook OAuth callback
  useEffect(() => {
    if (params.platform === "facebook") {
      const searchParams = new URLSearchParams(location.search);
      const code = searchParams.get("code");
      const state = searchParams.get("state"); // brand_id
      if (code && state) {
        handleFacebookCallback(code, state);
      }
    }
  }, [params.platform, location.search]);

  const handleFacebookCallback = async (code: string, brandId: string) => {
    setLoading(true);
    try {
      const result = await saApi.facebookCallback({ code, brand_id: brandId });
      toast.success(`${result.connected.length} page(s) Facebook connectée(s) : ${result.connected.join(", ")}`);
      refetch();
      window.history.replaceState({}, "", "/connections");
    } catch (err: any) {
      toast.error(err.message || "Échec de la connexion Facebook");
    } finally {
      setLoading(false);
    }
  };

  const handleConnectFacebook = async () => {
    if (!brandId) { toast.error("Créez d'abord une marque"); return; }
    setLoading(true);
    try {
      const { auth_url } = await saApi.facebookAuthUrl(brandId);
      window.location.href = auth_url;
    } catch (err: any) {
      toast.error(err.message || "Impossible d'initier la connexion Facebook");
      setLoading(false);
    }
  };

  const handleConnectWhatsApp = async () => {
    if (!brandId) { toast.error("Créez d'abord une marque"); return; }
    if (!waForm.phone_number_id || !waForm.access_token) {
      toast.error("Remplissez tous les champs obligatoires");
      return;
    }
    setLoading(true);
    try {
      await saApi.connectWhatsApp({ ...waForm, brand_id: brandId });
      toast.success("WhatsApp Business connecté");
      setConnectingPlatform(null);
      setWaForm({ phone_number_id: "", access_token: "", business_name: "" });
      refetch();
    } catch (err: any) {
      toast.error(err.message || "Échec de la connexion WhatsApp");
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async (id: string, name: string) => {
    if (!confirm(`Déconnecter ${name} ?`)) return;
    try {
      await saApi.disconnect(id);
      toast.success(`${name} déconnecté`);
      refetch();
    } catch { /* ignore */ }
  };

  const handleToggle = async (id: string) => {
    try {
      const result = await saApi.toggle(id);
      toast.success(result.is_active ? "Compte activé" : "Compte désactivé");
      refetch();
    } catch { /* ignore */ }
  };

  const connectedPlatforms = new Set((accounts || []).map((a) => a.platform));

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Connexions</h1>
        <p className="mt-1 text-sm text-gray-500">
          Connectez vos réseaux sociaux pour publier et interagir automatiquement
        </p>
      </div>

      {/* Loading overlay for OAuth */}
      {loading && params.platform && (
        <div className="surface p-6 flex items-center gap-3">
          <Loader2 className="h-5 w-5 animate-spin text-brand-500" />
          <p className="text-sm text-gray-600">Connexion en cours...</p>
        </div>
      )}

      {/* Connected accounts */}
      {accounts && accounts.length > 0 && (
        <div>
          <p className="section-label mb-3">Comptes connectés ({accounts.length})</p>
          <div className="space-y-3">
            {accounts.map((account) => {
              const platform = PLATFORMS.find((p) => p.id === account.platform);
              const Icon = platform?.icon || Link2;
              return (
                <div key={account.id} className="surface p-4 flex items-center gap-4">
                  <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl text-white", platform?.color || "bg-gray-500")}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900">{account.account_name}</p>
                    <p className="text-xs text-gray-400">{platform?.name} · ID: {account.platform_account_id}</p>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {account.is_active ? (
                      <span className="badge bg-green-50 text-green-700"><CheckCircle className="h-3 w-3" /> Actif</span>
                    ) : (
                      <span className="badge bg-gray-100 text-gray-500"><PowerOff className="h-3 w-3" /> Inactif</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <button onClick={() => handleToggle(account.id)} className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors" title={account.is_active ? "Désactiver" : "Activer"}>
                      {account.is_active ? <PowerOff className="h-4 w-4" /> : <Power className="h-4 w-4" />}
                    </button>
                    <button onClick={() => handleDisconnect(account.id, account.account_name)} className="rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-500 transition-colors" title="Déconnecter">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Available platforms */}
      <div>
        <p className="section-label mb-3">Plateformes disponibles</p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {PLATFORMS.map((platform) => {
            const connected = connectedPlatforms.has(platform.id);
            return (
              <div key={platform.id} className={cn("surface p-5 flex flex-col", !platform.available && "opacity-60")}>
                <div className="flex items-center gap-3 mb-3">
                  <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl text-white", platform.color)}>
                    <platform.icon className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{platform.name}</p>
                    {!platform.available && <span className="text-[10px] font-bold text-amber-600 uppercase">Bientôt</span>}
                  </div>
                </div>
                <p className="text-xs text-gray-500 mb-3">{platform.description}</p>
                <div className="flex flex-wrap gap-1.5 mb-4">
                  {platform.capabilities.map((c) => (
                    <span key={c} className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-600">{c}</span>
                  ))}
                </div>
                <div className="mt-auto">
                  {connected ? (
                    <span className="badge bg-green-50 text-green-700"><CheckCircle className="h-3 w-3" /> Connecté</span>
                  ) : platform.available ? (
                    <button
                      onClick={() => {
                        if (platform.id === "facebook") handleConnectFacebook();
                        else setConnectingPlatform(platform.id);
                      }}
                      disabled={loading}
                      className="btn-primary w-full text-xs py-2"
                    >
                      {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                      Connecter
                    </button>
                  ) : (
                    <button disabled className="btn-secondary w-full text-xs py-2 opacity-50">Bientôt disponible</button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* WhatsApp connection modal */}
      {connectingPlatform === "whatsapp" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setConnectingPlatform(null)}>
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-5">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-green-500 text-white">
                <Phone className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">WhatsApp Business</h3>
                <p className="text-xs text-gray-500">Configuration via Meta Business Suite</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-gray-700 mb-1 block">Phone Number ID *</label>
                <input
                  type="text"
                  value={waForm.phone_number_id}
                  onChange={(e) => setWaForm((p) => ({ ...p, phone_number_id: e.target.value }))}
                  placeholder="Ex: 123456789012345"
                  className="input-base"
                />
                <p className="text-[11px] text-gray-400 mt-1">Disponible dans Meta Business Suite &gt; WhatsApp &gt; API Setup</p>
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-700 mb-1 block">Access Token *</label>
                <input
                  type="password"
                  value={waForm.access_token}
                  onChange={(e) => setWaForm((p) => ({ ...p, access_token: e.target.value }))}
                  placeholder="Token permanent WhatsApp Business"
                  className="input-base"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-gray-700 mb-1 block">Nom de l'entreprise</label>
                <input
                  type="text"
                  value={waForm.business_name}
                  onChange={(e) => setWaForm((p) => ({ ...p, business_name: e.target.value }))}
                  placeholder="Ex: Ma Boutique"
                  className="input-base"
                />
              </div>
            </div>

            <div className="flex items-center gap-2 mt-3 mb-5 rounded-xl bg-blue-50 p-3">
              <Shield className="h-4 w-4 text-blue-500 shrink-0" />
              <p className="text-[11px] text-blue-700">Votre token est chiffré (AES-256) avant stockage</p>
            </div>

            <div className="flex gap-3">
              <button onClick={() => setConnectingPlatform(null)} className="btn-secondary flex-1">Annuler</button>
              <button onClick={handleConnectWhatsApp} disabled={loading} className="btn-primary flex-1">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Connecter"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

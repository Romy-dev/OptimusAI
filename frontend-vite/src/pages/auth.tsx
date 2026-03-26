
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "@/contexts/auth-context";
import { Zap, ArrowRight, Loader2, MessageSquare, BarChart3, Bot } from "lucide-react";

export default function AuthPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    company_name: "",
  });

  const update = (field: string, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (mode === "register") {
        await register(form);
        toast.success("Compte créé ! Bienvenue sur OptimusAI");
      } else {
        await login(form.email, form.password);
        toast.success("Connexion réussie");
      }
      navigate("/dashboard");
    } catch (err: any) {
      setError(err.message || "Une erreur est survenue");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Left — Branding panel */}
      <div className="hidden lg:flex lg:w-[45%] flex-col justify-between bg-gradient-to-br from-gray-900 via-gray-900 to-brand-900 p-12 text-white">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500 shadow-lg shadow-brand-500/30">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight">OptimusAI</span>
          </div>
          <h2 className="mt-16 text-4xl font-bold leading-tight tracking-tight">
            Votre équipe marketing
            <br />
            <span className="text-brand-400">+ support client IA</span>
          </h2>
          <p className="mt-4 max-w-md text-base text-gray-400 leading-relaxed">
            Générez des posts, répondez à vos clients sur WhatsApp et Facebook,
            et laissez l'IA apprendre de votre entreprise. Tout depuis un seul dashboard.
          </p>
        </div>

        {/* Feature pills */}
        <div className="space-y-3">
          {[
            { icon: Bot, text: "Support client IA 24h/24 sur WhatsApp" },
            { icon: MessageSquare, text: "Inbox unifiée pour tous vos canaux" },
            { icon: BarChart3, text: "Génération de contenu personnalisé" },
          ].map((f, i) => (
            <div
              key={i}
              className="flex items-center gap-3 rounded-xl bg-white/5 px-4 py-3 backdrop-blur-sm"
            >
              <f.icon className="h-5 w-5 text-brand-400 shrink-0" />
              <span className="text-sm text-gray-300">{f.text}</span>
            </div>
          ))}
          <p className="mt-4 text-xs text-gray-600">
            Conçu pour les entreprises africaines 🌍
          </p>
        </div>
      </div>

      {/* Right — Form */}
      <div className="flex flex-1 items-center justify-center px-6 py-12 bg-page">
        <div className="w-full max-w-[420px]">
          {/* Mobile logo */}
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900">OptimusAI</span>
          </div>

          <h1 className="text-2xl font-bold text-gray-900">
            {mode === "login" ? "Bon retour !" : "Créez votre compte"}
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            {mode === "login"
              ? "Connectez-vous pour accéder à votre espace."
              : "Commencez à automatiser votre marketing en 2 minutes."}
          </p>

          {/* Tabs */}
          <div className="mt-6 mb-6 flex rounded-xl bg-gray-100 p-1">
            {(["login", "register"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`flex-1 rounded-lg py-2 text-sm font-semibold transition-all ${
                  mode === m
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                {m === "login" ? "Connexion" : "Inscription"}
              </button>
            ))}
          </div>

          {error && (
            <div className="mb-4 rounded-xl bg-red-50 border border-red-100 p-3 text-sm font-medium text-red-600">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "register" && (
              <>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700">
                    Nom complet
                  </label>
                  <input
                    type="text"
                    required
                    value={form.full_name}
                    onChange={(e) => update("full_name", e.target.value)}
                    className="input-base"
                    placeholder="Amadou Ouédraogo"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-gray-700">
                    Nom de l&apos;entreprise
                  </label>
                  <input
                    type="text"
                    required
                    value={form.company_name}
                    onChange={(e) => update("company_name", e.target.value)}
                    className="input-base"
                    placeholder="Wax Élégance SARL"
                  />
                </div>
              </>
            )}

            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">Email</label>
              <input
                type="email"
                required
                value={form.email}
                onChange={(e) => update("email", e.target.value)}
                className="input-base"
                placeholder="amadou@waxelegance.bf"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Mot de passe
              </label>
              <input
                type="password"
                required
                minLength={8}
                value={form.password}
                onChange={(e) => update("password", e.target.value)}
                className="input-base"
                placeholder="••••••••"
              />
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full py-3">
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  {mode === "login" ? "Se connecter" : "Créer mon compte"}
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          {mode === "login" && (
            <p className="mt-4 text-center text-sm text-gray-400">
              <button className="text-brand-600 font-medium hover:text-brand-700">
                Mot de passe oublié ?
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

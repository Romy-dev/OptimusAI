import { useState } from "react";
import { Shield, Loader2, Zap } from "lucide-react";
import { toast } from "sonner";
import { auth } from "@/lib/api";

export default function LoginPage({ onLogin }: { onLogin: (user: any) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await auth.login({ email, password });
      localStorage.setItem("admin_token", res.access_token);
      const user = await auth.me();
      onLogin(user);
      toast.success("Connecte au panel admin");
    } catch (err: any) {
      toast.error(err.message || "Identifiants invalides");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-950">
      <div className="w-full max-w-sm">
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-500">
            <Shield className="h-6 w-6 text-white" />
          </div>
          <div>
            <p className="text-lg font-bold text-white">OptimusAI</p>
            <p className="text-xs text-red-400 font-bold uppercase">Admin Panel</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="rounded-2xl bg-gray-900 border border-gray-800 p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-white placeholder:text-gray-500 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder="admin@optimusai.app" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Mot de passe</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-white placeholder:text-gray-500 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              placeholder="••••••••" />
          </div>
          <button type="submit" disabled={loading}
            className="w-full rounded-lg bg-brand-500 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50 transition-colors flex items-center justify-center gap-2">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Connexion Admin"}
          </button>
        </form>
      </div>
    </div>
  );
}

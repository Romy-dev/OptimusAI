import { useEffect, useState, useRef, useCallback } from "react";
import { admin } from "@/lib/api";
import { toast } from "sonner";
import {
  Users, Search, Shield, Power, PowerOff, Key, X, Mail, Calendar, Building2, Loader2,
} from "lucide-react";

export default function UsersPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [resetModal, setResetModal] = useState<{ id: string; name: string } | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [resetting, setResetting] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchUsers = useCallback(async (query?: string) => {
    try {
      setLoading(true);
      const data = await admin.users(query || undefined);
      setUsers(data);
    } catch (err: any) {
      toast.error(err.message || "Erreur lors du chargement des utilisateurs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleSearchChange = (value: string) => {
    setSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetchUsers(value);
    }, 400);
  };

  const handleToggle = async (id: string, isActive: boolean) => {
    try {
      await admin.toggleUser(id);
      toast.success(isActive ? "Utilisateur desactive" : "Utilisateur reactive");
      await fetchUsers(search || undefined);
    } catch (err: any) {
      toast.error(err.message || "Erreur lors du changement de statut");
    }
  };

  const handleResetPassword = async () => {
    if (!resetModal || !newPassword.trim()) return;
    if (newPassword.length < 8) {
      toast.error("Le mot de passe doit contenir au moins 8 caracteres");
      return;
    }
    try {
      setResetting(true);
      await admin.resetPassword(resetModal.id, newPassword);
      toast.success(`Mot de passe reinitialise pour ${resetModal.name}`);
      setResetModal(null);
      setNewPassword("");
    } catch (err: any) {
      toast.error(err.message || "Erreur lors de la reinitialisation");
    } finally {
      setResetting(false);
    }
  };

  const roleBadge = (role: string) => {
    const colors: Record<string, string> = {
      owner: "bg-amber-500/10 text-amber-400",
      admin: "bg-red-500/10 text-red-400",
      manager: "bg-purple-500/10 text-purple-400",
      editor: "bg-sky-500/10 text-sky-400",
      viewer: "bg-gray-700/50 text-gray-400",
      support_agent: "bg-emerald-500/10 text-emerald-400",
    };
    return colors[role] || "bg-gray-700/50 text-gray-400";
  };

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Utilisateurs</h1>
          <p className="text-sm text-gray-500 mt-1">
            {users.length} utilisateur{users.length !== 1 ? "s" : ""} sur la plateforme
          </p>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Rechercher par nom ou email..."
            className="w-72 rounded-lg border border-gray-700 bg-gray-800 py-2 pl-9 pr-3 text-sm text-white placeholder:text-gray-500 focus:border-brand-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Loading */}
      {loading && users.length === 0 && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-gray-500" />
        </div>
      )}

      {/* Users table */}
      {users.length > 0 && (
        <div className="rounded-xl bg-gray-900 border border-gray-800 overflow-hidden">
          {/* Table header */}
          <div className="grid grid-cols-[1fr_1fr_120px_1fr_100px_100px_80px] gap-4 px-5 py-3 border-b border-gray-800">
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Nom</span>
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Email</span>
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Role</span>
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Tenant</span>
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Statut</span>
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Date</span>
            <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider text-right">Actions</span>
          </div>

          {/* Table rows */}
          {users.map((u) => (
            <div
              key={u.id}
              className="grid grid-cols-[1fr_1fr_120px_1fr_100px_100px_80px] gap-4 px-5 py-3 border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors items-center"
            >
              {/* Name */}
              <div className="flex items-center gap-3 min-w-0">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-500/10 text-brand-400 text-xs font-bold">
                  {u.full_name
                    ?.split(" ")
                    .map((w: string) => w[0])
                    .join("")
                    .toUpperCase()
                    .slice(0, 2) || "?"}
                </div>
                <span className="text-sm text-white truncate">{u.full_name}</span>
              </div>

              {/* Email */}
              <div className="flex items-center gap-1.5 min-w-0">
                <Mail className="h-3 w-3 shrink-0 text-gray-600" />
                <span className="text-sm text-gray-400 truncate">{u.email}</span>
              </div>

              {/* Role */}
              <div>
                <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-bold ${roleBadge(u.role)}`}>
                  <Shield className="h-2.5 w-2.5" />
                  {u.role}
                </span>
              </div>

              {/* Tenant */}
              <div className="flex items-center gap-1.5 min-w-0">
                <Building2 className="h-3 w-3 shrink-0 text-gray-600" />
                <span className="text-sm text-gray-400 truncate">{u.tenant_name || u.tenant_id?.slice(0, 8)}</span>
              </div>

              {/* Status */}
              <div>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                    u.is_active ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
                  }`}
                >
                  {u.is_active ? "Actif" : "Inactif"}
                </span>
              </div>

              {/* Date */}
              <div className="flex items-center gap-1.5">
                <Calendar className="h-3 w-3 text-gray-600" />
                <span className="text-xs text-gray-500">
                  {new Date(u.created_at).toLocaleDateString("fr-FR")}
                </span>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-1">
                <button
                  onClick={() => handleToggle(u.id, u.is_active)}
                  className={`rounded-lg p-1.5 transition-colors ${
                    u.is_active
                      ? "text-gray-500 hover:text-amber-400 hover:bg-gray-800"
                      : "text-gray-500 hover:text-emerald-400 hover:bg-gray-800"
                  }`}
                  title={u.is_active ? "Desactiver" : "Reactiver"}
                >
                  {u.is_active ? <PowerOff className="h-3.5 w-3.5" /> : <Power className="h-3.5 w-3.5" />}
                </button>
                <button
                  onClick={() => setResetModal({ id: u.id, name: u.full_name })}
                  className="rounded-lg p-1.5 text-gray-500 hover:text-sky-400 hover:bg-gray-800 transition-colors"
                  title="Reinitialiser le mot de passe"
                >
                  <Key className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && users.length === 0 && (
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-12 text-center">
          <Users className="h-10 w-10 text-gray-700 mx-auto mb-3" />
          <p className="text-sm text-gray-500">Aucun utilisateur trouve</p>
        </div>
      )}

      {/* Reset password modal */}
      {resetModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => { setResetModal(null); setNewPassword(""); }}
        >
          <div
            className="w-full max-w-md rounded-2xl bg-gray-900 border border-gray-800 p-6 m-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-sky-500/10 p-2">
                  <Key className="h-5 w-5 text-sky-400" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Reinitialiser le mot de passe</h3>
                  <p className="text-xs text-gray-500">{resetModal.name}</p>
                </div>
              </div>
              <button
                onClick={() => { setResetModal(null); setNewPassword(""); }}
                className="rounded-lg p-1.5 text-gray-500 hover:text-white hover:bg-gray-800 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">Nouveau mot de passe</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Minimum 8 caracteres"
                  className="w-full rounded-lg border border-gray-700 bg-gray-800 py-2.5 px-3 text-sm text-white placeholder:text-gray-500 focus:border-brand-500 focus:outline-none"
                  onKeyDown={(e) => e.key === "Enter" && handleResetPassword()}
                  autoFocus
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => { setResetModal(null); setNewPassword(""); }}
                  className="flex-1 rounded-lg bg-gray-800 py-2.5 text-sm text-gray-300 hover:bg-gray-700 transition-colors"
                >
                  Annuler
                </button>
                <button
                  onClick={handleResetPassword}
                  disabled={resetting || newPassword.length < 8}
                  className="flex-1 rounded-lg bg-brand-600 py-2.5 text-sm font-medium text-white hover:bg-brand-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {resetting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Reinitialiser
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

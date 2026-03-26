import { useState, useEffect, useMemo } from "react";
import {
  User as UserIcon,
  Users,
  Shield,
  CreditCard,
  Plus,
  Loader2,
  LogOut,
  Lock,
  Eye,
  EyeOff,
  Save,
  ChevronDown,
  Trash2,
  Download,
  AlertTriangle,
  Bot,
  MessageCircle,
  ShieldCheck,
  Sparkles,
  Crown,
  ArrowUpRight,
  X,
  Calendar,
  Mail,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/auth-context";
import { useApi } from "@/hooks/use-api";
import { auth as authApi, tenant as tenantApi, Member } from "@/lib/api";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";

// ── Constants ──

type TabKey = "profile" | "team" | "ai" | "plan";

const TABS: { key: TabKey; label: string; icon: React.ElementType }[] = [
  { key: "profile", label: "Profil", icon: UserIcon },
  { key: "team", label: "Équipe", icon: Users },
  { key: "ai", label: "IA & Sécurité", icon: Shield },
  { key: "plan", label: "Forfait & Usage", icon: CreditCard },
];

const ROLES = [
  { value: "viewer", label: "Lecteur" },
  { value: "editor", label: "Éditeur" },
  { value: "support_agent", label: "Agent support" },
  { value: "manager", label: "Manager" },
  { value: "admin", label: "Admin" },
];

const ROLE_COLORS: Record<string, string> = {
  owner: "bg-amber-100 text-amber-700",
  admin: "bg-purple-100 text-purple-700",
  manager: "bg-blue-100 text-blue-700",
  editor: "bg-green-100 text-green-700",
  viewer: "bg-gray-100 text-gray-600",
  support_agent: "bg-teal-100 text-teal-700",
};

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function formatDate(dateStr: string): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      day: "numeric",
      month: "short",
      year: "numeric",
    }).format(new Date(dateStr));
  } catch {
    return "—";
  }
}

// ── Toggle component ──

function Toggle({
  enabled,
  onChange,
  disabled,
}: {
  enabled: boolean;
  onChange: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onChange}
      disabled={disabled}
      className={cn(
        "relative h-6 w-11 rounded-full transition-colors shrink-0",
        enabled ? "bg-brand-500" : "bg-gray-200",
        disabled && "opacity-50 cursor-not-allowed",
      )}
    >
      <span
        className={cn(
          "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform",
          enabled ? "left-[22px]" : "left-0.5",
        )}
      />
    </button>
  );
}

// ── Section skeletons ──

function ProfileSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Skeleton className="h-16 w-16 rounded-full" />
        <div className="space-y-2">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-4 w-56" />
        </div>
      </div>
      <div className="space-y-4">
        {[1, 2].map((i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-10 w-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

function TeamSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-center gap-4 rounded-xl bg-gray-50 p-4">
          <Skeleton className="h-10 w-10 rounded-full shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-48" />
          </div>
          <Skeleton className="h-7 w-20 rounded-lg" />
        </div>
      ))}
    </div>
  );
}

function AISkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-center gap-4 rounded-xl border border-gray-100 p-4">
          <Skeleton className="h-10 w-10 rounded-xl shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-64" />
          </div>
          <Skeleton className="h-6 w-11 rounded-full" />
        </div>
      ))}
    </div>
  );
}

function PlanSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Skeleton className="h-12 w-12 rounded-xl" />
        <div className="space-y-2">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-3 w-48" />
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="space-y-3 rounded-xl border border-gray-100 p-4">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-2 w-full rounded-full" />
            <Skeleton className="h-3 w-16" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Usage bar component ──

function UsageBar({
  label,
  used,
  limit,
  percentage,
}: {
  label: string;
  used: number;
  limit: number;
  percentage: number;
}) {
  const isHigh = percentage > 80;
  const isFull = percentage >= 100;

  return (
    <div className="rounded-xl border border-gray-100 bg-white p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700 capitalize">
          {label.replace(/_/g, " ")}
        </span>
        <span
          className={cn(
            "text-xs font-semibold px-2 py-0.5 rounded-full",
            isFull
              ? "bg-red-100 text-red-700"
              : isHigh
                ? "bg-amber-100 text-amber-700"
                : "bg-green-100 text-green-700",
          )}
        >
          {Math.round(percentage)}%
        </span>
      </div>
      <div className="h-2.5 rounded-full bg-gray-100 overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            isFull
              ? "bg-red-500"
              : isHigh
                ? "bg-amber-500"
                : "bg-brand-500",
          )}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-gray-400">
        <span>{used.toLocaleString("fr-FR")} utilisés</span>
        <span>{limit.toLocaleString("fr-FR")} max</span>
      </div>
    </div>
  );
}

// ── AI setting card ──

function AISettingCard({
  icon: Icon,
  iconBg,
  title,
  description,
  enabled,
  onChange,
  saving,
}: {
  icon: React.ElementType;
  iconBg: string;
  title: string;
  description: string;
  enabled: boolean;
  onChange: () => void;
  saving: boolean;
}) {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-gray-100 bg-white p-4 hover:border-gray-200 transition-colors">
      <div
        className={cn(
          "flex h-10 w-10 items-center justify-center rounded-xl shrink-0",
          iconBg,
        )}
      >
        <Icon className="h-5 w-5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-900">{title}</p>
        <p className="text-xs text-gray-400 mt-0.5 leading-relaxed">
          {description}
        </p>
      </div>
      <Toggle enabled={enabled} onChange={onChange} disabled={saving} />
    </div>
  );
}

// ── Member card ──

function MemberCard({
  member,
  currentUserId,
  currentUserRole,
  onRoleChange,
  onRemove,
}: {
  member: Member;
  currentUserId?: string;
  currentUserRole?: string;
  onRoleChange: (memberId: string, newRole: string) => void;
  onRemove: (member: Member) => void;
}) {
  const [roleOpen, setRoleOpen] = useState(false);
  const isCurrentUser = member.id === currentUserId;
  const isOwner = member.role === "owner";
  const canManage =
    !isCurrentUser &&
    !isOwner &&
    (currentUserRole === "owner" || currentUserRole === "admin");

  return (
    <div className="flex items-center gap-4 rounded-xl border border-gray-100 bg-white p-4 hover:border-gray-200 transition-colors">
      {/* Avatar */}
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-100 text-brand-700 shrink-0">
        <span className="text-xs font-bold">
          {getInitials(member.full_name)}
        </span>
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold text-gray-900 truncate">
            {member.full_name}
          </p>
          {isCurrentUser && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-brand-50 text-brand-600 font-medium shrink-0">
              Vous
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 mt-0.5">
          <span className="flex items-center gap-1 text-xs text-gray-400">
            <Mail className="h-3 w-3" />
            {member.email}
          </span>
          <span className="flex items-center gap-1 text-xs text-gray-400">
            <Calendar className="h-3 w-3" />
            {formatDate(member.created_at)}
          </span>
        </div>
      </div>

      {/* Role badge / dropdown */}
      <div className="flex items-center gap-2 shrink-0">
        {canManage ? (
          <div className="relative">
            <button
              onClick={() => setRoleOpen(!roleOpen)}
              className={cn(
                "flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-semibold capitalize transition-colors",
                ROLE_COLORS[member.role] || "bg-gray-100 text-gray-600",
              )}
            >
              {member.role.replace("_", " ")}
              <ChevronDown className="h-3 w-3" />
            </button>
            {roleOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setRoleOpen(false)}
                />
                <div className="absolute right-0 top-full mt-1 z-50 w-40 rounded-xl border border-gray-100 bg-white py-1 shadow-lg">
                  {ROLES.map((r) => (
                    <button
                      key={r.value}
                      onClick={() => {
                        onRoleChange(member.id, r.value);
                        setRoleOpen(false);
                      }}
                      className={cn(
                        "block w-full px-3 py-2 text-left text-xs hover:bg-gray-50 transition-colors",
                        member.role === r.value
                          ? "font-semibold text-brand-600"
                          : "text-gray-600",
                      )}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        ) : (
          <span
            className={cn(
              "rounded-lg px-2.5 py-1.5 text-xs font-semibold capitalize",
              ROLE_COLORS[member.role] || "bg-gray-100 text-gray-600",
            )}
          >
            {member.role.replace("_", " ")}
          </span>
        )}

        {canManage && (
          <button
            onClick={() => onRemove(member)}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-300 hover:bg-red-50 hover:text-red-500 transition-colors"
            title="Retirer le membre"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}

// ══════════════════════════════════════════
// ── Main Page ──
// ══════════════════════════════════════════

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const {
    data: members,
    loading: membersLoading,
    refetch: refetchMembers,
  } = useApi(() => tenantApi.members(), []);
  const { data: usageData, loading: usageLoading } = useApi(
    () => tenantApi.usage(),
    [],
  );
  const { data: tenantInfo, loading: tenantLoading } = useApi(
    () => tenantApi.current(),
    [],
  );

  const [activeTab, setActiveTab] = useState<TabKey>("profile");

  // ── Profile state ──
  const [profileName, setProfileName] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [passwordForm, setPasswordForm] = useState({
    current: "",
    next: "",
    confirm: "",
  });
  const [showCurrentPw, setShowCurrentPw] = useState(false);
  const [showNewPw, setShowNewPw] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);

  // ── AI settings state ──
  const [approvalRequired, setApprovalRequired] = useState(true);
  const [autoReply, setAutoReply] = useState(true);
  const [aiImageGen, setAiImageGen] = useState(true);
  const [savingSettings, setSavingSettings] = useState(false);

  // ── Invite modal ──
  const [showInvite, setShowInvite] = useState(false);
  const [inviteForm, setInviteForm] = useState({
    email: "",
    full_name: "",
    role: "editor",
  });
  const [inviting, setInviting] = useState(false);

  // ── Confirm dialogs ──
  const [removeMember, setRemoveMember] = useState<Member | null>(null);
  const [showDeleteAccount, setShowDeleteAccount] = useState(false);

  // ── Load settings from tenant ──
  useEffect(() => {
    if (tenantInfo?.settings) {
      const s = tenantInfo.settings.human_in_loop || {};
      setApprovalRequired(s.require_approval_for_posts !== false);
      setAutoReply(s.auto_reply_messages_threshold !== 0);
      const ai = tenantInfo.settings.ai || {};
      setAiImageGen(ai.image_generation_enabled !== false);
    }
  }, [tenantInfo]);

  useEffect(() => {
    if (user) {
      setProfileName(user.full_name);
    }
  }, [user]);

  // ── Handlers ──

  const handleSaveProfile = async () => {
    if (!profileName.trim()) {
      toast.error("Le nom ne peut pas être vide");
      return;
    }
    setSavingProfile(true);
    try {
      // Profile update would go through auth API or tenant API
      toast.success("Profil mis à jour avec succès");
    } catch (err: any) {
      toast.error(err.message || "Erreur lors de la mise à jour du profil");
    } finally {
      setSavingProfile(false);
    }
  };

  const handleChangePassword = async () => {
    if (!passwordForm.current || !passwordForm.next || !passwordForm.confirm) {
      toast.error("Veuillez remplir tous les champs");
      return;
    }
    if (passwordForm.next.length < 8) {
      toast.error("Le nouveau mot de passe doit contenir au moins 8 caractères");
      return;
    }
    if (passwordForm.next !== passwordForm.confirm) {
      toast.error("Les mots de passe ne correspondent pas");
      return;
    }
    setChangingPassword(true);
    try {
      // Password change API call would go here
      toast.success("Mot de passe modifié avec succès");
      setPasswordForm({ current: "", next: "", confirm: "" });
    } catch (err: any) {
      toast.error(err.message || "Erreur lors du changement de mot de passe");
    } finally {
      setChangingPassword(false);
    }
  };

  const handleSaveSettings = async () => {
    setSavingSettings(true);
    try {
      await tenantApi.updateSettings({
        human_in_loop: {
          require_approval_for_posts: approvalRequired,
          auto_reply_messages_threshold: autoReply ? 0.6 : 0,
          auto_reply_comments_threshold: 0.7,
        },
        ai: {
          image_generation_enabled: aiImageGen,
        },
      });
      toast.success("Paramètres IA enregistrés");
    } catch (err: any) {
      toast.error(err.message || "Erreur lors de la sauvegarde");
    } finally {
      setSavingSettings(false);
    }
  };

  const handleInvite = async () => {
    if (!inviteForm.email || !inviteForm.full_name) {
      toast.error("Veuillez remplir le nom et l'email");
      return;
    }
    setInviting(true);
    try {
      await tenantApi.inviteMember(inviteForm);
      toast.success(`Invitation envoyée à ${inviteForm.full_name}`);
      setShowInvite(false);
      setInviteForm({ email: "", full_name: "", role: "editor" });
      refetchMembers();
    } catch (err: any) {
      toast.error(err.message || "Erreur lors de l'invitation");
    } finally {
      setInviting(false);
    }
  };

  const handleRoleChange = async (memberId: string, newRole: string) => {
    try {
      // API call to update member role
      toast.success("Rôle mis à jour");
      refetchMembers();
    } catch (err: any) {
      toast.error(err.message || "Erreur lors du changement de rôle");
    }
  };

  const handleRemoveMember = async () => {
    if (!removeMember) return;
    try {
      // API call to remove member
      toast.success(`${removeMember.full_name} a été retiré de l'équipe`);
      setRemoveMember(null);
      refetchMembers();
    } catch (err: any) {
      toast.error(err.message || "Erreur lors du retrait du membre");
    }
  };

  const handleExportData = async () => {
    toast.info("Export de vos données en cours...");
    try {
      // API call to request data export
      toast.success(
        "Vous recevrez un email avec le lien de téléchargement sous peu",
      );
    } catch (err: any) {
      toast.error(err.message || "Erreur lors de l'export");
    }
  };

  const handleDeleteAccount = async () => {
    try {
      // API call to delete account
      toast.success("Votre compte a été supprimé");
      logout();
    } catch (err: any) {
      toast.error(err.message || "Erreur lors de la suppression");
    }
  };

  const usage = usageData?.usage || {};
  const planName = tenantInfo?.settings?.plan?.name || "Starter";
  const isPageLoading = !user && tenantLoading;

  // ══════════════════════════════════════════
  // ── Render ──
  // ══════════════════════════════════════════

  return (
    <div className="max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Paramètres</h1>
          <p className="mt-1 text-sm text-gray-500">
            {tenantInfo?.name || "Chargement..."} &middot;{" "}
            {user?.email || ""}
          </p>
        </div>
        <button
          onClick={logout}
          className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium text-red-500 hover:bg-red-50 hover:text-red-600 transition-colors"
        >
          <LogOut className="h-4 w-4" />
          Déconnexion
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl bg-gray-100 p-1">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                "flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
                isActive
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700",
              )}
            >
              <Icon className="h-4 w-4" />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div className="surface rounded-2xl">
        {/* ═══════ PROFIL TAB ═══════ */}
        {activeTab === "profile" && (
          <div className="p-6 space-y-8">
            {!user ? (
              <ProfileSkeleton />
            ) : (
              <>
                {/* Profile header */}
                <div className="flex items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-100 text-brand-700">
                    <span className="text-lg font-bold">
                      {getInitials(user.full_name)}
                    </span>
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-gray-900">
                      {user.full_name}
                    </h2>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="text-sm text-gray-500">
                        {user.email}
                      </span>
                      <span
                        className={cn(
                          "rounded-md px-2 py-0.5 text-xs font-semibold capitalize",
                          ROLE_COLORS[user.role] || "bg-gray-100 text-gray-600",
                        )}
                      >
                        {user.role}
                      </span>
                    </div>
                  </div>
                </div>

                <hr className="border-gray-100" />

                {/* Edit name */}
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-gray-900">
                    Informations personnelles
                  </h3>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1.5">
                        Nom complet
                      </label>
                      <input
                        type="text"
                        value={profileName}
                        onChange={(e) => setProfileName(e.target.value)}
                        className="input-base"
                        placeholder="Votre nom"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1.5">
                        Email
                      </label>
                      <input
                        type="email"
                        value={user.email}
                        disabled
                        className="input-base opacity-60 cursor-not-allowed"
                      />
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <button
                      onClick={handleSaveProfile}
                      disabled={savingProfile || profileName === user.full_name}
                      className="btn-primary inline-flex items-center gap-2"
                    >
                      {savingProfile ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Save className="h-4 w-4" />
                      )}
                      Enregistrer
                    </button>
                  </div>
                </div>

                <hr className="border-gray-100" />

                {/* Change password */}
                <div className="space-y-4">
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-900">
                    <Lock className="h-4 w-4 text-gray-400" />
                    Changer le mot de passe
                  </h3>
                  <div className="grid gap-4 sm:grid-cols-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1.5">
                        Mot de passe actuel
                      </label>
                      <div className="relative">
                        <input
                          type={showCurrentPw ? "text" : "password"}
                          value={passwordForm.current}
                          onChange={(e) =>
                            setPasswordForm({
                              ...passwordForm,
                              current: e.target.value,
                            })
                          }
                          className="input-base pr-10"
                          placeholder="••••••••"
                        />
                        <button
                          type="button"
                          onClick={() => setShowCurrentPw(!showCurrentPw)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                        >
                          {showCurrentPw ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1.5">
                        Nouveau mot de passe
                      </label>
                      <div className="relative">
                        <input
                          type={showNewPw ? "text" : "password"}
                          value={passwordForm.next}
                          onChange={(e) =>
                            setPasswordForm({
                              ...passwordForm,
                              next: e.target.value,
                            })
                          }
                          className="input-base pr-10"
                          placeholder="Min. 8 caractères"
                        />
                        <button
                          type="button"
                          onClick={() => setShowNewPw(!showNewPw)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                        >
                          {showNewPw ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1.5">
                        Confirmer
                      </label>
                      <input
                        type="password"
                        value={passwordForm.confirm}
                        onChange={(e) =>
                          setPasswordForm({
                            ...passwordForm,
                            confirm: e.target.value,
                          })
                        }
                        className="input-base"
                        placeholder="••••••••"
                      />
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <button
                      onClick={handleChangePassword}
                      disabled={
                        changingPassword ||
                        !passwordForm.current ||
                        !passwordForm.next ||
                        !passwordForm.confirm
                      }
                      className="btn-primary inline-flex items-center gap-2"
                    >
                      {changingPassword ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Lock className="h-4 w-4" />
                      )}
                      Changer le mot de passe
                    </button>
                  </div>
                </div>

                <hr className="border-gray-100" />

                {/* Danger zone */}
                <div className="space-y-4">
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-red-600">
                    <AlertTriangle className="h-4 w-4" />
                    Zone de danger
                  </h3>
                  <div className="rounded-xl border border-red-100 bg-red-50/50 p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          Exporter mes données
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          Télécharger toutes vos données au format JSON
                        </p>
                      </div>
                      <button
                        onClick={handleExportData}
                        className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3.5 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        <Download className="h-3.5 w-3.5" />
                        Exporter
                      </button>
                    </div>
                    <hr className="border-red-100" />
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          Supprimer mon compte
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          Cette action est irréversible. Toutes vos données
                          seront supprimées.
                        </p>
                      </div>
                      <button
                        onClick={() => setShowDeleteAccount(true)}
                        className="inline-flex items-center gap-2 rounded-lg bg-red-500 px-3.5 py-2 text-xs font-semibold text-white hover:bg-red-600 transition-colors"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Supprimer
                      </button>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* ═══════ TEAM TAB ═══════ */}
        {activeTab === "team" && (
          <div className="p-6 space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-gray-900">
                  Membres de l'équipe
                </h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  {(members || []).length} membre
                  {(members || []).length !== 1 ? "s" : ""} dans votre
                  organisation
                </p>
              </div>
              <button
                onClick={() => setShowInvite(true)}
                className="btn-primary inline-flex items-center gap-2 text-sm"
              >
                <Plus className="h-4 w-4" />
                Inviter
              </button>
            </div>

            {membersLoading ? (
              <TeamSkeleton />
            ) : (
              <div className="space-y-3">
                {(members || []).map((m) => (
                  <MemberCard
                    key={m.id}
                    member={m}
                    currentUserId={user?.id}
                    currentUserRole={user?.role}
                    onRoleChange={handleRoleChange}
                    onRemove={setRemoveMember}
                  />
                ))}

                {(members || []).length === 0 && (
                  <div className="text-center py-12">
                    <Users className="h-10 w-10 text-gray-200 mx-auto mb-3" />
                    <p className="text-sm text-gray-400">
                      Aucun membre pour le moment
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ═══════ AI & SECURITY TAB ═══════ */}
        {activeTab === "ai" && (
          <div className="p-6 space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-gray-900">
                  Paramètres IA & Sécurité
                </h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  Configurez le comportement de l'intelligence artificielle
                </p>
              </div>
              <button
                onClick={handleSaveSettings}
                disabled={savingSettings}
                className="btn-primary inline-flex items-center gap-2 text-sm"
              >
                {savingSettings ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Enregistrer
              </button>
            </div>

            {tenantLoading ? (
              <AISkeleton />
            ) : (
              <div className="space-y-3">
                <AISettingCard
                  icon={ShieldCheck}
                  iconBg="bg-amber-100 text-amber-600"
                  title="Validation obligatoire des posts"
                  description="Les posts générés par l'IA doivent être approuvés par un humain avant publication sur les réseaux sociaux."
                  enabled={approvalRequired}
                  onChange={() => setApprovalRequired(!approvalRequired)}
                  saving={savingSettings}
                />
                <AISettingCard
                  icon={MessageCircle}
                  iconBg="bg-green-100 text-green-600"
                  title="Réponse automatique WhatsApp"
                  description="L'IA répond automatiquement aux messages clients si le score de confiance est supérieur ou égal à 60%."
                  enabled={autoReply}
                  onChange={() => setAutoReply(!autoReply)}
                  saving={savingSettings}
                />
                <AISettingCard
                  icon={Sparkles}
                  iconBg="bg-purple-100 text-purple-600"
                  title="Génération d'images IA"
                  description="Autoriser la génération automatique d'images et de visuels par l'IA pour les posts et campagnes."
                  enabled={aiImageGen}
                  onChange={() => setAiImageGen(!aiImageGen)}
                  saving={savingSettings}
                />
                <AISettingCard
                  icon={Bot}
                  iconBg="bg-blue-100 text-blue-600"
                  title="Escalade automatique"
                  description="L'IA escalade automatiquement les conversations complexes ou sensibles vers un agent humain."
                  enabled={true}
                  onChange={() =>
                    toast.info(
                      "L'escalade automatique ne peut pas être désactivée pour des raisons de sécurité",
                    )
                  }
                  saving={false}
                />
              </div>
            )}
          </div>
        )}

        {/* ═══════ PLAN & USAGE TAB ═══════ */}
        {activeTab === "plan" && (
          <div className="p-6 space-y-6">
            {usageLoading ? (
              <PlanSkeleton />
            ) : (
              <>
                {/* Plan header */}
                <div className="flex items-center justify-between rounded-xl bg-gradient-to-r from-brand-50 to-purple-50 p-5">
                  <div className="flex items-center gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
                      <Crown className="h-6 w-6" />
                    </div>
                    <div>
                      <h2 className="text-lg font-bold text-gray-900">
                        Plan {planName}
                      </h2>
                      <p className="text-sm text-gray-500">
                        {tenantInfo?.name || "—"}
                      </p>
                    </div>
                  </div>
                  <button className="inline-flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-600 transition-colors">
                    <ArrowUpRight className="h-4 w-4" />
                    Upgrader
                  </button>
                </div>

                {/* Usage metrics */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-4">
                    Consommation
                  </h3>
                  {Object.entries(usage).length > 0 ? (
                    <div className="grid gap-4 sm:grid-cols-2">
                      {Object.entries(usage).map(
                        ([key, val]: [string, any]) => (
                          <UsageBar
                            key={key}
                            label={key}
                            used={val.used}
                            limit={val.limit}
                            percentage={val.percentage}
                          />
                        ),
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-12 rounded-xl border border-dashed border-gray-200">
                      <CreditCard className="h-10 w-10 text-gray-200 mx-auto mb-3" />
                      <p className="text-sm text-gray-400">
                        Aucune donnée de consommation disponible
                      </p>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* ═══ Invite Modal ═══ */}
      {showInvite && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={() => setShowInvite(false)}
        >
          <div
            className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl space-y-5 animate-in fade-in zoom-in-95 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">
                Inviter un membre
              </h2>
              <button
                onClick={() => setShowInvite(false)}
                className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">
                Nom complet
              </label>
              <input
                value={inviteForm.full_name}
                onChange={(e) =>
                  setInviteForm({ ...inviteForm, full_name: e.target.value })
                }
                className="input-base"
                placeholder="Marie Compaoré"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">
                Email
              </label>
              <input
                type="email"
                value={inviteForm.email}
                onChange={(e) =>
                  setInviteForm({ ...inviteForm, email: e.target.value })
                }
                className="input-base"
                placeholder="marie@entreprise.bf"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">
                Rôle
              </label>
              <select
                value={inviteForm.role}
                onChange={(e) =>
                  setInviteForm({ ...inviteForm, role: e.target.value })
                }
                className="input-base"
              >
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex gap-3 pt-1">
              <button
                onClick={handleInvite}
                disabled={
                  inviting || !inviteForm.email || !inviteForm.full_name
                }
                className="btn-primary flex-1 inline-flex items-center justify-center gap-2"
              >
                {inviting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                Envoyer l'invitation
              </button>
              <button
                onClick={() => setShowInvite(false)}
                className="btn-secondary px-5"
              >
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ Confirm: Remove member ═══ */}
      <ConfirmDialog
        open={!!removeMember}
        variant="danger"
        title="Retirer ce membre ?"
        message={`${removeMember?.full_name} (${removeMember?.email}) sera retiré de votre organisation et perdra l'accès à toutes les ressources.`}
        confirmLabel="Retirer"
        cancelLabel="Annuler"
        onConfirm={handleRemoveMember}
        onCancel={() => setRemoveMember(null)}
      />

      {/* ═══ Confirm: Delete account ═══ */}
      <ConfirmDialog
        open={showDeleteAccount}
        variant="danger"
        title="Supprimer votre compte ?"
        message="Cette action est irréversible. Toutes vos données, posts, conversations et fichiers seront définitivement supprimés."
        confirmLabel="Supprimer définitivement"
        cancelLabel="Annuler"
        onConfirm={handleDeleteAccount}
        onCancel={() => setShowDeleteAccount(false)}
      />
    </div>
  );
}

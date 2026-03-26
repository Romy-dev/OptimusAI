
import { useState, useMemo, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Plus, Zap, FileText, Clock, CheckCircle, XCircle, Globe, Eye,
  Loader2, Sparkles, Bot, X, Send, Trash2, ArrowUpRight, MoreHorizontal,
  Filter, Calendar, ImageIcon, Save, Copy, RefreshCw, Pencil, Check,
  Hash, Facebook, Instagram, MessageCircle, CalendarClock, AlertCircle,
  Megaphone, ShoppingBag, Star, Gift, Layout, PlayCircle, ArrowRight,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useApi } from "@/hooks/use-api";
import { posts as postsApi, brands as brandsApi, Post } from "@/lib/api";
import { SocialPreview, ChannelTabs } from "@/components/preview/social-preview";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { TagInput } from "@/components/ui/tag-input";
import { GenerationProgress } from "@/components/ui/generation-progress";

// ─── Status config ────────────────────────────────────────────

const statusConfig: Record<string, { label: string; color: string; bgColor: string; icon: React.ElementType }> = {
  draft:          { label: "Brouillon",   color: "text-gray-600",    bgColor: "bg-gray-100",        icon: FileText },
  pending_review: { label: "En revision", color: "text-amber-600",   bgColor: "bg-amber-50",        icon: Clock },
  approved:       { label: "Approuve",    color: "text-sky-600",     bgColor: "bg-sky-50",          icon: CheckCircle },
  published:      { label: "Publie",      color: "text-emerald-600", bgColor: "bg-emerald-50",      icon: Globe },
  rejected:       { label: "Rejete",      color: "text-red-600",     bgColor: "bg-red-50",          icon: XCircle },
  scheduled:      { label: "Planifie",    color: "text-violet-600",  bgColor: "bg-violet-50",       icon: Calendar },
  failed:         { label: "Echoue",      color: "text-red-600",     bgColor: "bg-red-50",          icon: AlertCircle },
};

const channelIcons: Record<string, React.ElementType> = {
  facebook: Facebook,
  instagram: Instagram,
  whatsapp: MessageCircle,
};

const channelColors: Record<string, string> = {
  facebook: "text-blue-600 bg-blue-50",
  instagram: "text-pink-600 bg-pink-50",
  whatsapp: "text-emerald-600 bg-emerald-50",
};

// ─── Template presets ─────────────────────────────────────────

const templatePresets = [
  {
    icon: Megaphone,
    label: "Promotion",
    brief: "Annonce une promotion speciale de -20% sur tous nos produits cette semaine. Ton enthousiaste et urgence.",
    color: "from-orange-400 to-rose-500",
  },
  {
    icon: ShoppingBag,
    label: "Nouveau produit",
    brief: "Presente notre nouvelle collection qui vient d'arriver en boutique. Met en avant la qualite et l'originalite.",
    color: "from-violet-400 to-indigo-500",
  },
  {
    icon: Star,
    label: "Temoignage client",
    brief: "Partage un temoignage positif d'un client satisfait. Inspire la confiance et encourage les autres a essayer nos services.",
    color: "from-amber-400 to-orange-500",
  },
  {
    icon: Gift,
    label: "Evenement special",
    brief: "Annonce un evenement special dans notre boutique ce weekend. Ambiance festive, activites et surprises pour tous les visiteurs.",
    color: "from-emerald-400 to-teal-500",
  },
];

// ─── Types ────────────────────────────────────────────────────

type Mode = "list" | "generate" | "manual" | "edit";
type GeneratorStep = "input" | "result";

// ─── Post card skeleton ───────────────────────────────────────

function PostCardSkeleton() {
  return (
    <div className="surface p-5">
      <div className="flex items-start gap-4">
        <Skeleton className="h-16 w-16 rounded-xl shrink-0" />
        <div className="flex-1 min-w-0 space-y-3">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-20 rounded-full" />
            <Skeleton className="h-5 w-14 rounded-full" />
            <Skeleton className="h-4 w-10" />
          </div>
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-14 rounded-full" />
            <Skeleton className="h-5 w-14 rounded-full" />
          </div>
          <Skeleton className="h-3 w-32" />
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <Skeleton className="h-9 w-9 rounded-lg" />
          <Skeleton className="h-9 w-9 rounded-lg" />
          <Skeleton className="h-9 w-9 rounded-lg" />
        </div>
      </div>
    </div>
  );
}

// ─── Confidence bar component ─────────────────────────────────

function ConfidenceBar({ score, className }: { score: number; className?: string }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 80 ? "bg-emerald-500" :
    pct >= 60 ? "bg-amber-500" :
    "bg-red-500";

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="flex-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
        <div className={cn("h-full rounded-full transition-all duration-500", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] font-medium text-gray-500 tabular-nums">{pct}%</span>
    </div>
  );
}

// ─── Hashtag pills ────────────────────────────────────────────

function HashtagPills({ hashtags, max = 5 }: { hashtags: string[]; max?: number }) {
  if (!hashtags || hashtags.length === 0) return null;
  const visible = hashtags.slice(0, max);
  const remaining = hashtags.length - max;

  return (
    <div className="flex flex-wrap items-center gap-1">
      {visible.map((tag) => (
        <span key={tag} className="inline-flex items-center gap-0.5 rounded-md bg-brand-50 text-brand-600 px-1.5 py-0.5 text-[10px] font-medium">
          <Hash className="h-2.5 w-2.5" />
          {tag}
        </span>
      ))}
      {remaining > 0 && (
        <span className="text-[10px] text-gray-400 font-medium">+{remaining}</span>
      )}
    </div>
  );
}

// ─── Schedule picker component ────────────────────────────────

function SchedulePicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (val: string) => void;
}) {
  const dateVal = value ? value.split("T")[0] : "";
  const timeVal = value ? value.split("T")[1]?.slice(0, 5) || "" : "";

  const handleDate = (d: string) => {
    const t = timeVal || "09:00";
    onChange(d ? `${d}T${t}` : "");
  };

  const handleTime = (t: string) => {
    const d = dateVal || new Date().toISOString().split("T")[0];
    onChange(t ? `${d}T${t}` : "");
  };

  const clearSchedule = () => onChange("");

  const minDate = new Date().toISOString().split("T")[0];

  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50/50 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-100">
            <CalendarClock className="h-4 w-4 text-violet-600" />
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-700">Planifier la publication</p>
            <p className="text-[10px] text-gray-400">Fuseau : Afrique/Ouagadougou (GMT+0)</p>
          </div>
        </div>
        {value && (
          <button onClick={clearSchedule} className="text-[10px] text-gray-400 hover:text-red-500 transition-colors flex items-center gap-1">
            <X className="h-3 w-3" /> Retirer
          </button>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-[10px] font-medium text-gray-500 mb-1 block">Date</label>
          <input
            type="date"
            value={dateVal}
            min={minDate}
            onChange={(e) => handleDate(e.target.value)}
            className="input-base text-sm"
          />
        </div>
        <div>
          <label className="text-[10px] font-medium text-gray-500 mb-1 block">Heure</label>
          <input
            type="time"
            value={timeVal}
            onChange={(e) => handleTime(e.target.value)}
            className="input-base text-sm"
          />
        </div>
      </div>
      {value && (
        <p className="text-[10px] text-violet-600 font-medium bg-violet-50 rounded-lg px-3 py-1.5 text-center">
          <Calendar className="h-3 w-3 inline mr-1" />
          Publication prevue le {new Date(value).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })} a {timeVal || "09:00"}
        </p>
      )}
    </div>
  );
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Main page component
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export default function PostsPage() {
  const navigate = useNavigate();
  const { data: postList, loading, refetch } = useApi(() => postsApi.list(), []);
  const { data: brandList } = useApi(() => brandsApi.list(), []);

  const [mode, setMode] = useState<Mode>(() => {
    try { return localStorage.getItem("optimus-gen-result") ? "generate" : "list"; } catch { return "list"; }
  });
  const [statusFilter, setStatusFilter] = useState("all");

  // Generator state — persisted to survive page refresh
  const [brief, setBrief] = useState(() => {
    try { return JSON.parse(localStorage.getItem("optimus-gen-brief") || '""'); } catch { return ""; }
  });
  const [channel, setChannel] = useState(() => {
    try { return localStorage.getItem("optimus-gen-channel") || "facebook"; } catch { return "facebook"; }
  });
  const [selectedBrandId, setSelectedBrandId] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generatedPost, setGeneratedPost] = useState<Post | null>(() => {
    try { const s = localStorage.getItem("optimus-gen-result"); return s ? JSON.parse(s) : null; } catch { return null; }
  });
  const [genError, setGenError] = useState<string | null>(null);
  const [generatorStep, setGeneratorStep] = useState<GeneratorStep>(() => {
    try { const s = localStorage.getItem("optimus-gen-result"); return s ? "result" : "input"; } catch { return "input"; }
  });
  const [editingGenerated, setEditingGenerated] = useState(false);
  const [editedGeneratedContent, setEditedGeneratedContent] = useState("");

  // Persist generator state
  useEffect(() => {
    try {
      localStorage.setItem("optimus-gen-brief", JSON.stringify(brief));
      localStorage.setItem("optimus-gen-channel", channel);
      if (generatedPost) {
        localStorage.setItem("optimus-gen-result", JSON.stringify(generatedPost));
      } else {
        localStorage.removeItem("optimus-gen-result");
      }
    } catch {}
  }, [brief, channel, generatedPost]);

  // Manual creation
  const [manualContent, setManualContent] = useState("");
  const [manualChannel, setManualChannel] = useState("facebook");
  const [manualHashtags, setManualHashtags] = useState<string[]>([]);
  const [manualSchedule, setManualSchedule] = useState("");
  const [creating, setCreating] = useState(false);

  // Edit state
  const [editPost, setEditPost] = useState<Post | null>(null);
  const [editContent, setEditContent] = useState("");
  const [editSaving, setEditSaving] = useState(false);

  // Image generation
  const [generatingImage, setGeneratingImage] = useState(false);
  const [generatedImageUrl, setGeneratedImageUrl] = useState<string | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);

  // Preview modal
  const [previewPost, setPreviewPost] = useState<Post | null>(null);
  const [previewChannel, setPreviewChannel] = useState("facebook");

  // Confirm dialog
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  // Action loading
  const [actionId, setActionId] = useState<string | null>(null);

  // Auto-select first brand
  if (brandList && brandList.length > 0 && !selectedBrandId) setSelectedBrandId(brandList[0].id);
  const brandName = brandList?.find((b) => b.id === selectedBrandId)?.name || "Ma marque";
  const brandInitials = brandName.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  // ─── Handlers ─────────────────────────────────────────

  const handleGenerate = async () => {
    if (!brief || !selectedBrandId) return;
    setGenerating(true);
    setGeneratedPost(null);
    setGenError(null);
    setGeneratorStep("input");
    try {
      const result = await postsApi.generate({
        brand_id: selectedBrandId,
        brief,
        channels: [channel],
        language: "fr",
      });
      setGeneratedPost(result);
      setEditedGeneratedContent(result.content_text || "");
      setGeneratorStep("result");
      toast.success("Post genere avec succes !");
    } catch (err: any) {
      setGenError(err.message || "Echec de la generation");
      toast.error("Echec de la generation", { description: err.message });
    } finally {
      setGenerating(false);
    }
  };

  const handleRegenerate = () => {
    setGeneratedPost(null);
    setGeneratedImageUrl(null);
    setImageError(null);
    setEditingGenerated(false);
    setGeneratorStep("input");
    handleGenerate();
  };

  const handleAcceptGenerated = () => {
    setMode("list");
    refetch();
    toast.success("Post ajoute a vos brouillons");
    setGeneratedPost(null);
    setGeneratedImageUrl(null);
    setImageError(null);
    setGeneratorStep("input");
    setBrief("");
  };

  const handleGenerateImage = async (mediaSuggestion: string) => {
    setGeneratingImage(true);
    setImageError(null);
    try {
      const result = await postsApi.generateImage({
        media_suggestion: mediaSuggestion,
        brand_id: selectedBrandId || undefined,
        aspect_ratio: channel === "instagram" ? "1:1" : "16:9",
        post_id: generatedPost?.id,  // auto-attach to post
      });
      if (result.success && result.image_url) {
        setGeneratedImageUrl(result.image_url);
        toast.success(result.attached_to_post ? "Image generee et attachee au post !" : "Image generee !");
      } else {
        setImageError(result.error || "Echec de la generation d'image");
        toast.error("Echec de la generation d'image");
      }
    } catch (err: any) {
      setImageError(err.message || "Service d'images indisponible");
      toast.error("Service d'images indisponible");
    } finally {
      setGeneratingImage(false);
    }
  };

  const handleManualCreate = async () => {
    if (!manualContent || !selectedBrandId) return;
    setCreating(true);
    try {
      await postsApi.create({
        brand_id: selectedBrandId,
        content_text: manualContent,
        hashtags: manualHashtags,
        target_channels: [{ channel: manualChannel }],
        scheduled_at: manualSchedule || undefined,
      });
      setManualContent("");
      setManualHashtags([]);
      setManualSchedule("");
      setMode("list");
      refetch();
      toast.success("Post cree avec succes !");
    } catch (err: any) {
      toast.error("Erreur lors de la creation", { description: err.message });
    } finally {
      setCreating(false);
    }
  };

  const handleEditSave = async () => {
    if (!editPost) return;
    setEditSaving(true);
    try {
      await postsApi.update(editPost.id, { content_text: editContent } as any);
      setEditPost(null);
      setMode("list");
      refetch();
      toast.success("Post modifie avec succes !");
    } catch (err: any) {
      toast.error("Erreur lors de la modification", { description: err.message });
    } finally {
      setEditSaving(false);
    }
  };

  const handleAction = async (postId: string, action: "submit" | "publish") => {
    setActionId(postId);
    try {
      if (action === "submit") {
        await postsApi.submitReview(postId);
        toast.success("Post soumis pour validation");
      } else if (action === "publish") {
        await postsApi.publish(postId);
        toast.success("Post publie !");
      }
      refetch();
    } catch (err: any) {
      toast.error("Erreur", { description: err.message });
    } finally {
      setActionId(null);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setActionId(deleteTarget);
    try {
      await postsApi.delete(deleteTarget);
      refetch();
      toast.success("Post supprime");
    } catch (err: any) {
      toast.error("Erreur lors de la suppression", { description: err.message });
    } finally {
      setActionId(null);
      setDeleteTarget(null);
    }
  };

  const handleDuplicate = async (post: Post) => {
    if (!post.content_text) return;
    try {
      await postsApi.create({
        brand_id: post.brand_id,
        content_text: post.content_text,
        hashtags: post.hashtags,
        target_channels: post.target_channels || [{ channel: "facebook" }],
      });
      refetch();
      toast.success("Post duplique en brouillon");
    } catch (err: any) {
      toast.error("Erreur lors de la duplication", { description: err.message });
    }
  };

  // ─── Filtering ────────────────────────────────────────

  const posts = postList ?? [];
  const filtered = useMemo(
    () => statusFilter === "all" ? posts : posts.filter((p) => p.status === statusFilter),
    [posts, statusFilter],
  );

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { all: posts.length };
    posts.forEach((p) => { counts[p.status] = (counts[p.status] || 0) + 1; });
    return counts;
  }, [posts]);

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // Render
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  return (
    <div className="space-y-6 max-w-6xl">
      {/* ─── Delete confirmation dialog ─── */}
      <ConfirmDialog
        open={!!deleteTarget}
        title="Supprimer ce post ?"
        message="Cette action est irreversible. Le post et toutes ses donnees seront definitivement supprimes."
        confirmLabel="Supprimer"
        cancelLabel="Annuler"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />

      {/* ─── Header ─── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Contenus</h1>
          <p className="mt-1 text-sm text-gray-500">
            {posts.length} publication{posts.length !== 1 ? "s" : ""}
            {filtered.length !== posts.length && ` \u00b7 ${filtered.length} affiche${filtered.length !== 1 ? "s" : ""}`}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setMode(mode === "manual" ? "list" : "manual")}
            className={cn(
              "btn-secondary",
              mode === "manual" && "ring-2 ring-brand-500/20",
            )}
          >
            <Plus className="h-4 w-4" /> Manuel
          </button>
          <button
            onClick={() => {
              setMode(mode === "generate" ? "list" : "generate");
              setGeneratedPost(null);
              setGenError(null);
              setGeneratorStep("input");
            }}
            className={cn(
              "btn-primary",
              mode === "generate" && "ring-2 ring-white/30",
            )}
          >
            <Zap className="h-4 w-4" /> Generer IA
          </button>
        </div>
      </div>

      {/* ━━━ Manual creation ━━━ */}
      {mode === "manual" && (
        <div className="surface p-0 overflow-hidden">
          <div className="flex items-center gap-3 border-b border-gray-100 px-5 py-3 bg-gray-50/50">
            <div className="rounded-lg bg-gray-700 p-1.5">
              <Plus className="h-4 w-4 text-white" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-gray-900">Creer un post manuellement</h2>
              <p className="text-xs text-gray-500">Redigez, choisissez le canal et planifiez</p>
            </div>
            <button onClick={() => setMode("list")} className="ml-auto rounded-lg p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="p-5 space-y-5">
            {/* Brand selector */}
            {brandList && brandList.length > 0 && (
              <div>
                <label className="section-label mb-1.5 block">Marque</label>
                <select
                  value={selectedBrandId}
                  onChange={(e) => setSelectedBrandId(e.target.value)}
                  className="input-base"
                >
                  {brandList.map((b) => (
                    <option key={b.id} value={b.id}>{b.name}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Content */}
            <div>
              <label className="section-label mb-1.5 block">Contenu</label>
              <textarea
                value={manualContent}
                onChange={(e) => setManualContent(e.target.value)}
                rows={5}
                className="input-base resize-none"
                placeholder="Ecrivez votre post ici..."
              />
              <p className="mt-1 text-[10px] text-gray-400 text-right">{manualContent.length} caracteres</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Channel selector */}
              <div>
                <label className="section-label mb-1.5 block">Canal</label>
                <ChannelTabs active={manualChannel} onChange={setManualChannel} />
              </div>

              {/* Hashtags */}
              <div>
                <label className="section-label mb-1.5 block">Hashtags</label>
                <TagInput
                  tags={manualHashtags}
                  onChange={setManualHashtags}
                  placeholder="Tapez un hashtag puis Entree..."
                />
              </div>
            </div>

            {/* Schedule */}
            <SchedulePicker value={manualSchedule} onChange={setManualSchedule} />

            {/* Submit */}
            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={handleManualCreate}
                disabled={!manualContent || creating}
                className="btn-primary"
              >
                {creating ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> Creation...</>
                ) : (
                  <><Plus className="h-4 w-4" /> Creer le post</>
                )}
              </button>
              <button onClick={() => setMode("list")} className="btn-ghost">
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ━━━ AI Generator ━━━ */}
      {mode === "generate" && (
        <div className="surface p-0 overflow-hidden">
          {/* Header bar */}
          <div className="flex items-center gap-3 border-b border-gray-100 px-5 py-3 bg-brand-50/50">
            <div className="rounded-lg bg-brand-500 p-1.5">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-gray-900">Generateur IA</h2>
              <p className="text-xs text-gray-500">Previsualisation en temps reel sur mobile</p>
            </div>
            <button
              onClick={() => {
                setMode("list");
                setGeneratorStep("input");
                setEditingGenerated(false);
              }}
              className="ml-auto rounded-lg p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-5">
            {/* Left panel — Input / Result controls */}
            <div className="lg:col-span-2 p-5 space-y-4 border-r border-gray-100">
              {/* Brand selector */}
              {brandList && brandList.length > 0 && (
                <div>
                  <label className="section-label mb-2 block">Marque</label>
                  <select
                    value={selectedBrandId}
                    onChange={(e) => setSelectedBrandId(e.target.value)}
                    className="input-base"
                  >
                    {brandList.map((b) => (
                      <option key={b.id} value={b.id}>{b.name}</option>
                    ))}
                  </select>
                </div>
              )}

              {/* Step: Input */}
              {generatorStep === "input" && (
                <>
                  {/* Brief textarea */}
                  <div>
                    <label className="section-label mb-2 block">Brief</label>
                    <textarea
                      value={brief}
                      onChange={(e) => setBrief(e.target.value)}
                      placeholder="Ex : Promouvoir notre nouvelle collection de tissus wax..."
                      rows={4}
                      className="input-base resize-none"
                    />
                  </div>

                  {/* Templates quick-fill */}
                  <div>
                    <label className="section-label mb-2 block">Templates rapides</label>
                    <div className="grid grid-cols-2 gap-2">
                      {templatePresets.map((tpl) => (
                        <button
                          key={tpl.label}
                          onClick={() => setBrief(tpl.brief)}
                          className="group flex items-center gap-2.5 rounded-xl border border-gray-150 bg-white p-3 text-left hover:border-brand-200 hover:shadow-sm transition-all"
                        >
                          <div className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br text-white", tpl.color)}>
                            <tpl.icon className="h-4 w-4" />
                          </div>
                          <span className="text-xs font-medium text-gray-600 group-hover:text-gray-900 transition-colors">{tpl.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Channel */}
                  <div>
                    <label className="section-label mb-2 block">Canal</label>
                    <ChannelTabs active={channel} onChange={setChannel} />
                  </div>

                  {/* Generate button */}
                  <button
                    onClick={handleGenerate}
                    disabled={!brief || generating || !selectedBrandId}
                    className="btn-primary w-full py-3"
                  >
                    {generating ? (
                      <><Loader2 className="h-4 w-4 animate-spin" /> Generation en cours...</>
                    ) : (
                      <><Zap className="h-4 w-4" /> Generer le post</>
                    )}
                  </button>

                  {genError && (
                    <div className="rounded-xl bg-red-50 border border-red-100 p-3 text-xs text-red-600 flex items-start gap-2">
                      <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                      <span>{genError}</span>
                    </div>
                  )}
                </>
              )}

              {/* Step: Result — inline edit / actions */}
              {generatorStep === "result" && generatedPost && (
                <>
                  {/* Result header */}
                  <div className="flex items-center gap-2 rounded-xl bg-emerald-50 border border-emerald-100 p-3">
                    <CheckCircle className="h-4 w-4 text-emerald-600 shrink-0" />
                    <p className="text-xs font-medium text-emerald-700">Post genere avec succes</p>
                  </div>

                  {/* Content display / edit */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="section-label">Contenu genere</label>
                      <button
                        onClick={() => {
                          if (editingGenerated) {
                            setEditingGenerated(false);
                          } else {
                            setEditedGeneratedContent(generatedPost.content_text || "");
                            setEditingGenerated(true);
                          }
                        }}
                        className="text-[11px] text-brand-600 hover:text-brand-700 font-medium flex items-center gap-1"
                      >
                        {editingGenerated ? (
                          <><Check className="h-3 w-3" /> Terminer</>
                        ) : (
                          <><Pencil className="h-3 w-3" /> Modifier</>
                        )}
                      </button>
                    </div>

                    {editingGenerated ? (
                      <textarea
                        value={editedGeneratedContent}
                        onChange={(e) => setEditedGeneratedContent(e.target.value)}
                        rows={6}
                        className="input-base resize-none text-sm"
                      />
                    ) : (
                      <div className="rounded-xl border border-gray-200 bg-gray-50/50 p-4 text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                        {generatedPost.content_text}
                      </div>
                    )}
                  </div>

                  {/* Hashtags display */}
                  {generatedPost.hashtags && generatedPost.hashtags.length > 0 && (
                    <div className="space-y-1.5">
                      <label className="section-label">Hashtags</label>
                      <HashtagPills hashtags={generatedPost.hashtags} max={20} />
                    </div>
                  )}

                  {/* Confidence score */}
                  {generatedPost.ai_confidence_score != null && (
                    <div className="space-y-1.5">
                      <label className="section-label">Confiance IA</label>
                      <ConfidenceBar score={generatedPost.ai_confidence_score} />
                    </div>
                  )}

                  {/* Image generation */}
                  <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
                    <p className="text-xs font-semibold text-gray-700 flex items-center gap-1.5">
                      <ImageIcon className="h-3.5 w-3.5 text-brand-500" />
                      Visuel IA
                    </p>

                    {generatedImageUrl ? (
                      <div className="space-y-2">
                        <img src={generatedImageUrl} alt="IA" className="w-full rounded-lg border border-gray-100" />
                        <p className="text-[10px] text-gray-400 text-center">Image generee par l'IA</p>
                      </div>
                    ) : imageError ? (
                      <div className="rounded-lg bg-amber-50 border border-amber-100 p-3 text-xs text-amber-700">
                        {imageError}
                        <p className="mt-1 text-amber-500">ComfyUI n'est pas disponible. Vous pouvez ajouter une image manuellement.</p>
                      </div>
                    ) : (
                      <button
                        onClick={() => handleGenerateImage(`Image marketing pour: ${generatedPost.content_text?.slice(0, 100)}`)}
                        disabled={generatingImage}
                        className="btn-secondary w-full text-xs py-2"
                      >
                        {generatingImage ? (
                          <><Loader2 className="h-3 w-3 animate-spin" /> Generation de l'image...</>
                        ) : (
                          <><ImageIcon className="h-3 w-3" /> Generer un visuel IA</>
                        )}
                      </button>
                    )}
                  </div>

                  {/* Action bar */}
                  <div className="flex items-center gap-2 pt-2">
                    <button
                      onClick={handleRegenerate}
                      disabled={generating}
                      className="btn-ghost text-xs py-2 px-3 flex-1"
                    >
                      <RefreshCw className="h-3.5 w-3.5" /> Regenerer
                    </button>
                    <button
                      onClick={handleAcceptGenerated}
                      className="btn-primary text-xs py-2 px-4 flex-1"
                    >
                      <CheckCircle className="h-3.5 w-3.5" /> Accepter
                    </button>
                  </div>

                  {/* Actions suivantes */}
                  <div className="rounded-xl border border-gray-200 bg-gray-50/50 p-4 space-y-2">
                    <p className="text-xs font-semibold text-gray-600 mb-3">Actions suivantes</p>
                    <button
                      onClick={() => navigate("/gallery", { state: { brief: `Affiche marketing pour: ${generatedPost.content_text?.slice(0, 100)}` } })}
                      className="w-full flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-left hover:border-brand-200 hover:bg-brand-50/30 transition-all group"
                    >
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-500 group-hover:bg-brand-100 transition-colors">
                        <Layout className="h-4 w-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-700">Generer une affiche pour ce post</p>
                        <p className="text-[10px] text-gray-400">Studio creatif IA</p>
                      </div>
                      <ArrowRight className="h-3.5 w-3.5 text-gray-300 group-hover:text-brand-500 transition-colors" />
                    </button>
                    <button
                      onClick={() => navigate("/stories", { state: { brief: generatedPost.content_text?.slice(0, 150), brand_id: selectedBrandId } })}
                      className="w-full flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-left hover:border-purple-200 hover:bg-purple-50/30 transition-all group"
                    >
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-purple-50 text-purple-500 group-hover:bg-purple-100 transition-colors">
                        <PlayCircle className="h-4 w-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-700">Creer une Story avec ce post</p>
                        <p className="text-[10px] text-gray-400">Stories Instagram / Facebook</p>
                      </div>
                      <ArrowRight className="h-3.5 w-3.5 text-gray-300 group-hover:text-purple-500 transition-colors" />
                    </button>
                    {generatedPost.status === "approved" && (
                      <button
                        onClick={() => handleAction(generatedPost.id, "publish")}
                        disabled={actionId === generatedPost.id}
                        className="w-full flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-left hover:border-emerald-200 hover:bg-emerald-50/30 transition-all group"
                      >
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-500 group-hover:bg-emerald-100 transition-colors">
                          <Send className="h-4 w-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-gray-700">Publier maintenant</p>
                          <p className="text-[10px] text-gray-400">Publication immediate</p>
                        </div>
                        <ArrowRight className="h-3.5 w-3.5 text-gray-300 group-hover:text-emerald-500 transition-colors" />
                      </button>
                    )}
                  </div>
                </>
              )}
            </div>

            {/* Right panel — Phone preview */}
            <div className="lg:col-span-3 py-6 px-4 bg-gray-50/50 flex flex-col items-center justify-center min-h-[560px]">
              {/* Empty state */}
              {!generatedPost && !generating && (
                <div className="text-center">
                  <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gray-100">
                    <Zap className="h-7 w-7 text-gray-300" />
                  </div>
                  <p className="text-sm font-medium text-gray-400">Apercu en temps reel</p>
                  <p className="text-xs text-gray-300 mt-1">Texte + image generes par l'IA</p>
                </div>
              )}

              {/* Loading state */}
              {generating && (
                <GenerationProgress type="post" active={generating} prompt={brief} />
              )}

              {/* Generated preview */}
              {generatedPost && !generating && (
                <div className="space-y-4 w-full max-w-sm">
                  {/* Channel switcher */}
                  <div className="flex justify-center">
                    <ChannelTabs active={channel} onChange={setChannel} />
                  </div>

                  {/* Phone preview using SocialPreview */}
                  <SocialPreview
                    content={editingGenerated ? editedGeneratedContent : (generatedPost.content_text || "")}
                    hashtags={generatedPost.hashtags}
                    channel={channel}
                    brandName={brandName}
                    brandInitials={brandInitials}
                    imageUrl={generatedImageUrl || undefined}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ━━━ Edit mode ━━━ */}
      {mode === "edit" && editPost && (
        <div className="surface p-0 overflow-hidden">
          <div className="flex items-center gap-3 border-b border-gray-100 px-5 py-3 bg-sky-50/50">
            <div className="rounded-lg bg-sky-500 p-1.5">
              <Pencil className="h-4 w-4 text-white" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-gray-900">Modifier le post</h2>
              <p className="text-xs text-gray-500">
                Cree le {new Date(editPost.created_at).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}
              </p>
            </div>
            <button
              onClick={() => { setMode("list"); setEditPost(null); }}
              className="ml-auto rounded-lg p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="p-5 space-y-4">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              rows={8}
              className="input-base resize-none"
            />
            <p className="text-[10px] text-gray-400 text-right">{editContent.length} caracteres</p>

            {/* Show current hashtags */}
            {editPost.hashtags && editPost.hashtags.length > 0 && (
              <div>
                <label className="section-label mb-1.5 block">Hashtags actuels</label>
                <HashtagPills hashtags={editPost.hashtags} max={20} />
              </div>
            )}

            <div className="flex gap-2 pt-2">
              <button onClick={handleEditSave} disabled={editSaving} className="btn-primary">
                {editSaving ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> Enregistrement...</>
                ) : (
                  <><Save className="h-4 w-4" /> Enregistrer</>
                )}
              </button>
              <button onClick={() => { setMode("list"); setEditPost(null); }} className="btn-ghost">
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ━━━ Status filter pills ━━━ */}
      {mode === "list" && (
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="h-4 w-4 text-gray-400 shrink-0" />
          {["all", "draft", "pending_review", "approved", "scheduled", "published", "rejected", "failed"].map((s) => {
            const conf = statusConfig[s];
            const count = statusCounts[s] || 0;
            const isActive = statusFilter === s;
            const label = s === "all" ? "Tous" : conf?.label || s;

            return (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-all border",
                  isActive
                    ? "bg-gray-900 text-white border-gray-900 shadow-sm"
                    : "bg-white text-gray-500 border-gray-200 hover:border-gray-300 hover:bg-gray-50",
                )}
              >
                {s !== "all" && conf && (
                  <conf.icon className={cn("h-3 w-3", isActive ? "text-white" : conf.color)} />
                )}
                {label}
                {count > 0 && (
                  <span className={cn(
                    "rounded-full px-1.5 py-0.5 text-[10px] font-bold leading-none",
                    isActive ? "bg-white/20 text-white" : "bg-gray-100 text-gray-500",
                  )}>
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* ━━━ Posts list ━━━ */}
      {mode === "list" && (
        <div>
          {/* Loading skeletons */}
          {loading && posts.length === 0 ? (
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <PostCardSkeleton key={i} />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            /* Empty state */
            <div className="surface flex flex-col items-center py-16 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gray-100 mb-4">
                <FileText className="h-8 w-8 text-gray-300" />
              </div>
              <p className="text-sm font-medium text-gray-500">
                {statusFilter === "all" ? "Aucun contenu" : "Aucun post avec ce statut"}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {statusFilter === "all"
                  ? "Creez votre premier post en cliquant sur \"Generer IA\" ou \"Manuel\""
                  : "Changez de filtre pour voir d'autres posts"}
              </p>
            </div>
          ) : (
            /* Post cards */
            <div className="space-y-3">
              {filtered.map((post) => {
                const st = statusConfig[post.status] || statusConfig.draft;
                const ch = post.target_channels?.[0]?.channel || "facebook";
                const ChIcon = channelIcons[ch] || Globe;
                const thumbnail = post.assets?.[0]?.thumbnail_url || post.assets?.[0]?.file_url;

                return (
                  <div key={post.id} className="surface-hover p-5 group">
                    <div className="flex items-start gap-4">
                      {/* Thumbnail / placeholder */}
                      <div className="relative h-16 w-16 rounded-xl overflow-hidden shrink-0 bg-gray-100">
                        {thumbnail ? (
                          <img src={thumbnail} alt="" className="h-full w-full object-cover" />
                        ) : (
                          <div className="h-full w-full flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100">
                            <FileText className="h-6 w-6 text-gray-300" />
                          </div>
                        )}
                        {/* Channel icon overlay */}
                        <div className={cn("absolute bottom-0.5 right-0.5 flex h-5 w-5 items-center justify-center rounded-md", channelColors[ch] || "bg-gray-100 text-gray-500")}>
                          <ChIcon className="h-3 w-3" />
                        </div>
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        {/* Status badges row */}
                        <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                          <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold", st.bgColor, st.color)}>
                            <st.icon className="h-3 w-3" />
                            {st.label}
                          </span>

                          {post.ai_generated && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-violet-50 text-violet-600 px-2 py-0.5 text-[10px] font-semibold">
                              <Zap className="h-3 w-3" />
                              IA
                            </span>
                          )}

                          {post.scheduled_at && (
                            <span className="inline-flex items-center gap-1 text-[10px] text-violet-500">
                              <Clock className="h-3 w-3" />
                              {new Date(post.scheduled_at).toLocaleDateString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
                            </span>
                          )}
                        </div>

                        {/* Content preview */}
                        <p className="text-sm text-gray-700 line-clamp-2 leading-relaxed">
                          {post.content_text || "\u2014"}
                        </p>

                        {/* Hashtags */}
                        {post.hashtags && post.hashtags.length > 0 && (
                          <div className="mt-1.5">
                            <HashtagPills hashtags={post.hashtags} max={4} />
                          </div>
                        )}

                        {/* Confidence bar for AI posts */}
                        {post.ai_generated && post.ai_confidence_score != null && (
                          <div className="mt-2 max-w-[160px]">
                            <div className="flex items-center gap-1.5">
                              <Bot className="h-3 w-3 text-gray-400" />
                              <ConfidenceBar score={post.ai_confidence_score} className="flex-1" />
                            </div>
                          </div>
                        )}

                        {/* Date */}
                        <p className="mt-2 text-[11px] text-gray-400">
                          {new Date(post.created_at).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}
                        </p>
                      </div>

                      {/* Actions — always visible */}
                      <div className="flex flex-wrap items-center gap-2 shrink-0 mt-3 pt-3 border-t border-gray-100 lg:mt-0 lg:pt-0 lg:border-0">
                        {/* Preview */}
                        <button
                          onClick={() => { setPreviewPost(post); setPreviewChannel(ch); }}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:text-brand-600 hover:border-brand-200 hover:bg-brand-50 transition-colors"
                        >
                          <Eye className="h-3.5 w-3.5" /> Voir
                        </button>

                        {/* Draft-specific actions */}
                        {post.status === "draft" && (
                          <>
                            <button
                              onClick={() => {
                                setEditPost(post);
                                setEditContent(post.content_text || "");
                                setMode("edit");
                              }}
                              className="inline-flex items-center gap-1.5 rounded-lg border border-sky-200 bg-sky-50 px-3 py-1.5 text-xs font-medium text-sky-700 hover:bg-sky-100 transition-colors"
                            >
                              <Pencil className="h-3.5 w-3.5" /> Modifier
                            </button>
                            <button
                              onClick={() => handleAction(post.id, "submit")}
                              disabled={actionId === post.id}
                              className="inline-flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-100 transition-colors disabled:opacity-50"
                            >
                              {actionId === post.id ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <ArrowUpRight className="h-3.5 w-3.5" />
                              )}
                              Valider
                            </button>
                          </>
                        )}

                        {/* Publish action */}
                        {(post.status === "approved" || post.status === "scheduled") && (
                          <button
                            onClick={() => handleAction(post.id, "publish")}
                            disabled={actionId === post.id}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-emerald-600 transition-colors disabled:opacity-50"
                          >
                            {actionId === post.id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Send className="h-3.5 w-3.5" />
                            )}
                            Publier
                          </button>
                        )}

                        {/* Secondary actions */}
                        <div className="flex items-center gap-1 ml-auto">
                          <button
                            onClick={() => handleDuplicate(post)}
                            className="rounded-lg p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
                            title="Dupliquer"
                          >
                            <Copy className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => setDeleteTarget(post.id)}
                            disabled={actionId === post.id}
                            className="rounded-lg p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                            title="Supprimer"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ━━━ Preview modal ━━━ */}
      {previewPost && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={() => setPreviewPost(null)}
        >
          <div className="relative" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setPreviewPost(null)}
              className="absolute -top-3 -right-3 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-white shadow-lg text-gray-500 hover:text-gray-800 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
            <div className="space-y-4">
              <div className="flex justify-center">
                <ChannelTabs active={previewChannel} onChange={setPreviewChannel} />
              </div>
              <SocialPreview
                content={previewPost.content_text || ""}
                hashtags={previewPost.hashtags}
                channel={previewChannel}
                brandName={brandName}
                brandInitials={brandInitials}
                imageUrl={previewPost.assets?.[0]?.file_url}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

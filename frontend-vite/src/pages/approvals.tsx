
import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import {
  CheckCircle,
  XCircle,
  Zap,
  Clock,
  Loader2,
  Eye,
  X,
  Bot,
  CheckSquare,
  Square,
  Filter,
  ChevronDown,
  MessageSquare,
  Sparkles,
  AlertTriangle,
  TrendingUp,
  Hash,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useApi } from "@/hooks/use-api";
import {
  approvals as approvalsApi,
  posts as postsApi,
  brands as brandsApi,
  Approval,
  Post,
} from "@/lib/api";
import { SocialPreview, ChannelTabs } from "@/components/preview/social-preview";
import { Skeleton, ListItemSkeleton } from "@/components/ui/skeleton";

// ─── Types ───────────────────────────────────────────────

type ConfidenceLevel = "all" | "high" | "medium" | "low";

interface EnrichedApproval extends Approval {
  post?: Post;
}

// ─── Confidence helpers ──────────────────────────────────

function getConfidenceLevel(score?: number): ConfidenceLevel {
  if (score == null) return "medium";
  if (score >= 0.8) return "high";
  if (score >= 0.5) return "medium";
  return "low";
}

function getConfidenceColor(level: ConfidenceLevel) {
  switch (level) {
    case "high":
      return { bg: "bg-emerald-500", text: "text-emerald-700", light: "bg-emerald-50", border: "border-emerald-200" };
    case "medium":
      return { bg: "bg-amber-500", text: "text-amber-700", light: "bg-amber-50", border: "border-amber-200" };
    case "low":
      return { bg: "bg-red-500", text: "text-red-700", light: "bg-red-50", border: "border-red-200" };
    default:
      return { bg: "bg-gray-400", text: "text-gray-600", light: "bg-gray-50", border: "border-gray-200" };
  }
}

function getConfidenceLabel(level: ConfidenceLevel) {
  switch (level) {
    case "high": return "Haute";
    case "medium": return "Moyenne";
    case "low": return "Faible";
    default: return "Toutes";
  }
}

// ─── Confidence gauge component ──────────────────────────

function ConfidenceGauge({ score }: { score?: number }) {
  if (score == null) return null;
  const pct = Math.round(score * 100);
  const level = getConfidenceLevel(score);
  const colors = getConfidenceColor(level);

  return (
    <div className="flex items-center gap-2.5">
      <div className="flex items-center gap-1.5">
        <Zap className={cn("h-3.5 w-3.5", colors.text)} />
        <span className={cn("text-xs font-semibold", colors.text)}>{pct}%</span>
      </div>
      <div className="relative h-2 w-24 overflow-hidden rounded-full bg-gray-100">
        <div
          className={cn("absolute inset-y-0 left-0 rounded-full transition-all duration-700 ease-out", colors.bg)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={cn(
        "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
        colors.light, colors.text,
      )}>
        {getConfidenceLabel(level)}
      </span>
    </div>
  );
}

// ─── Inline social preview (mini card) ───────────────────

function InlinePostPreview({
  content,
  hashtags,
  channel,
  brandName,
  brandInitials,
  aiGenerated,
}: {
  content: string;
  hashtags: string[];
  channel: string;
  brandName: string;
  brandInitials: string;
  aiGenerated?: boolean;
}) {
  const channelColors: Record<string, string> = {
    facebook: "border-l-blue-500",
    instagram: "border-l-pink-500",
    whatsapp: "border-l-emerald-500",
  };

  const channelLabels: Record<string, string> = {
    facebook: "Facebook",
    instagram: "Instagram",
    whatsapp: "WhatsApp",
  };

  return (
    <div className={cn(
      "rounded-xl border border-gray-100 bg-white shadow-sm overflow-hidden border-l-4",
      channelColors[channel] || "border-l-gray-400",
    )}>
      {/* Mini header bar */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-gray-50/80 border-b border-gray-100">
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-500 text-white text-[9px] font-bold shrink-0">
          {brandInitials}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-gray-900 truncate">{brandName}</p>
          <p className="text-[10px] text-gray-400">{channelLabels[channel] || channel} &middot; Brouillon</p>
        </div>
        {aiGenerated && (
          <span className="flex items-center gap-1 rounded-full bg-violet-50 px-2 py-0.5 text-[10px] font-medium text-violet-600 shrink-0">
            <Sparkles className="h-3 w-3" />
            IA
          </span>
        )}
      </div>

      {/* Content body */}
      <div className="px-4 py-3">
        {content ? (
          <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap line-clamp-6">
            {content}
          </p>
        ) : (
          <p className="text-sm italic text-gray-400">Contenu vide</p>
        )}

        {/* Hashtags as pills */}
        {hashtags.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {hashtags.map((h) => (
              <span
                key={h}
                className="inline-flex items-center gap-0.5 rounded-full bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-700 border border-brand-100"
              >
                <Hash className="h-3 w-3 text-brand-400" />
                {h}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Filter dropdown ─────────────────────────────────────

function ConfidenceFilter({
  value,
  onChange,
  counts,
}: {
  value: ConfidenceLevel;
  onChange: (v: ConfidenceLevel) => void;
  counts: Record<ConfidenceLevel, number>;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const options: ConfidenceLevel[] = ["all", "high", "medium", "low"];
  const icons: Record<ConfidenceLevel, React.ReactNode> = {
    all: <Filter className="h-3.5 w-3.5" />,
    high: <TrendingUp className="h-3.5 w-3.5 text-emerald-600" />,
    medium: <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />,
    low: <XCircle className="h-3.5 w-3.5 text-red-500" />,
  };
  const labels: Record<ConfidenceLevel, string> = {
    all: "Toutes",
    high: "Haute confiance",
    medium: "Confiance moyenne",
    low: "Faible confiance",
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-all",
          value !== "all"
            ? "border-brand-200 bg-brand-50 text-brand-700"
            : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50",
        )}
      >
        {icons[value]}
        <span>{labels[value]}</span>
        <ChevronDown className={cn("h-4 w-4 text-gray-400 transition-transform", open && "rotate-180")} />
      </button>

      {open && (
        <div className="absolute right-0 z-20 mt-1.5 w-56 rounded-xl border border-gray-100 bg-white p-1.5 shadow-xl animate-in fade-in slide-in-from-top-1 duration-150">
          {options.map((opt) => (
            <button
              key={opt}
              onClick={() => { onChange(opt); setOpen(false); }}
              className={cn(
                "flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm transition-colors",
                value === opt ? "bg-gray-100 font-medium text-gray-900" : "text-gray-600 hover:bg-gray-50",
              )}
            >
              {icons[opt]}
              <span className="flex-1 text-left">{labels[opt]}</span>
              <span className={cn(
                "rounded-full px-2 py-0.5 text-xs font-medium",
                opt === "all" ? "bg-gray-100 text-gray-500" :
                opt === "high" ? "bg-emerald-50 text-emerald-600" :
                opt === "medium" ? "bg-amber-50 text-amber-600" :
                "bg-red-50 text-red-600",
              )}>
                {counts[opt]}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Single approval card ────────────────────────────────

function ApprovalCard({
  item,
  post,
  brandName,
  brandInitials,
  selected,
  onToggleSelect,
  onApprove,
  onReject,
  onPreview,
  acting,
  removing,
}: {
  item: Approval;
  post?: Post;
  brandName: string;
  brandInitials: string;
  selected: boolean;
  onToggleSelect: () => void;
  onApprove: (id: string, note?: string) => void;
  onReject: (id: string, note: string) => void;
  onPreview: (post: Post, channel: string) => void;
  acting: boolean;
  removing: boolean;
}) {
  const [noteOpen, setNoteOpen] = useState(false);
  const [note, setNote] = useState("");

  const postContent = post?.content_text || "";
  const postHashtags = post?.hashtags || [];
  const postChannel = post?.target_channels?.[0]?.channel || "facebook";
  const confidence = post?.ai_confidence_score;
  const confidenceLevel = getConfidenceLevel(confidence);

  return (
    <div
      className={cn(
        "group relative rounded-2xl border bg-white shadow-sm transition-all duration-500 ease-out overflow-hidden",
        selected ? "border-brand-300 ring-2 ring-brand-100" : "border-gray-100 hover:border-gray-200 hover:shadow-md",
        removing && "opacity-0 scale-95 -translate-x-4 pointer-events-none",
      )}
    >
      {/* Top bar */}
      <div className="flex items-center gap-3 px-5 py-3.5 border-b border-gray-50">
        {/* Checkbox */}
        <button
          onClick={onToggleSelect}
          className="shrink-0 text-gray-300 hover:text-brand-500 transition-colors"
        >
          {selected ? (
            <CheckSquare className="h-5 w-5 text-brand-500" />
          ) : (
            <Square className="h-5 w-5" />
          )}
        </button>

        {/* Status + channel */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700 border border-amber-100">
            <Clock className="h-3 w-3" />
            En attente
          </span>
          <span className="rounded-full bg-gray-100 px-2.5 py-1 text-[11px] font-medium text-gray-500 capitalize">
            {postChannel}
          </span>
        </div>

        {/* Date */}
        <span className="text-xs text-gray-400 shrink-0">
          {new Date(item.created_at).toLocaleDateString("fr-FR", {
            day: "numeric",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>

      {/* Body */}
      <div className="px-5 py-4 space-y-4">
        {/* Confidence gauge */}
        {confidence != null && <ConfidenceGauge score={confidence} />}

        {/* Inline post preview */}
        {post ? (
          <div className="flex gap-4">
            <div className="flex-1 min-w-0">
              <InlinePostPreview
                content={postContent}
                hashtags={postHashtags}
                channel={postChannel}
                brandName={brandName}
                brandInitials={brandInitials}
                aiGenerated={post.ai_generated}
              />
            </div>

            {/* Preview button */}
            <button
              onClick={() => onPreview(post, postChannel)}
              className="shrink-0 self-start flex flex-col items-center gap-1.5 rounded-xl border border-gray-200 px-4 py-3.5 text-gray-400 hover:text-brand-600 hover:border-brand-200 hover:bg-brand-50/50 transition-all group/preview"
            >
              <Eye className="h-5 w-5 group-hover/preview:scale-110 transition-transform" />
              <span className="text-[10px] font-semibold tracking-wide uppercase">Preview</span>
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-3 w-1/3" />
          </div>
        )}
      </div>

      {/* Actions bar / History info */}
      <div className="border-t border-gray-50 px-5 py-3.5 bg-gray-50/30">
        {/* History info for reviewed items */}
        {item.status !== "pending" && (
          <div className="flex items-center gap-3">
            <div className={cn(
              "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold",
              item.status === "approved" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
            )}>
              {item.status === "approved" ? <CheckCircle className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
              {item.status === "approved" ? "Approuvé" : "Rejeté"}
            </div>
            {(item as any).review_note && (
              <span className="text-xs text-gray-500 italic">"{(item as any).review_note}"</span>
            )}
            {(item as any).reviewed_at && (
              <span className="text-xs text-gray-400 ml-auto">
                {new Date((item as any).reviewed_at).toLocaleDateString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
              </span>
            )}
          </div>
        )}

        {/* Action buttons for pending items */}
        {item.status === "pending" && (<>
          <div className="flex items-center gap-3">
            {/* Approve button */}
            <button
              onClick={() => onApprove(item.id, note || undefined)}
              disabled={acting}
              className={cn(
                "inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-all",
                "bg-emerald-600 text-white shadow-sm",
                "hover:bg-emerald-700 hover:shadow-md active:scale-[0.98]",
                "disabled:opacity-50 disabled:cursor-not-allowed",
              )}
            >
              {acting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle className="h-4 w-4" />
              )}
              Approuver
            </button>

            {/* Reject button */}
            <button
              onClick={() => {
                if (!note || note.length < 5) {
                  toast.error("Note requise", {
                    description: "La note de rejet doit faire au moins 5 caracteres.",
                  });
                  setNoteOpen(true);
                  return;
                }
                onReject(item.id, note);
              }}
              disabled={acting}
              className={cn(
                "inline-flex items-center gap-2 rounded-xl border-2 border-red-200 px-5 py-2.5 text-sm font-semibold transition-all",
                "text-red-600 bg-white",
                "hover:bg-red-50 hover:border-red-300 active:scale-[0.98]",
                "disabled:opacity-50 disabled:cursor-not-allowed",
              )}
            >
              <XCircle className="h-4 w-4" />
              Rejeter
            </button>

            {/* Note toggle */}
            <button
              onClick={() => setNoteOpen(!noteOpen)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-xl px-3 py-2.5 text-sm font-medium transition-all",
                noteOpen || note
                  ? "bg-gray-200 text-gray-800"
                  : "text-gray-400 hover:text-gray-600 hover:bg-gray-100",
              )}
            >
              <MessageSquare className="h-4 w-4" />
              {note ? "Note ajoutee" : "Ajouter une note"}
            </button>
          </div>

          {/* Expandable note input */}
          <div
            className={cn(
              "overflow-hidden transition-all duration-300 ease-out",
              noteOpen ? "max-h-32 opacity-100 mt-3" : "max-h-0 opacity-0",
            )}
          >
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Note de revue (obligatoire pour le rejet, min. 5 caracteres)..."
              rows={2}
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-800 placeholder:text-gray-400 focus:border-brand-300 focus:ring-2 focus:ring-brand-100 focus:outline-none resize-none transition-all"
            />
          </div>
        </>)}
      </div>
    </div>
  );
}

// ─── Loading skeleton ────────────────────────────────────

function ApprovalSkeleton() {
  return (
    <div className="rounded-2xl border border-gray-100 bg-white p-5 space-y-4">
      <div className="flex items-center gap-3">
        <Skeleton className="h-5 w-5 rounded" />
        <Skeleton className="h-6 w-20 rounded-full" />
        <Skeleton className="h-6 w-16 rounded-full" />
        <div className="flex-1" />
        <Skeleton className="h-4 w-24" />
      </div>
      <Skeleton className="h-2 w-24 rounded-full" />
      <div className="rounded-xl border border-gray-100 p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Skeleton className="h-7 w-7 rounded-full" />
          <div className="space-y-1">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-2 w-16" />
          </div>
        </div>
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <div className="flex gap-1.5 mt-2">
          <Skeleton className="h-6 w-16 rounded-full" />
          <Skeleton className="h-6 w-20 rounded-full" />
          <Skeleton className="h-6 w-14 rounded-full" />
        </div>
      </div>
      <div className="flex gap-3 pt-2">
        <Skeleton className="h-10 w-32 rounded-xl" />
        <Skeleton className="h-10 w-28 rounded-xl" />
        <Skeleton className="h-10 w-36 rounded-xl" />
      </div>
    </div>
  );
}

// ─── Main page component ─────────────────────────────────

type TabKey = "pending" | "approved" | "rejected" | "all";

const STATUS_TABS: { key: TabKey; label: string; icon: typeof Clock }[] = [
  { key: "pending", label: "En attente", icon: Clock },
  { key: "approved", label: "Approuvés", icon: CheckCircle },
  { key: "rejected", label: "Rejetés", icon: XCircle },
  { key: "all", label: "Tout", icon: Filter },
];

export default function ApprovalsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("pending");
  const { data: approvalList, loading, refetch } = useApi(
    () => approvalsApi.list(activeTab === "pending" ? undefined : activeTab),
    [activeTab],
  );
  const { data: brandList } = useApi(() => brandsApi.list(), []);

  const [postCache, setPostCache] = useState<Record<string, Post>>({});
  const [acting, setActing] = useState<Set<string>>(new Set());
  const [removing, setRemoving] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confidenceFilter, setConfidenceFilter] = useState<ConfidenceLevel>("all");

  // Preview modal state
  const [previewPost, setPreviewPost] = useState<Post | null>(null);
  const [previewChannel, setPreviewChannel] = useState("facebook");

  const brandName = brandList?.[0]?.name || "Ma marque";
  const brandInitials = brandName
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  // ─── Fetch posts for approvals ───────────────────────

  useEffect(() => {
    if (!approvalList) return;
    approvalList.forEach((a) => {
      if (!postCache[a.post_id]) {
        postsApi
          .get(a.post_id)
          .then((p) => setPostCache((prev) => ({ ...prev, [a.post_id]: p })))
          .catch(() => {});
      }
    });
  }, [approvalList]);

  // ─── Filtering ───────────────────────────────────────

  const items = approvalList ?? [];

  const confidenceCounts = useMemo(() => {
    const counts: Record<ConfidenceLevel, number> = { all: items.length, high: 0, medium: 0, low: 0 };
    items.forEach((item) => {
      const post = postCache[item.post_id];
      const level = getConfidenceLevel(post?.ai_confidence_score);
      counts[level]++;
    });
    return counts;
  }, [items, postCache]);

  const filteredItems = useMemo(() => {
    if (confidenceFilter === "all") return items;
    return items.filter((item) => {
      const post = postCache[item.post_id];
      return getConfidenceLevel(post?.ai_confidence_score) === confidenceFilter;
    });
  }, [items, postCache, confidenceFilter]);

  // ─── Selection ───────────────────────────────────────

  const toggleSelect = useCallback((id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    if (selected.size === filteredItems.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(filteredItems.map((i) => i.id)));
    }
  }, [filteredItems, selected.size]);

  // ─── Animated removal helper ─────────────────────────

  const animateRemoval = useCallback((id: string) => {
    setRemoving((prev) => new Set(prev).add(id));
    setTimeout(() => {
      setRemoving((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      refetch();
    }, 500);
  }, [refetch]);

  // ─── Approve / Reject handlers ───────────────────────

  const handleApprove = useCallback(async (id: string, note?: string) => {
    setActing((prev) => new Set(prev).add(id));
    try {
      await approvalsApi.approve(id, note);
      toast.success("Contenu approuve", {
        description: "Le contenu a ete valide et sera publie selon le calendrier.",
      });
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      animateRemoval(id);
    } catch (err: any) {
      toast.error("Erreur lors de l'approbation", {
        description: err.message || "Une erreur inattendue est survenue.",
      });
    } finally {
      setActing((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }, [animateRemoval]);

  const handleReject = useCallback(async (id: string, note: string) => {
    setActing((prev) => new Set(prev).add(id));
    try {
      await approvalsApi.reject(id, note);
      toast.success("Contenu rejete", {
        description: "Le contenu a ete renvoye pour revision.",
      });
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      animateRemoval(id);
    } catch (err: any) {
      toast.error("Erreur lors du rejet", {
        description: err.message || "Une erreur inattendue est survenue.",
      });
    } finally {
      setActing((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }, [animateRemoval]);

  // ─── Bulk approve ────────────────────────────────────

  const [bulkActing, setBulkActing] = useState(false);

  const handleBulkApprove = useCallback(async () => {
    if (selected.size === 0) {
      toast.warning("Aucune selection", {
        description: "Selectionnez au moins un contenu a approuver.",
      });
      return;
    }

    setBulkActing(true);
    const ids = Array.from(selected);
    let successCount = 0;
    let errorCount = 0;

    for (const id of ids) {
      try {
        await approvalsApi.approve(id);
        successCount++;
        setRemoving((prev) => new Set(prev).add(id));
      } catch {
        errorCount++;
      }
    }

    setSelected(new Set());
    setBulkActing(false);

    if (successCount > 0) {
      toast.success(`${successCount} contenu${successCount > 1 ? "s" : ""} approuve${successCount > 1 ? "s" : ""}`, {
        description: errorCount > 0
          ? `${errorCount} erreur${errorCount > 1 ? "s" : ""} rencontree${errorCount > 1 ? "s" : ""}.`
          : "Tous les contenus selectionnes ont ete valides.",
      });
    } else if (errorCount > 0) {
      toast.error("Echec de l'approbation en masse", {
        description: "Aucun contenu n'a pu etre approuve.",
      });
    }

    setTimeout(() => {
      setRemoving(new Set());
      refetch();
    }, 500);
  }, [selected, refetch]);

  // ─── Preview handler ─────────────────────────────────

  const openPreview = useCallback((post: Post, channel: string) => {
    setPreviewPost(post);
    setPreviewChannel(channel);
  }, []);

  // ─── Loading state ───────────────────────────────────

  if (loading) {
    return (
      <div className="space-y-6 max-w-5xl">
        <div>
          <Skeleton className="h-8 w-40" />
          <Skeleton className="h-4 w-64 mt-2" />
        </div>
        <div className="space-y-4">
          <ApprovalSkeleton />
          <ApprovalSkeleton />
          <ApprovalSkeleton />
        </div>
      </div>
    );
  }

  // ─── Render ──────────────────────────────────────────

  const allSelected = filteredItems.length > 0 && selected.size === filteredItems.length;
  const someSelected = selected.size > 0 && selected.size < filteredItems.length;

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Validations</h1>
          <p className="mt-1 text-sm text-gray-500">
            {activeTab === "pending" && items.length > 0
              ? `${items.length} contenu${items.length > 1 ? "s" : ""} en attente de votre approbation`
              : activeTab === "approved"
              ? `${items.length} contenu${items.length > 1 ? "s" : ""} approuve${items.length > 1 ? "s" : ""}`
              : activeTab === "rejected"
              ? `${items.length} contenu${items.length > 1 ? "s" : ""} rejete${items.length > 1 ? "s" : ""}`
              : `${items.length} validation${items.length > 1 ? "s" : ""} au total`}
          </p>
        </div>
        {activeTab === "pending" && items.length > 0 && (
          <ConfidenceFilter
            value={confidenceFilter}
            onChange={setConfidenceFilter}
            counts={confidenceCounts}
          />
        )}
      </div>

      {/* Status tabs */}
      <div className="flex gap-1 rounded-xl bg-gray-100/80 p-1">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => { setActiveTab(tab.key); setSelected(new Set()); }}
            className={cn(
              "flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-all",
              activeTab === tab.key
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            )}
          >
            <tab.icon className="h-3.5 w-3.5" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Bulk actions bar */}
      {filteredItems.length > 0 && (
        <div className={cn(
          "flex items-center gap-4 rounded-xl border px-4 py-3 transition-all",
          selected.size > 0
            ? "border-brand-200 bg-brand-50/50"
            : "border-gray-100 bg-gray-50/50",
        )}>
          {/* Select all checkbox */}
          <button onClick={toggleSelectAll} className="flex items-center gap-2.5 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors">
            {allSelected ? (
              <CheckSquare className="h-5 w-5 text-brand-500" />
            ) : someSelected ? (
              <div className="relative">
                <Square className="h-5 w-5 text-brand-400" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="h-2 w-2 rounded-sm bg-brand-500" />
                </div>
              </div>
            ) : (
              <Square className="h-5 w-5 text-gray-300" />
            )}
            {selected.size > 0
              ? `${selected.size} selectionne${selected.size > 1 ? "s" : ""}`
              : "Tout selectionner"
            }
          </button>

          <div className="flex-1" />

          {/* Bulk approve */}
          <button
            onClick={handleBulkApprove}
            disabled={selected.size === 0 || bulkActing}
            className={cn(
              "inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-all",
              selected.size > 0
                ? "bg-emerald-600 text-white shadow-sm hover:bg-emerald-700 hover:shadow-md active:scale-[0.98]"
                : "bg-gray-100 text-gray-400 cursor-not-allowed",
            )}
          >
            {bulkActing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <CheckCircle className="h-4 w-4" />
            )}
            Approuver{selected.size > 1 ? " tout" : ""}
            {selected.size > 0 && (
              <span className="rounded-full bg-white/20 px-2 py-0.5 text-xs">
                {selected.size}
              </span>
            )}
          </button>
        </div>
      )}

      {/* Empty state */}
      {filteredItems.length === 0 && items.length === 0 && (
        <div className="surface flex flex-col items-center py-20 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50">
            <CheckCircle className="h-8 w-8 text-emerald-400" />
          </div>
          <p className="mt-5 text-lg font-semibold text-gray-900">Tout est valide !</p>
          <p className="mt-1 text-sm text-gray-500 max-w-sm">
            Aucun contenu en attente d&apos;approbation. Revenez plus tard ou creez de nouveaux posts.
          </p>
        </div>
      )}

      {/* Filtered empty state */}
      {filteredItems.length === 0 && items.length > 0 && (
        <div className="surface flex flex-col items-center py-16 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gray-100">
            <Filter className="h-6 w-6 text-gray-400" />
          </div>
          <p className="mt-4 text-base font-semibold text-gray-900">Aucun resultat pour ce filtre</p>
          <p className="mt-1 text-sm text-gray-500">
            {confidenceCounts.all} contenu{confidenceCounts.all > 1 ? "s" : ""} au total.{" "}
            <button
              onClick={() => setConfidenceFilter("all")}
              className="text-brand-600 hover:text-brand-700 font-medium"
            >
              Voir tout
            </button>
          </p>
        </div>
      )}

      {/* Approval cards */}
      {filteredItems.length > 0 && (
        <div className="space-y-4">
          {filteredItems.map((item) => (
            <ApprovalCard
              key={item.id}
              item={item}
              post={postCache[item.post_id]}
              brandName={brandName}
              brandInitials={brandInitials}
              selected={selected.has(item.id)}
              onToggleSelect={() => toggleSelect(item.id)}
              onApprove={handleApprove}
              onReject={handleReject}
              onPreview={openPreview}
              acting={acting.has(item.id)}
              removing={removing.has(item.id)}
            />
          ))}
        </div>
      )}

      {/* iPhone Preview Modal */}
      {previewPost && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setPreviewPost(null)}
        >
          <div
            className="relative animate-in zoom-in-95 fade-in duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setPreviewPost(null)}
              className="absolute -top-3 -right-3 z-10 flex h-9 w-9 items-center justify-center rounded-full bg-white shadow-xl text-gray-500 hover:text-gray-800 hover:scale-110 transition-all"
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
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

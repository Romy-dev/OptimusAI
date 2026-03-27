import { useState, useEffect, useRef, useCallback } from "react";
import { getPersistedValue, setPersistedValue } from "@/hooks/use-persisted-state";
import { toast } from "sonner";
import {
  Film, Play, Pause, Download, ChevronLeft, ChevronRight, Sparkles,
  Image, Clock, Zap, Target, MousePointerClick, Music, Loader2,
  RefreshCw, Type, AlignLeft, Timer, Wand2, CheckCircle, Brain,
  Trash2, Video, Layout, Calendar,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi } from "@/hooks/use-api";
import { brands as brandsApi, stories as storiesApi } from "@/lib/api";

// ─── Types ───────────────────────────────────────────────────

interface StorySlide {
  index: number;
  role: "hook" | "detail" | "urgency" | "cta";
  headline: string;
  subtext: string;
  duration: number;
  animation: string;
  image_url?: string;
  rendered?: boolean;
}

interface StoryPlan {
  slides: StorySlide[];
  platform: string;
  brand_id: string;
  theme?: string;
}

type PageState = "initial" | "planning" | "planned" | "rendering" | "rendered" | "video_ready";
type AnimationType = "fade_in" | "slide_up" | "zoom_in" | "bounce";
type StoryTab = "create" | "history";

const PLATFORMS = [
  { id: "instagram", label: "Instagram", icon: "📸" },
  { id: "facebook", label: "Facebook", icon: "📘" },
  { id: "whatsapp", label: "WhatsApp", icon: "💬" },
];

const PLATFORM_BADGES: Record<string, { label: string; color: string }> = {
  instagram: { label: "Instagram", color: "bg-pink-100 text-pink-700" },
  facebook: { label: "Facebook", color: "bg-blue-100 text-blue-700" },
  whatsapp: { label: "WhatsApp", color: "bg-emerald-100 text-emerald-700" },
};

const STATUS_BADGES: Record<string, { label: string; color: string }> = {
  draft: { label: "Brouillon", color: "bg-gray-100 text-gray-600" },
  planned: { label: "Planifie", color: "bg-sky-100 text-sky-700" },
  rendered: { label: "Rendu", color: "bg-purple-100 text-purple-700" },
  video_ready: { label: "Video prete", color: "bg-emerald-100 text-emerald-700" },
};

const ROLE_CONFIG: Record<string, { label: string; color: string; bgColor: string; icon: React.ElementType }> = {
  hook:    { label: "HOOK",    color: "text-amber-700",   bgColor: "bg-amber-100",   icon: Zap },
  detail:  { label: "DETAIL",  color: "text-sky-700",     bgColor: "bg-sky-100",     icon: AlignLeft },
  urgency: { label: "URGENCE", color: "text-rose-700",    bgColor: "bg-rose-100",    icon: Target },
  cta:     { label: "CTA",     color: "text-emerald-700", bgColor: "bg-emerald-100", icon: MousePointerClick },
};

const ANIMATIONS: { id: AnimationType; label: string; icon: React.ElementType }[] = [
  { id: "fade_in",  label: "Fondu",    icon: Sparkles },
  { id: "slide_up", label: "Glisser",  icon: ChevronLeft },
  { id: "zoom_in",  label: "Zoom",     icon: Target },
  { id: "bounce",   label: "Rebond",   icon: Zap },
];

const MUSIC_MOODS = [
  { id: "upbeat",     label: "Upbeat",     emoji: "🎵" },
  { id: "chill",      label: "Chill",      emoji: "🎶" },
  { id: "african",    label: "Africain",   emoji: "🥁" },
  { id: "dramatic",   label: "Dramatique", emoji: "🎸" },
  { id: "inspiring",  label: "Inspirant",  emoji: "✨" },
  { id: "festive",    label: "Festif",     emoji: "🎉" },
];

const GRADIENT_PRESETS = [
  "from-brand-500 via-brand-600 to-sky-600",
  "from-purple-600 via-pink-500 to-rose-500",
  "from-amber-500 via-orange-500 to-red-500",
  "from-emerald-500 via-teal-500 to-cyan-500",
  "from-indigo-600 via-violet-500 to-purple-500",
  "from-rose-500 via-pink-500 to-fuchsia-500",
];

// ─── Story Progress Steps ────────────────────────────────────

const PLANNING_STEPS = [
  { label: "Analyse du brief", icon: Brain, duration: 3 },
  { label: "Structure narrative", icon: Type, duration: 4 },
  { label: "Composition des slides", icon: Film, duration: 8 },
  { label: "Finalisation", icon: CheckCircle, duration: 3 },
];

// Quick Action templates — one-click story briefs
const QUICK_ACTIONS = [
  { label: "Promo Flash", emoji: "🔥", brief: "Promo flash -30% pendant 24h seulement, ne ratez pas cette offre exceptionnelle", mood: "urgent" },
  { label: "Nouveau Produit", emoji: "✨", brief: "Lancement de notre nouveau produit phare, découvrez ses caractéristiques uniques", mood: "inspiring" },
  { label: "Événement", emoji: "🎉", brief: "Grand événement ce weekend, venez nombreux, ambiance garantie et surprises", mood: "festive" },
  { label: "Témoignage", emoji: "💬", brief: "Nos clients témoignent de leur satisfaction, découvrez leurs avis authentiques", mood: "warm" },
  { label: "Behind the Scenes", emoji: "🎬", brief: "Découvrez les coulisses de notre entreprise, notre équipe et notre savoir-faire", mood: "chill" },
  { label: "Astuce du Jour", emoji: "💡", brief: "Astuce du jour pour bien utiliser nos produits et en tirer le meilleur parti", mood: "upbeat" },
  { label: "Jeu Concours", emoji: "🎁", brief: "Grand jeu concours, participez pour gagner des lots exceptionnels, règles simples", mood: "festive" },
  { label: "Fête / Célébration", emoji: "🌙", brief: "Bonne fête à tous, que cette journée soit remplie de joie et de bonheur", mood: "inspiring" },
];

// ─── Main Page ───────────────────────────────────────────────

export default function StoriesPage() {
  const { data: brandList } = useApi(() => brandsApi.list(), []);

  // Tab state
  const [activeTab, setActiveTab] = useState<StoryTab>("create");

  // Story history
  const [storyHistory, setStoryHistory] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [storyId, setStoryId] = useState<string | null>(null);

  // State
  const [brief, setBrief] = useState("");
  const [platform, setPlatform] = useState("instagram");
  const [brandId, setBrandId] = useState("");
  const [pageState, setPageState] = useState<PageState>("initial");
  const [storyPlan, setStoryPlan] = useState<StoryPlan | null>(null);
  const [activeSlide, setActiveSlide] = useState(0);
  const [musicMood, setMusicMood] = useState("upbeat");
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [renderProgress, setRenderProgress] = useState<Record<number, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [isAutoPlaying, setIsAutoPlaying] = useState(false);
  const autoPlayRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch story history
  const fetchHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const list = await storiesApi.list();
      setStoryHistory(list || []);
    } catch {
      // Silently fail - history is optional
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  // Load history when switching to history tab
  useEffect(() => {
    if (activeTab === "history") {
      fetchHistory();
    }
  }, [activeTab, fetchHistory]);

  // Restore state from localStorage on mount
  useEffect(() => {
    try {
      const s = getPersistedValue<any>("story-state", null);
      if (s) {
        if (s.storyPlan?.slides?.length) {
          setStoryPlan(s.storyPlan);
          setBrief(s.brief || "");
          setPlatform(s.platform || "instagram");
          setBrandId(s.brandId || "");
          setMusicMood(s.musicMood || "upbeat");
          setVideoUrl(s.videoUrl || null);
          setStoryId(s.storyId || null);
          setActiveSlide(0);
          // Determine state from data
          const hasRendered = s.storyPlan.slides.some((sl: any) => sl.image_url);
          setPageState(s.videoUrl ? "video_ready" : hasRendered ? "rendered" : "planned");
        }
      }
    } catch {}
  }, []);

  // Persist state to localStorage on changes
  useEffect(() => {
    if (storyPlan && pageState !== "initial" && pageState !== "planning") {
      try {
        setPersistedValue("story-state", {
          storyPlan, brief, platform, brandId, musicMood, videoUrl, storyId,
        });
      } catch {}
    }
  }, [storyPlan, brief, platform, brandId, musicMood, videoUrl, pageState, storyId]);

  // Auto-select first brand
  useEffect(() => {
    if (brandList?.length && !brandId) {
      setBrandId(brandList[0].id);
    }
  }, [brandList, brandId]);

  // Auto-play logic
  useEffect(() => {
    if (!isAutoPlaying || !storyPlan) return;
    const slide = storyPlan.slides[activeSlide];
    autoPlayRef.current = setTimeout(() => {
      setActiveSlide((prev) => (prev + 1) % storyPlan.slides.length);
    }, (slide?.duration || 3) * 1000);
    return () => { if (autoPlayRef.current) clearTimeout(autoPlayRef.current); };
  }, [isAutoPlaying, activeSlide, storyPlan]);

  // ─── Handlers ────────────────────────────────────────────────

  const handleGenerate = async () => {
    if (!brief.trim() || !brandId) return;
    setPageState("planning");
    setError(null);
    setStoryPlan(null);
    setActiveSlide(0);
    setRenderProgress({});
    setVideoUrl(null);
    setStoryId(null);

    try {
      const result = await storiesApi.plan(brief, brandId, platform);
      const plan: StoryPlan = {
        slides: (result.slides || result.story_plan?.slides || []).map((s: any, i: number) => ({
          index: i,
          role: s.role || ["hook", "detail", "urgency", "cta"][i % 4],
          headline: s.headline || s.title || `Slide ${i + 1}`,
          subtext: s.subtext || s.description || "",
          duration: s.duration || 3,
          animation: s.animation || "fade_in",
          image_url: s.image_url,
          rendered: false,
        })),
        platform,
        brand_id: brandId,
        theme: result.theme,
      };
      setStoryPlan(plan);
      setPageState("planned");
      // Track story_id if returned
      if (result.story_id || result.id) {
        setStoryId(result.story_id || result.id);
      }
      toast.success(`Story planifiee : ${plan.slides.length} slides`);
    } catch (err: any) {
      setError(err.message || "Erreur lors de la planification");
      setPageState("initial");
    }
  };

  const handleRenderSlide = async (slideIndex: number) => {
    if (!storyPlan) return;
    setRenderProgress((prev) => ({ ...prev, [slideIndex]: true }));
    try {
      const result = await storiesApi.render(storyPlan, brandId, slideIndex);
      setStoryPlan((prev) => {
        if (!prev) return prev;
        const slides = [...prev.slides];
        slides[slideIndex] = {
          ...slides[slideIndex],
          image_url: result.image_url || result.slides?.[slideIndex]?.image_url,
          rendered: true,
        };
        return { ...prev, slides };
      });
      toast.success(`Slide ${slideIndex + 1} rendue`);
    } catch (err: any) {
      toast.error(err.message || "Erreur de rendu");
    } finally {
      setRenderProgress((prev) => ({ ...prev, [slideIndex]: false }));
    }
  };

  const handleRenderAll = async () => {
    if (!storyPlan) return;
    setPageState("rendering");
    for (let i = 0; i < storyPlan.slides.length; i++) {
      await handleRenderSlide(i);
    }
    setPageState("rendered");
    toast.success("Toutes les slides sont pretes !");
  };

  const handleGenerateVideo = async () => {
    if (!storyPlan) return;
    setPageState("rendering");
    try {
      // Build the plan with rendered slide URLs + music mood
      const planForVideo = {
        slides: storyPlan.slides.map((s) => ({
          ...s,
          image_url: s.image_url,
          s3_key: s.image_url?.includes("/optimusai/") ? s.image_url.split("/optimusai/")[1] : undefined,
        })),
        music_mood: musicMood,
      };
      const result = await storiesApi.video(planForVideo);
      if (result.error) {
        throw new Error(result.error);
      }
      setVideoUrl(result.video_url || result.url);
      // Track story_id if returned
      if (result.story_id || result.id) {
        setStoryId(result.story_id || result.id);
      }
      setPageState("video_ready");
      toast.success("Video generee avec succes !");
    } catch (err: any) {
      toast.error(err.message || "Erreur de generation video");
      setPageState("rendered");
    }
  };

  // Quick action: fill brief and auto-generate
  const handleQuickAction = (qa: typeof QUICK_ACTIONS[0]) => {
    setBrief(qa.brief);
    setMusicMood(qa.mood || "upbeat");
  };

  // One-click: plan + render all slides
  const handleOneClick = async () => {
    if (!brief.trim() || !brandId) {
      toast.error("Remplissez le brief et sélectionnez une marque");
      return;
    }
    setPageState("planning");
    setError(null);
    setStoryPlan(null);
    setActiveSlide(0);
    setRenderProgress({});
    setVideoUrl(null);
    setStoryId(null);

    try {
      // Step 1: Plan
      const result = await storiesApi.plan(brief, brandId, platform);
      const plan: StoryPlan = {
        slides: (result.slides || result.story_plan?.slides || []).map((s: any, i: number) => ({
          index: i,
          role: s.role || ["hook", "detail", "urgency", "cta"][i % 4],
          headline: s.headline || s.title || `Slide ${i + 1}`,
          subtext: s.subtext || s.description || "",
          duration: s.duration || 3,
          animation: s.animation || "fade_in",
          image_url: s.image_url,
          rendered: false,
        })),
        platform,
        brand_id: brandId,
        theme: result.theme,
      };
      setStoryPlan(plan);
      if (result.story_id || result.id) {
        setStoryId(result.story_id || result.id);
      }
      setPageState("rendering");
      toast.success(`${plan.slides.length} slides planifiées, rendu en cours...`);

      // Step 2: Render all
      for (let i = 0; i < plan.slides.length; i++) {
        setRenderProgress((prev) => ({ ...prev, [i]: true }));
        try {
          const renderResult = await storiesApi.render(plan, brandId, i);
          plan.slides[i].image_url = renderResult.image_url || renderResult.slides?.[i]?.image_url;
          plan.slides[i].rendered = true;
          setStoryPlan({ ...plan });
        } catch {
          // Continue with next slide
        } finally {
          setRenderProgress((prev) => ({ ...prev, [i]: false }));
        }
      }

      setStoryPlan({ ...plan });
      setPageState("rendered");
      toast.success("Story complete !");
    } catch (err: any) {
      setError(err.message || "Erreur");
      setPageState("initial");
    }
  };

  // Load a saved story into the editor
  const handleLoadStory = async (story: any) => {
    try {
      const full = await storiesApi.get(story.id);
      const slides = (full.slides || full.story_plan?.slides || []).map((s: any, i: number) => ({
        index: i,
        role: s.role || ["hook", "detail", "urgency", "cta"][i % 4],
        headline: s.headline || s.title || `Slide ${i + 1}`,
        subtext: s.subtext || s.description || "",
        duration: s.duration || 3,
        animation: s.animation || "fade_in",
        image_url: s.image_url,
        rendered: !!s.image_url,
      }));

      const plan: StoryPlan = {
        slides,
        platform: full.platform || story.platform || "instagram",
        brand_id: full.brand_id || story.brand_id || brandId,
        theme: full.theme,
      };

      setStoryPlan(plan);
      setBrief(full.brief || story.brief || "");
      setPlatform(plan.platform);
      if (plan.brand_id) setBrandId(plan.brand_id);
      setStoryId(story.id);
      setVideoUrl(full.video_url || null);
      setActiveSlide(0);
      setRenderProgress({});

      // Determine page state
      if (full.video_url) {
        setPageState("video_ready");
      } else if (slides.some((s: any) => s.image_url)) {
        setPageState("rendered");
      } else {
        setPageState("planned");
      }

      setActiveTab("create");
      toast.success("Story chargee dans l'editeur");
    } catch (err: any) {
      toast.error("Erreur lors du chargement", { description: err.message });
    }
  };

  // Delete a saved story
  const handleDeleteStory = async (id: string) => {
    if (!confirm("Supprimer cette story ?")) return;
    try {
      await storiesApi.delete(id);
      toast.success("Story supprimee");
      setStoryHistory((prev) => prev.filter((s) => s.id !== id));
      if (storyId === id) {
        setStoryId(null);
      }
    } catch (err: any) {
      toast.error("Erreur lors de la suppression", { description: err.message });
    }
  };

  const updateSlide = useCallback((field: string, value: any) => {
    setStoryPlan((prev) => {
      if (!prev) return prev;
      const slides = [...prev.slides];
      slides[activeSlide] = { ...slides[activeSlide], [field]: value };
      return { ...prev, slides };
    });
  }, [activeSlide]);

  const currentSlide = storyPlan?.slides[activeSlide];

  return (
    <div className="max-w-7xl">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-purple-600 shadow-lg shadow-brand-500/20">
            <Film className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Story Creator</h1>
            <p className="text-sm text-gray-500">
              Creez des stories captivantes avec l'IA en quelques secondes
            </p>
          </div>
        </div>
      </div>

      {/* Tab navigation */}
      <div className="flex items-center gap-2 mb-6">
        <button
          onClick={() => setActiveTab("create")}
          className={cn(
            "flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-all",
            activeTab === "create"
              ? "bg-brand-500 text-white shadow-sm"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          )}
        >
          <Sparkles className="h-4 w-4" /> Creer
        </button>
        <button
          onClick={() => setActiveTab("history")}
          className={cn(
            "flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-all",
            activeTab === "history"
              ? "bg-brand-500 text-white shadow-sm"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          )}
        >
          <Layout className="h-4 w-4" /> Mes Stories
          {storyHistory.length > 0 && (
            <span className={cn(
              "rounded-full px-1.5 py-0.5 text-[10px] font-bold",
              activeTab === "history" ? "bg-white/20 text-white" : "bg-gray-200 text-gray-500"
            )}>
              {storyHistory.length}
            </span>
          )}
        </button>
      </div>

      {/* ─── History Tab ──────────────────────────────────────── */}
      {activeTab === "history" && (
        <div className="space-y-4">
          {loadingHistory && (
            <div className="surface flex items-center justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
              <span className="ml-2 text-sm text-gray-500">Chargement...</span>
            </div>
          )}

          {!loadingHistory && storyHistory.length === 0 && (
            <div className="surface flex flex-col items-center py-16 text-center">
              <Film className="h-12 w-12 text-gray-200" />
              <p className="mt-4 text-sm font-medium text-gray-500">Aucune story sauvegardee</p>
              <p className="mt-1 text-xs text-gray-400">
                Creez votre premiere story et elle apparaitra ici
              </p>
              <button
                onClick={() => setActiveTab("create")}
                className="mt-4 btn-primary px-6 py-2"
              >
                <Sparkles className="h-4 w-4" /> Creer une story
              </button>
            </div>
          )}

          {!loadingHistory && storyHistory.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {storyHistory.map((story) => {
                const slides = story.slides || story.story_plan?.slides || [];
                const firstSlide = slides[0];
                const platformBadge = PLATFORM_BADGES[story.platform] || PLATFORM_BADGES.instagram;
                const statusKey = story.video_url ? "video_ready" : slides.some((s: any) => s.image_url) ? "rendered" : story.status || "draft";
                const statusBadge = STATUS_BADGES[statusKey] || STATUS_BADGES.draft;
                const totalDuration = slides.reduce((sum: number, s: any) => sum + (s.duration || 3), 0);
                const createdDate = story.created_at ? new Date(story.created_at) : null;

                return (
                  <div
                    key={story.id}
                    className="surface overflow-hidden hover:shadow-lg transition-all cursor-pointer group"
                    onClick={() => handleLoadStory(story)}
                  >
                    {/* Thumbnail */}
                    <div className="relative aspect-video overflow-hidden">
                      {firstSlide?.image_url ? (
                        <img
                          src={firstSlide.image_url}
                          alt={firstSlide.headline || "Story"}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        />
                      ) : (
                        <div className={cn(
                          "w-full h-full bg-gradient-to-br flex items-center justify-center",
                          GRADIENT_PRESETS[0]
                        )}>
                          <Film className="h-10 w-10 text-white/50" />
                        </div>
                      )}
                      {/* Overlay badges */}
                      <div className="absolute top-2 left-2 flex items-center gap-1.5">
                        <span className={cn("rounded-lg px-2 py-0.5 text-[10px] font-bold", platformBadge.color)}>
                          {platformBadge.label}
                        </span>
                        <span className={cn("rounded-lg px-2 py-0.5 text-[10px] font-bold", statusBadge.color)}>
                          {statusBadge.label}
                        </span>
                      </div>
                      {/* Video indicator */}
                      {story.video_url && (
                        <div className="absolute bottom-2 right-2 flex items-center gap-1 rounded-md bg-black/60 backdrop-blur-sm px-2 py-0.5">
                          <Video className="h-3 w-3 text-white" />
                          <span className="text-[10px] font-semibold text-white">Video</span>
                        </div>
                      )}
                    </div>

                    {/* Card content */}
                    <div className="p-4 space-y-2">
                      {/* Title / brief */}
                      <p className="text-sm font-semibold text-gray-900 line-clamp-2">
                        {story.brief || firstSlide?.headline || "Story sans titre"}
                      </p>

                      {/* Meta */}
                      <div className="flex items-center gap-3 text-[11px] text-gray-400">
                        <span className="flex items-center gap-1">
                          <Film className="h-3 w-3" />
                          {slides.length} slide{slides.length !== 1 ? "s" : ""}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {totalDuration}s
                        </span>
                        {createdDate && (
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {createdDate.toLocaleDateString("fr-FR", { day: "numeric", month: "short" })}
                          </span>
                        )}
                      </div>

                      {/* Delete button */}
                      <div className="flex justify-end pt-1">
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDeleteStory(story.id); }}
                          className="flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-gray-400 hover:text-red-500 hover:bg-red-50 transition-all"
                        >
                          <Trash2 className="h-3 w-3" /> Supprimer
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ─── Create Tab ───────────────────────────────────────── */}
      {activeTab === "create" && (
        <>
          {/* Quick Actions */}
          {pageState === "initial" && (
            <div className="mb-6">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Actions rapides</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {QUICK_ACTIONS.map((qa) => (
                  <button
                    key={qa.label}
                    onClick={() => handleQuickAction(qa)}
                    className={cn(
                      "flex items-center gap-2 rounded-xl border border-gray-100 px-3 py-2.5 text-left transition-all hover:border-brand-200 hover:bg-brand-50/30 hover:shadow-sm",
                      brief === qa.brief && "border-brand-400 bg-brand-50 shadow-sm"
                    )}
                  >
                    <span className="text-lg">{qa.emoji}</span>
                    <span className="text-xs font-medium text-gray-700">{qa.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Two-column layout */}
          <div className="flex gap-6 items-start">
            {/* ─── Left Column (60%) ─────────────────────────────── */}
            <div className="flex-1 min-w-0 space-y-5" style={{ flex: "0 0 60%" }}>

              {/* Brief Input Section */}
              <div className="surface p-5 space-y-4">
                <div className="flex items-center gap-2 mb-1">
                  <Sparkles className="h-4 w-4 text-brand-500" />
                  <h2 className="text-sm font-bold text-gray-900">Brief de la Story</h2>
                  {storyId && (
                    <span className="rounded-full bg-brand-50 px-2 py-0.5 text-[10px] font-bold text-brand-600">
                      Story sauvegardee
                    </span>
                  )}
                </div>

                <textarea
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                  placeholder="Decrivez votre story (ex: Promo -50% ce weekend sur toute la collection)"
                  rows={3}
                  className="input-base w-full resize-none"
                />

                {/* Platform pills */}
                <div>
                  <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2 block">
                    Plateforme
                  </label>
                  <div className="flex items-center gap-2">
                    {PLATFORMS.map((p) => (
                      <button
                        key={p.id}
                        onClick={() => setPlatform(p.id)}
                        className={cn(
                          "flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-all duration-200",
                          platform === p.id
                            ? "bg-brand-500 text-white shadow-sm shadow-brand-500/20"
                            : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                        )}
                      >
                        <span>{p.icon}</span> {p.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Brand selector */}
                {brandList && brandList.length > 1 && (
                  <div>
                    <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2 block">
                      Marque
                    </label>
                    <select
                      value={brandId}
                      onChange={(e) => setBrandId(e.target.value)}
                      className="input-base w-full"
                    >
                      {brandList.map((b) => (
                        <option key={b.id} value={b.id}>{b.name}</option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Generate buttons */}
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={handleGenerate}
                    disabled={!brief.trim() || !brandId || pageState === "planning" || pageState === "rendering"}
                    className="btn-primary py-3 text-sm font-bold"
                  >
                    {pageState === "planning" ? (
                      <><Loader2 className="h-4 w-4 animate-spin" /> Planification...</>
                    ) : (
                      <><Sparkles className="h-4 w-4" /> Planifier</>
                    )}
                  </button>
                  <button
                    onClick={handleOneClick}
                    disabled={!brief.trim() || !brandId || pageState === "planning" || pageState === "rendering"}
                    className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-brand-500 to-purple-600 px-4 py-3 text-sm font-bold text-white shadow-lg shadow-brand-500/20 hover:shadow-xl transition-all disabled:opacity-50"
                  >
                    {pageState === "rendering" ? (
                      <><Loader2 className="h-4 w-4 animate-spin" /> Rendu en cours...</>
                    ) : (
                      <><Wand2 className="h-4 w-4" /> Tout en un</>
                    )}
                  </button>
                </div>

                {error && (
                  <div className="rounded-xl bg-red-50 border border-red-100 p-3 text-sm text-red-600">
                    {error}
                  </div>
                )}
              </div>

              {/* Planning Progress */}
              {pageState === "planning" && (
                <StoryProgress steps={PLANNING_STEPS} />
              )}

              {/* Story Timeline */}
              {storyPlan && pageState !== "planning" && (
                <div className="surface p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Film className="h-4 w-4 text-brand-500" />
                      <h2 className="text-sm font-bold text-gray-900">Timeline</h2>
                      <span className="rounded-full bg-brand-50 px-2 py-0.5 text-[10px] font-bold text-brand-600">
                        {storyPlan.slides.length} slides
                      </span>
                    </div>
                  </div>

                  {/* Progress dots */}
                  <div className="flex items-center gap-1 justify-center">
                    {storyPlan.slides.map((_, i) => (
                      <div
                        key={i}
                        className={cn(
                          "h-1.5 rounded-full transition-all duration-300",
                          i === activeSlide ? "w-6 bg-brand-500" : "w-1.5 bg-gray-200"
                        )}
                      />
                    ))}
                  </div>

                  {/* Horizontal scrollable thumbnails */}
                  <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1 scroll-smooth">
                    {storyPlan.slides.map((slide, i) => {
                      const roleConf = ROLE_CONFIG[slide.role] || ROLE_CONFIG.detail;
                      const RoleIcon = roleConf.icon;
                      return (
                        <button
                          key={i}
                          onClick={() => setActiveSlide(i)}
                          className={cn(
                            "relative flex-shrink-0 w-28 rounded-2xl overflow-hidden transition-all duration-300 group",
                            i === activeSlide
                              ? "ring-2 ring-brand-500 ring-offset-2 shadow-lg shadow-brand-500/10 scale-105"
                              : "ring-1 ring-gray-200 hover:ring-brand-200 hover:shadow-md"
                          )}
                        >
                          {/* Thumbnail content */}
                          <div
                            className={cn(
                              "aspect-[9/16] flex flex-col items-center justify-center p-2 text-center",
                              slide.image_url
                                ? ""
                                : `bg-gradient-to-br ${GRADIENT_PRESETS[i % GRADIENT_PRESETS.length]}`
                            )}
                            style={slide.image_url ? {
                              backgroundImage: `url(${slide.image_url})`,
                              backgroundSize: "cover",
                              backgroundPosition: "center",
                            } : undefined}
                          >
                            {slide.image_url && (
                              <div className="absolute inset-0 bg-black/30" />
                            )}
                            <div className="relative z-10 flex flex-col items-center gap-1">
                              <span className="text-[9px] font-bold text-white/70">
                                {i + 1}
                              </span>
                              <p className="text-[9px] font-bold text-white leading-tight line-clamp-2">
                                {slide.headline}
                              </p>
                            </div>
                          </div>

                          {/* Role badge */}
                          <div className={cn(
                            "absolute top-1.5 left-1.5 flex items-center gap-0.5 rounded-md px-1.5 py-0.5",
                            roleConf.bgColor
                          )}>
                            <RoleIcon className={cn("h-2 w-2", roleConf.color)} />
                            <span className={cn("text-[7px] font-bold", roleConf.color)}>
                              {roleConf.label}
                            </span>
                          </div>

                          {/* Render status */}
                          {slide.rendered && (
                            <div className="absolute top-1.5 right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500">
                              <CheckCircle className="h-2.5 w-2.5 text-white" />
                            </div>
                          )}
                          {renderProgress[i] && (
                            <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-sm">
                              <Loader2 className="h-5 w-5 text-white animate-spin" />
                            </div>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Slide Editor */}
              {storyPlan && currentSlide && pageState !== "planning" && (
                <div className="surface p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Type className="h-4 w-4 text-brand-500" />
                      <h2 className="text-sm font-bold text-gray-900">
                        Editeur — Slide {activeSlide + 1}
                      </h2>
                      {(() => {
                        const rc = ROLE_CONFIG[currentSlide.role] || ROLE_CONFIG.detail;
                        return (
                          <span className={cn("flex items-center gap-1 rounded-lg px-2 py-0.5 text-[10px] font-bold", rc.bgColor, rc.color)}>
                            <rc.icon className="h-3 w-3" /> {rc.label}
                          </span>
                        );
                      })()}
                    </div>
                  </div>

                  {/* Headline */}
                  <div>
                    <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">
                      Titre principal
                    </label>
                    <input
                      type="text"
                      value={currentSlide.headline}
                      onChange={(e) => updateSlide("headline", e.target.value)}
                      className="input-base w-full font-semibold"
                    />
                  </div>

                  {/* Subtext */}
                  <div>
                    <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5 block">
                      Sous-texte
                    </label>
                    <input
                      type="text"
                      value={currentSlide.subtext}
                      onChange={(e) => updateSlide("subtext", e.target.value)}
                      className="input-base w-full"
                    />
                  </div>

                  {/* Duration slider */}
                  <div>
                    <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5 flex items-center gap-2">
                      <Clock className="h-3 w-3" /> Duree : {currentSlide.duration}s
                    </label>
                    <input
                      type="range"
                      min={2}
                      max={6}
                      step={0.5}
                      value={currentSlide.duration}
                      onChange={(e) => updateSlide("duration", parseFloat(e.target.value))}
                      className="w-full accent-brand-500"
                    />
                    <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                      <span>2s</span><span>4s</span><span>6s</span>
                    </div>
                  </div>

                  {/* Animation selector */}
                  <div>
                    <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2 block">
                      Animation
                    </label>
                    <div className="flex gap-2">
                      {ANIMATIONS.map((anim) => (
                        <button
                          key={anim.id}
                          onClick={() => updateSlide("animation", anim.id)}
                          className={cn(
                            "flex flex-col items-center gap-1 rounded-xl px-3 py-2 text-[11px] font-medium transition-all",
                            currentSlide.animation === anim.id
                              ? "bg-brand-500 text-white shadow-sm"
                              : "bg-gray-50 text-gray-500 hover:bg-gray-100"
                          )}
                        >
                          <anim.icon className="h-4 w-4" />
                          {anim.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Render buttons */}
                  <div className="flex gap-3 pt-2">
                    <button
                      onClick={() => handleRenderSlide(activeSlide)}
                      disabled={renderProgress[activeSlide]}
                      className="btn-primary flex-1 py-2.5"
                    >
                      {renderProgress[activeSlide] ? (
                        <><Loader2 className="h-4 w-4 animate-spin" /> Rendu en cours...</>
                      ) : (
                        <><Image className="h-4 w-4" /> Rendre cette slide</>
                      )}
                    </button>
                    <button
                      onClick={handleRenderAll}
                      disabled={pageState === "rendering"}
                      className={cn(
                        "flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all",
                        "bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-sm hover:shadow-md active:scale-[0.98]"
                      )}
                    >
                      {pageState === "rendering" ? (
                        <><Loader2 className="h-4 w-4 animate-spin" /> Rendu...</>
                      ) : (
                        <><RefreshCw className="h-4 w-4" /> Toutes les slides</>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* Video Section */}
              {(pageState === "rendered" || pageState === "video_ready" || pageState === "rendering") && storyPlan && (
                <div className="surface p-5 space-y-4">
                  <div className="flex items-center gap-2">
                    <Music className="h-4 w-4 text-brand-500" />
                    <h2 className="text-sm font-bold text-gray-900">Video Story</h2>
                  </div>

                  {/* Music mood selector */}
                  <div>
                    <label className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2 block">
                      Ambiance musicale
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {MUSIC_MOODS.map((mood) => (
                        <button
                          key={mood.id}
                          onClick={() => setMusicMood(mood.id)}
                          className={cn(
                            "flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium transition-all",
                            musicMood === mood.id
                              ? "bg-brand-500 text-white shadow-sm"
                              : "bg-gray-50 text-gray-600 hover:bg-gray-100"
                          )}
                        >
                          <span>{mood.emoji}</span> {mood.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Generate video button */}
                  {!videoUrl && (
                    <button
                      onClick={handleGenerateVideo}
                      disabled={pageState === "rendering"}
                      className="btn-primary w-full py-3 text-sm font-bold"
                    >
                      {pageState === "rendering" ? (
                        <><Loader2 className="h-4 w-4 animate-spin" /> Generation video...</>
                      ) : (
                        <><Film className="h-4 w-4" /> Generer la video</>
                      )}
                    </button>
                  )}

                  {/* Video player */}
                  {videoUrl && (
                    <div className="space-y-3">
                      <div className="rounded-2xl overflow-hidden bg-black">
                        <video
                          src={videoUrl}
                          controls
                          className="w-full"
                          style={{ maxHeight: 400 }}
                        />
                      </div>
                      <a
                        href={videoUrl}
                        download="story.mp4"
                        className={cn(
                          "flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-bold w-full transition-all",
                          "bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-sm hover:shadow-md active:scale-[0.98]"
                        )}
                      >
                        <Download className="h-4 w-4" /> Telecharger la video
                      </a>
                      <button
                        onClick={() => {
                          setPageState("initial");
                          setBrief("");
                          setStoryPlan(null);
                          setVideoUrl(null);
                          setActiveSlide(0);
                          setRenderProgress({});
                          setStoryId(null);
                          setPersistedValue("story-state", null);
                        }}
                        className="flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-bold w-full bg-gray-100 text-gray-700 hover:bg-gray-200 transition-all"
                      >
                        <RefreshCw className="h-4 w-4" /> Nouvelle Story
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* ─── Right Column (40%) — Phone Preview ────────────── */}
            <div className="sticky top-6" style={{ flex: "0 0 37%" }}>
              <div className="flex items-center justify-between mb-3">
                <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                  Apercu en direct
                </p>
                {storyPlan && (
                  <button
                    onClick={() => setIsAutoPlaying(!isAutoPlaying)}
                    className={cn(
                      "flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-[11px] font-semibold transition-all",
                      isAutoPlaying
                        ? "bg-brand-500 text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    )}
                  >
                    {isAutoPlaying ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
                    {isAutoPlaying ? "Pause" : "Lecture"}
                  </button>
                )}
              </div>

              <StoryPhonePreview
                slides={storyPlan?.slides || []}
                activeSlide={activeSlide}
                onSlideChange={setActiveSlide}
                pageState={pageState}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ─── Phone Preview Component ─────────────────────────────────

function StoryPhonePreview({
  slides,
  activeSlide,
  onSlideChange,
  pageState,
}: {
  slides: StorySlide[];
  activeSlide: number;
  onSlideChange: (i: number) => void;
  pageState: PageState;
}) {
  const slide = slides[activeSlide];

  const handleTap = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!slides.length) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    if (x < rect.width / 3) {
      onSlideChange(Math.max(0, activeSlide - 1));
    } else if (x > (rect.width * 2) / 3) {
      onSlideChange(Math.min(slides.length - 1, activeSlide + 1));
    }
  };

  return (
    <div className="relative mx-auto" style={{ width: 300 }}>
      {/* Phone frame */}
      <div className="relative rounded-[2.8rem] border-[6px] border-gray-900 bg-gray-900 shadow-2xl shadow-gray-900/30">
        {/* Dynamic island */}
        <div className="absolute left-1/2 top-0 z-30 -translate-x-1/2 translate-y-2">
          <div className="h-7 w-28 rounded-full bg-gray-900" />
        </div>

        {/* Screen */}
        <div
          className="relative overflow-hidden rounded-[2.2rem] bg-gray-900 cursor-pointer select-none"
          onClick={handleTap}
          style={{ aspectRatio: "9/16" }}
        >
          {/* Story progress bars */}
          {slides.length > 0 && (
            <div className="absolute top-10 left-3 right-3 z-20 flex gap-1">
              {slides.map((_, i) => (
                <div key={i} className="flex-1 h-[3px] rounded-full bg-white/30 overflow-hidden">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-500",
                      i < activeSlide ? "w-full bg-white" :
                      i === activeSlide ? "w-full bg-white" :
                      "w-0 bg-white"
                    )}
                  />
                </div>
              ))}
            </div>
          )}

          {/* Account bar (Instagram-like) */}
          {slides.length > 0 && (
            <div className="absolute top-14 left-3 z-20 flex items-center gap-2">
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-brand-400 to-brand-600 ring-2 ring-white/50 flex items-center justify-center">
                <Zap className="h-3.5 w-3.5 text-white" />
              </div>
              <span className="text-white text-xs font-semibold drop-shadow-lg">optimusai</span>
            </div>
          )}

          {/* Slide content */}
          {!slides.length ? (
            /* Empty state */
            <div className="flex h-full flex-col items-center justify-center p-8 text-center bg-gradient-to-br from-gray-800 via-gray-900 to-black">
              <div className="relative mb-4">
                <div className="h-16 w-16 rounded-2xl bg-white/5 backdrop-blur-sm flex items-center justify-center border border-white/10">
                  <Film className="h-8 w-8 text-white/40" />
                </div>
                <div className="absolute -bottom-1 -right-1 h-6 w-6 rounded-full bg-brand-500 flex items-center justify-center">
                  <Sparkles className="h-3 w-3 text-white" />
                </div>
              </div>
              <p className="text-sm font-semibold text-white/60 mb-1">Votre story</p>
              <p className="text-[11px] text-white/30">
                Remplissez le brief pour commencer
              </p>
            </div>
          ) : slide ? (
            /* Slide view */
            <div className="relative h-full w-full">
              {slide.image_url ? (
                /* Rendered slide with image */
                <div className="absolute inset-0">
                  <img
                    src={slide.image_url}
                    alt={slide.headline}
                    className="h-full w-full object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/30" />
                </div>
              ) : (
                /* Text-only placeholder */
                <div className={cn(
                  "absolute inset-0 bg-gradient-to-br",
                  GRADIENT_PRESETS[activeSlide % GRADIENT_PRESETS.length]
                )}>
                  {/* Decorative elements */}
                  <div className="absolute top-1/4 -left-8 h-40 w-40 rounded-full bg-white/10 blur-3xl" />
                  <div className="absolute bottom-1/4 -right-8 h-32 w-32 rounded-full bg-white/10 blur-3xl" />
                </div>
              )}

              {/* Role badge */}
              {(() => {
                const rc = ROLE_CONFIG[slide.role] || ROLE_CONFIG.detail;
                return (
                  <div className="absolute top-24 left-3 z-20">
                    <div className={cn(
                      "flex items-center gap-1 rounded-lg px-2 py-1 backdrop-blur-md",
                      "bg-black/30 border border-white/10"
                    )}>
                      <rc.icon className="h-3 w-3 text-white" />
                      <span className="text-[9px] font-bold text-white tracking-wider">
                        {rc.label}
                      </span>
                    </div>
                  </div>
                );
              })()}

              {/* Text content — centered */}
              <div className="absolute inset-0 flex flex-col items-center justify-center p-6 z-10">
                <h3 className="text-xl font-black text-white text-center leading-tight drop-shadow-lg mb-2">
                  {slide.headline}
                </h3>
                {slide.subtext && (
                  <p className="text-sm text-white/80 text-center drop-shadow-md leading-snug max-w-[220px]">
                    {slide.subtext}
                  </p>
                )}
              </div>

              {/* CTA button overlay for CTA slides */}
              {slide.role === "cta" && (
                <div className="absolute bottom-20 inset-x-0 flex justify-center z-10">
                  <div className="rounded-full bg-white px-6 py-2.5 shadow-2xl">
                    <span className="text-sm font-bold text-gray-900">
                      {slide.subtext || "En savoir plus"}
                    </span>
                  </div>
                </div>
              )}

              {/* Navigation hints */}
              <div className="absolute inset-y-0 left-0 w-1/3 z-10" />
              <div className="absolute inset-y-0 right-0 w-1/3 z-10" />

              {/* Tap zone indicators on hover */}
              <div className="absolute bottom-8 inset-x-0 flex justify-center gap-4 z-10 opacity-0 hover:opacity-100 transition-opacity">
                {activeSlide > 0 && (
                  <div className="flex items-center gap-1 rounded-full bg-black/40 backdrop-blur-sm px-3 py-1">
                    <ChevronLeft className="h-3 w-3 text-white" />
                    <span className="text-[10px] text-white">Precedent</span>
                  </div>
                )}
                {activeSlide < slides.length - 1 && (
                  <div className="flex items-center gap-1 rounded-full bg-black/40 backdrop-blur-sm px-3 py-1">
                    <span className="text-[10px] text-white">Suivant</span>
                    <ChevronRight className="h-3 w-3 text-white" />
                  </div>
                )}
              </div>
            </div>
          ) : null}

          {/* Instagram-like bottom UI */}
          {slides.length > 0 && (
            <div className="absolute bottom-3 left-3 right-3 z-20">
              <div className="flex items-center gap-2">
                <div className="flex-1 rounded-full border border-white/30 bg-white/10 backdrop-blur-sm px-4 py-2">
                  <span className="text-[11px] text-white/60">Envoyer un message</span>
                </div>
                <div className="flex gap-2">
                  <div className="h-8 w-8 rounded-full bg-white/10 backdrop-blur-sm flex items-center justify-center border border-white/20">
                    <svg className="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" /></svg>
                  </div>
                  <div className="h-8 w-8 rounded-full bg-white/10 backdrop-blur-sm flex items-center justify-center border border-white/20">
                    <svg className="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Phone home indicator */}
      <div className="absolute bottom-2 left-1/2 -translate-x-1/2 z-10">
        <div className="h-1 w-28 rounded-full bg-gray-600" />
      </div>

      {/* Slide counter below phone */}
      {slides.length > 0 && (
        <div className="flex items-center justify-center gap-3 mt-4">
          <button
            onClick={() => onSlideChange(Math.max(0, activeSlide - 1))}
            disabled={activeSlide === 0}
            className="rounded-full p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 disabled:opacity-30 transition-all"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-xs font-semibold text-gray-500">
            {activeSlide + 1} / {slides.length}
          </span>
          <button
            onClick={() => onSlideChange(Math.min(slides.length - 1, activeSlide + 1))}
            disabled={activeSlide === slides.length - 1}
            className="rounded-full p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 disabled:opacity-30 transition-all"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Story Planning Progress ─────────────────────────────────

function StoryProgress({ steps }: { steps: { label: string; icon: React.ElementType; duration: number }[] }) {
  const [elapsed, setElapsed] = useState(0);
  const [currentFact, setCurrentFact] = useState(0);
  const startRef = useRef(Date.now());

  const FACTS = [
    "L'IA analyse les meilleures stories de votre secteur",
    "Chaque slide est optimisee pour retenir l'attention",
    "La structure Hook → Detail → Urgence → CTA maximise les conversions",
    "Les stories generent 2x plus d'engagement que les posts classiques",
    "Le format vertical 9:16 est le plus consomme au monde",
  ];

  const totalEstimated = steps.reduce((s, st) => s + st.duration, 0);

  useEffect(() => {
    startRef.current = Date.now();
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentFact((p) => (p + 1) % FACTS.length);
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  let accum = 0;
  let activeStep = 0;
  for (let i = 0; i < steps.length; i++) {
    accum += steps[i].duration;
    if (elapsed < accum) { activeStep = i; break; }
    if (i === steps.length - 1) activeStep = i;
  }

  const rawProgress = Math.min((elapsed / totalEstimated) * 100, 95);
  const progressWidth = Math.max(rawProgress, 5);

  return (
    <div className="surface p-5 space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300 bg-gradient-to-br from-brand-50/50 via-white to-purple-50/50">
      <div className="flex items-center gap-2">
        <div className="relative">
          <div className="h-10 w-10 rounded-xl bg-brand-500 flex items-center justify-center animate-pulse">
            <Film className="h-5 w-5 text-white" />
          </div>
          <span className="absolute -bottom-1 -right-1 flex h-4 w-4">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-4 w-4 bg-brand-500" />
          </span>
        </div>
        <div>
          <p className="text-sm font-bold text-gray-900">L'IA planifie votre story...</p>
          <p className="text-xs text-gray-500">
            Temps ecoule : <span className="font-mono font-semibold text-brand-600">{elapsed}s</span>
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[11px] font-semibold text-brand-600">{Math.round(progressWidth)}%</span>
          <span className="text-[11px] text-gray-400">{steps[activeStep]?.label}</span>
        </div>
        <div className="h-2.5 rounded-full bg-gray-100 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-brand-400 via-brand-500 to-purple-500 transition-all duration-1000 ease-out relative"
            style={{ width: `${progressWidth}%` }}
          >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
          </div>
        </div>
      </div>

      {/* Steps */}
      <div className="flex items-center gap-1 overflow-x-auto pb-1">
        {steps.map((step, i) => {
          const Icon = step.icon;
          const isDone = i < activeStep;
          const isCurrent = i === activeStep;
          return (
            <div
              key={i}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[11px] font-medium whitespace-nowrap transition-all duration-500",
                isDone ? "bg-brand-100 text-brand-700" :
                isCurrent ? "bg-brand-500 text-white shadow-sm shadow-brand-500/20" :
                "bg-gray-50 text-gray-400"
              )}
            >
              {isDone ? (
                <CheckCircle className="h-3 w-3" />
              ) : (
                <Icon className={cn("h-3 w-3", isCurrent && "animate-pulse")} />
              )}
              <span className="hidden sm:inline">{step.label}</span>
            </div>
          );
        })}
      </div>

      {/* Fun fact */}
      <div className="flex items-center gap-2 rounded-xl bg-white/80 px-3 py-2.5 border border-gray-50">
        <Sparkles className="h-4 w-4 text-amber-500 shrink-0" />
        <p className="text-xs text-gray-600" key={currentFact}>
          <span className="font-semibold text-gray-700">Le saviez-vous ?</span> {FACTS[currentFact]}
        </p>
      </div>
    </div>
  );
}

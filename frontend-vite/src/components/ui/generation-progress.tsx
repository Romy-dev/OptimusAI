import { useState, useEffect, useRef } from "react";
import { Zap, Sparkles, Palette, Brain, Wand2, CheckCircle, ImageIcon, FileText, Layout } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Fun facts to keep users entertained while waiting ─────────

const FUN_FACTS = [
  "L'IA analyse plus de 50 parametres pour personnaliser votre contenu",
  "Chaque post est adapte aux specificites de votre marque",
  "Les hashtags sont selectionnes pour maximiser votre visibilite",
  "Le ton est ajuste en fonction de votre audience cible",
  "L'IA genere en moyenne 3 variantes avant de choisir la meilleure",
  "Votre contenu est verifie automatiquement pour la conformite",
  "Les emojis sont places strategiquement pour capter l'attention",
  "FLUX utilise 4 etapes de diffusion pour creer chaque image",
  "L'image est optimisee pour chaque reseau social",
  "Les couleurs de votre marque guident la generation visuelle",
  "Chaque affiche est composee avec un titre accrocheur et un CTA",
  "L'IA s'inspire des meilleures pratiques du marketing africain",
  "Plus de 1000 styles visuels sont analyses pour chaque creation",
  "Le format est automatiquement adapte a chaque plateforme",
];

// ─── Step definitions per generation type ──────────────────────

interface Step {
  label: string;
  icon: React.ElementType;
  duration: number; // estimated seconds for this step
}

const STEPS: Record<string, Step[]> = {
  post: [
    { label: "Analyse du brief", icon: Brain, duration: 3 },
    { label: "Contexte de marque", icon: Palette, duration: 2 },
    { label: "Redaction IA", icon: Sparkles, duration: 15 },
    { label: "Verification qualite", icon: CheckCircle, duration: 5 },
  ],
  image: [
    { label: "Expansion du prompt", icon: Brain, duration: 5 },
    { label: "Initialisation FLUX", icon: Zap, duration: 10 },
    { label: "Diffusion etape 1/4", icon: ImageIcon, duration: 120 },
    { label: "Diffusion etape 2/4", icon: ImageIcon, duration: 120 },
    { label: "Diffusion etape 3/4", icon: ImageIcon, duration: 120 },
    { label: "Diffusion etape 4/4", icon: ImageIcon, duration: 120 },
    { label: "Post-traitement", icon: Wand2, duration: 10 },
  ],
  poster: [
    { label: "Creation du concept", icon: Brain, duration: 5 },
    { label: "Generation du visuel", icon: ImageIcon, duration: 300 },
    { label: "Composition texte + CTA", icon: Layout, duration: 5 },
    { label: "Finalisation", icon: Wand2, duration: 3 },
  ],
};

// ─── Component ─────────────────────────────────────────────────

interface GenerationProgressProps {
  type: "post" | "image" | "poster";
  active: boolean;
  prompt?: string;
}

export function GenerationProgress({ type, active, prompt }: GenerationProgressProps) {
  const [elapsed, setElapsed] = useState(0);
  const [currentFact, setCurrentFact] = useState(0);
  const startRef = useRef(Date.now());

  const steps = STEPS[type] || STEPS.post;
  const totalEstimated = steps.reduce((sum, s) => sum + s.duration, 0);

  // Timer
  useEffect(() => {
    if (!active) { setElapsed(0); return; }
    startRef.current = Date.now();
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [active]);

  // Rotate fun facts every 6s
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(() => {
      setCurrentFact((prev) => (prev + 1) % FUN_FACTS.length);
    }, 6000);
    return () => clearInterval(timer);
  }, [active]);

  if (!active) return null;

  // Calculate which step we're on based on elapsed time
  let accum = 0;
  let activeStep = 0;
  for (let i = 0; i < steps.length; i++) {
    accum += steps[i].duration;
    if (elapsed < accum) { activeStep = i; break; }
    if (i === steps.length - 1) activeStep = i;
  }

  // Progress percentage (cap at 95% until truly done)
  const rawProgress = Math.min((elapsed / totalEstimated) * 100, 95);
  const progressWidth = Math.max(rawProgress, 5);

  // Format elapsed time
  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  const timeStr = mins > 0 ? `${mins}m ${secs.toString().padStart(2, "0")}s` : `${secs}s`;

  return (
    <div className="mt-4 rounded-2xl bg-gradient-to-br from-brand-50 via-white to-sky-50 border border-brand-100 p-5 space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="relative">
            <div className="h-10 w-10 rounded-xl bg-brand-500 flex items-center justify-center animate-pulse">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <span className="absolute -bottom-1 -right-1 flex h-4 w-4">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-4 w-4 bg-brand-500" />
            </span>
          </div>
          <div>
            <p className="text-sm font-bold text-gray-900">
              {type === "post" ? "L'IA redige votre post..." : type === "poster" ? "Creation de l'affiche..." : "FLUX genere votre image..."}
            </p>
            <p className="text-xs text-gray-500">
              Temps ecoule : <span className="font-mono font-semibold text-brand-600">{timeStr}</span>
              {totalEstimated > 60 && (
                <> · Estime : ~{Math.ceil(totalEstimated / 60)} min</>
              )}
            </p>
          </div>
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
            className="h-full rounded-full bg-gradient-to-r from-brand-400 via-brand-500 to-sky-500 transition-all duration-1000 ease-out relative"
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

      {/* Prompt reminder */}
      {prompt && (
        <div className="rounded-xl bg-white/60 border border-gray-100 px-3 py-2">
          <p className="text-[11px] text-gray-400 mb-0.5">Votre brief :</p>
          <p className="text-xs text-gray-600 line-clamp-2 italic">"{prompt}"</p>
        </div>
      )}

      {/* Fun fact */}
      <div className="flex items-center gap-2 rounded-xl bg-white/80 px-3 py-2.5 border border-gray-50">
        <Sparkles className="h-4 w-4 text-amber-500 shrink-0" />
        <p className="text-xs text-gray-600 transition-opacity duration-500" key={currentFact}>
          <span className="font-semibold text-gray-700">Le saviez-vous ?</span> {FUN_FACTS[currentFact]}
        </p>
      </div>
    </div>
  );
}

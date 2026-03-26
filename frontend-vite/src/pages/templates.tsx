import { useState, useRef, useEffect, useCallback } from "react";
import { useWebSocket } from "@/hooks/use-websocket";
import { toast } from "sonner";
import {
  Upload, Trash2, RefreshCw, Loader2, Eye, Sparkles, Palette,
  CheckCircle, AlertCircle, Clock, X, Layers, Type, Image as ImageIcon,
  Layout, Zap, ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi } from "@/hooks/use-api";
import { designTemplates as dtApi, brands as brandsApi, DesignTemplateItem } from "@/lib/api";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";

const STATUS_CONFIG: Record<string, { icon: typeof Clock; color: string; label: string }> = {
  pending: { icon: Clock, color: "text-gray-500 bg-gray-100", label: "En attente" },
  analyzing: { icon: Loader2, color: "text-brand-600 bg-brand-50", label: "Analyse VLM..." },
  completed: { icon: CheckCircle, color: "text-emerald-600 bg-emerald-50", label: "Analyse" },
  failed: { icon: AlertCircle, color: "text-red-600 bg-red-50", label: "Echec" },
};

export default function TemplatesPage() {
  const { data: brandList } = useApi(() => brandsApi.list(), [], "brands-list");
  const brandId = brandList?.[0]?.id;
  const { data: templates, refetch } = useApi(
    () => (brandId ? dtApi.list(brandId) : Promise.resolve([])),
    [brandId],
    `templates-${brandId}`,
  );
  const { data: brandDna, refetch: refetchDna } = useApi(
    () => (brandId ? dtApi.brandDna(brandId) : Promise.resolve(null)),
    [brandId],
    `brand-dna-${brandId}`,
  );

  const [uploading, setUploading] = useState(false);
  const [previewDna, setPreviewDna] = useState<DesignTemplateItem | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DesignTemplateItem | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // WebSocket listener for real-time analysis updates (replaces polling)
  const { notifications } = useWebSocket();
  const [analyzingIds, setAnalyzingIds] = useState<Set<string>>(new Set());

  // Listen for design_analysis_complete events from WebSocket
  useEffect(() => {
    const latest = notifications[0];
    if (!latest || latest.type !== "design_analysis_complete") return;
    const templateId = latest.data?.template_id;
    if (!templateId) return;

    setAnalyzingIds((prev) => { const n = new Set(prev); n.delete(templateId); return n; });
    refetch();
    refetchDna();

    if (latest.data.status === "completed") {
      toast.success("Analyse VLM terminee — Design DNA extrait");
    } else {
      toast.error("Echec de l'analyse", { description: latest.data.message || "" });
    }
  }, [notifications[0]?.id]);

  // Fallback polling for when WS is not available (every 5s for analyzing templates)
  useEffect(() => {
    if (analyzingIds.size === 0) return;
    const poll = setInterval(async () => {
      for (const id of analyzingIds) {
        try {
          const status = await dtApi.status(id);
          if (status.analysis_status === "completed" || status.analysis_status === "failed") {
            setAnalyzingIds((prev) => { const n = new Set(prev); n.delete(id); return n; });
            refetch();
            refetchDna();
            if (status.analysis_status === "completed") toast.success("Analyse VLM terminee");
            else toast.error("Echec de l'analyse");
          }
        } catch { /* ignore */ }
      }
    }, 5000);
    return () => clearInterval(poll);
  }, [analyzingIds.size]);

  const trackAnalyzing = (templateId: string) => {
    setAnalyzingIds((prev) => new Set(prev).add(templateId));
  };

  const handleUpload = async (files: FileList | null) => {
    if (!files || !brandId) return;
    setUploading(true);
    let success = 0;
    for (const file of Array.from(files)) {
      try {
        const result = await dtApi.upload(file, brandId, file.name.replace(/\.\w+$/, ""));
        success++;
        // Start polling for this template
        trackAnalyzing(result.id);
      } catch (err: any) {
        toast.error(`Echec: ${file.name}`, { description: err.message });
      }
    }
    if (success > 0) {
      toast.success(`${success} template(s) uploade(s) — analyse VLM en cours...`);
      refetch();
    }
    setUploading(false);
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleReanalyze = async (id: string) => {
    try {
      await dtApi.reanalyze(id);
      toast.info("Re-analyse VLM lancee...");
      refetch();
      trackAnalyzing(id);
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await dtApi.delete(deleteTarget.id);
      toast.success("Template supprime");
      setDeleteTarget(null);
      refetch();
      refetchDna();
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  // Auto-poll templates that are still analyzing on page load
  useEffect(() => {
    if (!templates) return;
    templates.forEach((t) => {
      if (t.analysis_status === "analyzing" && !analyzingIds.has(t.id)) {
        trackAnalyzing(t.id);
      }
    });
  }, [templates]);

  const dna = brandDna?.merged_dna || {};
  const templateList = templates || [];

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Mes Templates</h1>
        <p className="mt-1 text-sm text-gray-500">
          Uploadez vos affiches de reference — l'IA analyse chaque detail pour reproduire votre style
        </p>
      </div>

      {/* Upload zone */}
      <div
        className={cn(
          "surface border-2 border-dashed p-8 text-center cursor-pointer transition-all hover:border-brand-300 hover:bg-brand-50/30",
          uploading && "pointer-events-none opacity-60",
        )}
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add("border-brand-400", "bg-brand-50"); }}
        onDragLeave={(e) => { e.currentTarget.classList.remove("border-brand-400", "bg-brand-50"); }}
        onDrop={(e) => { e.preventDefault(); e.currentTarget.classList.remove("border-brand-400", "bg-brand-50"); handleUpload(e.dataTransfer.files); }}
      >
        <input ref={fileRef} type="file" accept="image/*" multiple className="hidden" onChange={(e) => handleUpload(e.target.files)} />
        {uploading ? (
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="h-10 w-10 animate-spin text-brand-500" />
            <p className="text-sm font-medium text-brand-600">Upload et analyse VLM en cours...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-100 text-brand-600">
              <Upload className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-800">Glissez vos affiches ici ou cliquez</p>
              <p className="text-xs text-gray-400 mt-1">PNG, JPG, WEBP — max 10 Mo — plusieurs fichiers acceptes</p>
            </div>
          </div>
        )}
      </div>

      {/* Brand Design DNA summary */}
      {brandDna && brandDna.template_count > 0 && (
        <div className="surface p-5">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="h-4 w-4 text-brand-500" />
            <h2 className="text-sm font-bold text-gray-900">Design DNA de votre marque</h2>
            <span className="badge bg-brand-50 text-brand-600">{brandDna.template_count} template(s)</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {/* Fonts */}
            {brandDna.preferred_fonts?.length > 0 && (
              <div className="rounded-xl bg-gray-50 p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <Type className="h-3.5 w-3.5 text-gray-500" />
                  <span className="text-[11px] font-semibold text-gray-500 uppercase">Typographie</span>
                </div>
                {brandDna.preferred_fonts.map((f: string) => (
                  <p key={f} className="text-xs font-medium text-gray-800">{f}</p>
                ))}
              </div>
            )}

            {/* Colors */}
            {brandDna.color_palette?.length > 0 && (
              <div className="rounded-xl bg-gray-50 p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <Palette className="h-3.5 w-3.5 text-gray-500" />
                  <span className="text-[11px] font-semibold text-gray-500 uppercase">Couleurs</span>
                </div>
                <div className="flex gap-1.5 flex-wrap">
                  {brandDna.color_palette.slice(0, 6).map((c: any, i: number) => (
                    <div key={i} className="flex items-center gap-1">
                      <div className="h-5 w-5 rounded-md border border-gray-200" style={{ backgroundColor: c.hex || c }} />
                      <span className="text-[10px] text-gray-500">{c.role || ""}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Layouts */}
            {brandDna.layout_preferences?.length > 0 && (
              <div className="rounded-xl bg-gray-50 p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <Layout className="h-3.5 w-3.5 text-gray-500" />
                  <span className="text-[11px] font-semibold text-gray-500 uppercase">Layouts</span>
                </div>
                {brandDna.layout_preferences.map((l: string) => (
                  <p key={l} className="text-xs text-gray-700">{l.replace(/_/g, " ")}</p>
                ))}
              </div>
            )}

            {/* Mood */}
            {brandDna.mood_keywords?.length > 0 && (
              <div className="rounded-xl bg-gray-50 p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <Zap className="h-3.5 w-3.5 text-gray-500" />
                  <span className="text-[11px] font-semibold text-gray-500 uppercase">Ambiance</span>
                </div>
                <div className="flex gap-1 flex-wrap">
                  {brandDna.mood_keywords.map((m: string) => (
                    <span key={m} className="rounded-full bg-brand-100 text-brand-700 px-2 py-0.5 text-[10px] font-medium">{m}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Template grid */}
      {templateList.length > 0 && (
        <div>
          <p className="section-label mb-3">Templates de reference ({templateList.length})</p>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {templateList.map((t) => {
              const st = STATUS_CONFIG[t.analysis_status] || STATUS_CONFIG.pending;
              const StIcon = st.icon;
              return (
                <div key={t.id} className="surface overflow-hidden group">
                  {/* Image */}
                  <div className="relative aspect-[3/4] bg-gray-100">
                    <img src={t.image_url} alt={t.name} className="w-full h-full object-cover" />
                    {/* Status badge */}
                    <div className={cn("absolute top-2 left-2 inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-semibold", st.color)}>
                      <StIcon className={cn("h-3 w-3", t.analysis_status === "analyzing" && "animate-spin")} />
                      {st.label}
                    </div>
                    {/* Actions overlay */}
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                      {t.analysis_status === "completed" && (
                        <button onClick={() => setPreviewDna(t)} className="rounded-xl bg-white px-3 py-2 text-xs font-semibold text-gray-800 hover:bg-gray-100 transition-colors">
                          <Eye className="h-3.5 w-3.5 inline mr-1" /> DNA
                        </button>
                      )}
                      <button onClick={() => handleReanalyze(t.id)} className="rounded-xl bg-white/20 px-3 py-2 text-xs font-semibold text-white hover:bg-white/30 transition-colors">
                        <RefreshCw className="h-3.5 w-3.5 inline mr-1" /> Re-analyser
                      </button>
                    </div>
                  </div>
                  {/* Footer */}
                  <div className="flex items-center justify-between px-3 py-2.5">
                    <p className="text-xs font-medium text-gray-800 truncate flex-1">{t.name}</p>
                    <button onClick={() => setDeleteTarget(t)} className="rounded-lg p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Empty state */}
      {templateList.length === 0 && !uploading && (
        <div className="surface flex flex-col items-center py-16 text-center">
          <Layers className="h-12 w-12 text-gray-200" />
          <p className="mt-4 text-sm font-medium text-gray-500">Aucun template de reference</p>
          <p className="mt-1 text-xs text-gray-400 max-w-sm">
            Uploadez vos affiches existantes (Canva, Adobe, photos) et l'IA analysera votre style visuel pour le reproduire automatiquement
          </p>
        </div>
      )}

      {/* DNA Preview modal */}
      {previewDna && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setPreviewDna(null)}>
          <div className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl bg-white p-6 shadow-xl m-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-brand-500" />
                <h3 className="text-lg font-bold text-gray-900">Design DNA — {previewDna.name}</h3>
              </div>
              <button onClick={() => setPreviewDna(null)} className="rounded-lg p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100">
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Reference image */}
            <img src={previewDna.image_url} alt={previewDna.name} className="w-full max-h-64 object-contain rounded-xl bg-gray-50 mb-4" />

            {/* DNA sections */}
            <div className="space-y-3">
              {Object.entries(previewDna.design_dna).map(([section, data]) => (
                <details key={section} className="rounded-xl border border-gray-100">
                  <summary className="flex items-center gap-2 px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors">
                    <ChevronDown className="h-4 w-4 text-gray-400" />
                    <span className="text-sm font-semibold text-gray-800 capitalize">{section.replace(/_/g, " ")}</span>
                  </summary>
                  <div className="px-4 pb-3">
                    <pre className="text-xs text-gray-600 bg-gray-50 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">
                      {JSON.stringify(data, null, 2)}
                    </pre>
                  </div>
                </details>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Delete confirm */}
      <ConfirmDialog
        open={deleteTarget !== null}
        title="Supprimer ce template ?"
        message={`Le template "${deleteTarget?.name}" sera supprime. Le Design DNA de la marque sera recalcule.`}
        variant="danger"
        confirmLabel="Supprimer"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

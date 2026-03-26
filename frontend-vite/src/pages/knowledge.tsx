
import { useState, useMemo, useCallback } from "react";
import {
  Upload, Search, CheckCircle, Clock, XCircle, Loader2, Trash2,
  RefreshCw, Plus, X, Sparkles, FileText, HelpCircle, ShoppingBag,
  BookOpen, Shield, FileQuestion, ChevronDown, Layers, ClipboardPaste,
  Database, Lightbulb, BarChart3, ArrowRight,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useApi } from "@/hooks/use-api";
import { knowledge as knowledgeApi, brands as brandsApi } from "@/lib/api";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Skeleton, ListItemSkeleton } from "@/components/ui/skeleton";

// ── Status config ──

const statusMap: Record<string, { label: string; color: string; bg: string; icon: React.ElementType }> = {
  indexed: { label: "Index\u00e9", color: "text-emerald-600", bg: "bg-emerald-50 border-emerald-100", icon: CheckCircle },
  processing: { label: "En cours", color: "text-amber-600", bg: "bg-amber-50 border-amber-100", icon: Loader2 },
  pending: { label: "En attente", color: "text-gray-500", bg: "bg-gray-50 border-gray-100", icon: Clock },
  failed: { label: "Erreur", color: "text-red-600", bg: "bg-red-50 border-red-100", icon: XCircle },
};

// ── Document types with icons and descriptions ──

interface DocTypeConfig {
  label: string;
  description: string;
  icon: React.ElementType;
  iconColor: string;
  iconBg: string;
  tip: string;
  placeholder: string;
}

const docTypeConfigs: Record<string, DocTypeConfig> = {
  faq: {
    label: "FAQ",
    description: "Questions-r\u00e9ponses fr\u00e9quentes",
    icon: HelpCircle,
    iconColor: "text-blue-600",
    iconBg: "bg-blue-50",
    tip: "Format CSV : une question et une r\u00e9ponse par ligne, s\u00e9par\u00e9es par une virgule. L\u2019IA cr\u00e9era un fragment par paire Q/R pour des r\u00e9ponses pr\u00e9cises.",
    placeholder: "Question?,R\u00e9ponse\nCombien co\u00fbte le wax?,3500 FCFA le m\u00e8tre.\nLivrez-vous \u00e0 Bobo?,Oui, livraison en 48h.",
  },
  product_catalog: {
    label: "Catalogue produits",
    description: "Fiches produits, prix, r\u00e9f\u00e9rences",
    icon: ShoppingBag,
    iconColor: "text-purple-600",
    iconBg: "bg-purple-50",
    tip: "Collez votre catalogue produit (nom, description, prix). L\u2019IA indexera chaque produit s\u00e9par\u00e9ment pour les recommandations.",
    placeholder: "Wax Premium #5 \u2014 3500 FCFA/m\nTissu en coton de qualit\u00e9 sup\u00e9rieure, motif floral traditionnel.\nDisponible en 12 couleurs.\n\nBasin Rich\u00e9 \u2014 8000 FCFA/m\n...",
  },
  guide: {
    label: "Guide / tutoriel",
    description: "Proc\u00e9dures, modes d\u2019emploi",
    icon: BookOpen,
    iconColor: "text-teal-600",
    iconBg: "bg-teal-50",
    tip: "Collez le texte complet du guide. L\u2019IA d\u00e9coupera les sections automatiquement en fragments de 400-600 mots pour une recherche optimale.",
    placeholder: "Comment passer commande :\n1. Visitez notre site\n2. Choisissez votre tissu\n3. Ajoutez au panier\n...",
  },
  policy: {
    label: "Politique / conditions",
    description: "CGV, retours, garanties, confidentialit\u00e9",
    icon: Shield,
    iconColor: "text-orange-600",
    iconBg: "bg-orange-50",
    tip: "Collez vos conditions g\u00e9n\u00e9rales, politique de retour ou toute r\u00e8gle importante. L\u2019IA les citera lorsqu\u2019un client pose des questions juridiques.",
    placeholder: "Politique de retour :\n- Retour accept\u00e9 sous 7 jours\n- Le produit doit \u00eatre dans son \u00e9tat d\u2019origine\n...",
  },
  custom: {
    label: "Autre document",
    description: "Texte libre, notes, informations diverses",
    icon: FileQuestion,
    iconColor: "text-gray-600",
    iconBg: "bg-gray-50",
    tip: "Collez n\u2019importe quel texte utile. L\u2019IA le d\u00e9coupera automatiquement en fragments indexables.",
    placeholder: "Collez ici le contenu de votre document...",
  },
};

// ── CSV Preview parser ──

function parseCsvPreview(content: string): { question: string; answer: string }[] {
  if (!content.trim()) return [];
  const lines = content.split("\n").filter((l) => l.trim());
  const rows: { question: string; answer: string }[] = [];
  for (const line of lines) {
    const commaIdx = line.indexOf(",");
    if (commaIdx > 0) {
      const q = line.slice(0, commaIdx).trim();
      const a = line.slice(commaIdx + 1).trim();
      if (q && a) rows.push({ question: q, answer: a });
    }
  }
  return rows;
}

// ── Highlight query terms in text ──

function HighlightedText({ text, query }: { text: string; query: string }) {
  if (!query.trim()) return <>{text}</>;
  const terms = query.trim().split(/\s+/).filter(Boolean);
  const pattern = terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  const regex = new RegExp(`(${pattern})`, "gi");
  const parts = text.split(regex);
  return (
    <>
      {parts.map((part, i) =>
        regex.test(part) ? (
          <mark key={i} className="bg-yellow-200 text-yellow-900 rounded-sm px-0.5">{part}</mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

// ── Score bar component ──

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-400";
  return (
    <div className="flex items-center gap-2 shrink-0">
      <div className="w-20 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[11px] font-semibold tabular-nums text-gray-500">{pct}%</span>
    </div>
  );
}

// ── Chunk count visual indicator ──

function ChunkIndicator({ count }: { count: number }) {
  const dots = Math.min(count, 8);
  return (
    <div className="flex items-center gap-1" title={`${count} fragment${count !== 1 ? "s" : ""}`}>
      <Layers className="h-3 w-3 text-gray-400" />
      <div className="flex gap-0.5">
        {Array.from({ length: dots }).map((_, i) => (
          <div key={i} className="w-1.5 h-1.5 rounded-full bg-brand-400" />
        ))}
        {count > 8 && <span className="text-[10px] text-gray-400 ml-0.5">+{count - 8}</span>}
      </div>
      <span className="text-[11px] text-gray-400 ml-1">{count}</span>
    </div>
  );
}

// ── Document card skeleton ──

function DocCardSkeleton() {
  return (
    <div className="surface rounded-2xl p-5">
      <div className="flex items-start gap-4">
        <Skeleton className="h-11 w-11 rounded-xl shrink-0" />
        <div className="flex-1 space-y-2.5">
          <Skeleton className="h-4 w-3/5" />
          <Skeleton className="h-3 w-2/5" />
          <div className="flex gap-2">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-3 w-24" />
          </div>
        </div>
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// ═══ MAIN PAGE ═══
// ══════════════════════════════════════════════════════════

export default function KnowledgePage() {
  const { data: docs, loading, refetch } = useApi(() => knowledgeApi.list(), []);
  const { data: brandList } = useApi(() => brandsApi.list(), []);

  // Search state
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<any[] | null>(null);

  // Add document state
  const [showAdd, setShowAdd] = useState(false);
  const [newDoc, setNewDoc] = useState({ title: "", doc_type: "faq", raw_content: "" });
  const [creating, setCreating] = useState(false);
  const [typePickerOpen, setTypePickerOpen] = useState(false);

  // Action state
  const [actionId, setActionId] = useState<string | null>(null);

  // Delete confirmation state
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null);

  // Drag-and-drop state
  const [isDragOver, setIsDragOver] = useState(false);

  const brandId = brandList?.[0]?.id;
  const documents = docs ?? [];
  const activeDocType = docTypeConfigs[newDoc.doc_type] || docTypeConfigs.custom;

  // Live CSV preview
  const csvPreview = useMemo(() => {
    if (newDoc.doc_type !== "faq") return [];
    return parseCsvPreview(newDoc.raw_content);
  }, [newDoc.doc_type, newDoc.raw_content]);

  // ── Handlers ──

  const handleSearch = useCallback(async () => {
    if (!query.trim() || !brandId) return;
    setSearching(true);
    try {
      const res = await knowledgeApi.search({ query, brand_id: brandId, min_score: 0.01 });
      setResults(res.results);
      if (res.results.length === 0) {
        toast.info("Aucun r\u00e9sultat trouv\u00e9", { description: "Essayez avec d\u2019autres termes ou ajoutez plus de documents." });
      }
    } catch (err: any) {
      toast.error("Erreur de recherche", { description: err.message });
    } finally {
      setSearching(false);
    }
  }, [query, brandId]);

  const handleCreate = useCallback(async () => {
    if (!brandId || !newDoc.title.trim() || !newDoc.raw_content.trim()) {
      toast.warning("Champs requis", { description: "Remplissez le titre et le contenu du document." });
      return;
    }
    setCreating(true);
    try {
      await knowledgeApi.create({
        brand_id: brandId,
        title: newDoc.title,
        doc_type: newDoc.doc_type,
        raw_content: newDoc.raw_content,
        language: "fr",
      });
      toast.success("Document import\u00e9", { description: `\u00ab ${newDoc.title} \u00bb est en cours d\u2019indexation.` });
      setShowAdd(false);
      setNewDoc({ title: "", doc_type: "faq", raw_content: "" });
      refetch();
    } catch (err: any) {
      toast.error("Erreur d\u2019import", { description: err.message });
    } finally {
      setCreating(false);
    }
  }, [brandId, newDoc, refetch]);

  const handleDelete = useCallback(async (id: string) => {
    setActionId(id);
    try {
      await knowledgeApi.delete(id);
      toast.success("Document supprim\u00e9", { description: "Le document et ses fragments ont \u00e9t\u00e9 supprim\u00e9s." });
      setDeleteTarget(null);
      refetch();
    } catch (err: any) {
      toast.error("Erreur de suppression", { description: err.message });
    } finally {
      setActionId(null);
    }
  }, [refetch]);

  const handleReindex = useCallback(async (id: string) => {
    setActionId(id);
    try {
      await knowledgeApi.reindex(id);
      toast.success("R\u00e9indexation lanc\u00e9e", { description: "Le document sera r\u00e9index\u00e9 dans quelques instants." });
      refetch();
    } catch (err: any) {
      toast.error("Erreur de r\u00e9indexation", { description: err.message });
    } finally {
      setActionId(null);
    }
  }, [refetch]);

  // Drag-and-drop handlers for paste zone
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    const text = e.dataTransfer.getData("text/plain");
    if (text) {
      setNewDoc((prev) => ({
        ...prev,
        raw_content: prev.raw_content ? prev.raw_content + "\n" + text : text,
      }));
      toast.success("Texte d\u00e9pos\u00e9", { description: `${text.length} caract\u00e8res ajout\u00e9s au contenu.` });
    }
  }, []);

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    // Allow default paste behavior in the textarea but show feedback
    const text = e.clipboardData.getData("text/plain");
    if (text && text.length > 100) {
      setTimeout(() => toast.info("Contenu coll\u00e9", { description: `${text.length} caract\u00e8res ajout\u00e9s.` }), 100);
    }
  }, []);

  // ── Render ──

  return (
    <div className="space-y-8 max-w-5xl">
      {/* ═══ Header ═══ */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-100">
              <Database className="h-5 w-5 text-brand-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Base de connaissances</h1>
              <p className="text-sm text-gray-500">
                {loading
                  ? "Chargement..."
                  : `${documents.length} document${documents.length !== 1 ? "s" : ""} \u00b7 L\u2019IA utilise ces informations pour r\u00e9pondre \u00e0 vos clients`}
              </p>
            </div>
          </div>
        </div>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className={cn(
            "btn-primary",
            showAdd && "bg-gray-100 text-gray-600 hover:bg-gray-200 shadow-none"
          )}
        >
          {showAdd ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          {showAdd ? "Fermer" : "Ajouter un document"}
        </button>
      </div>

      {/* ═══ Add document panel ═══ */}
      {showAdd && (
        <div className="surface rounded-2xl overflow-hidden border border-gray-100 shadow-sm">
          {/* Panel header */}
          <div className="bg-gradient-to-r from-brand-50 to-blue-50 px-6 py-4 border-b border-gray-100">
            <h2 className="text-base font-bold text-gray-900">Nouveau document</h2>
            <p className="text-sm text-gray-500 mt-0.5">Importez du contenu pour enrichir les r\u00e9ponses de votre IA</p>
          </div>

          <div className="p-6 space-y-5">
            {/* Title */}
            <div>
              <label className="section-label mb-1.5 block">Titre du document</label>
              <input
                value={newDoc.title}
                onChange={(e) => setNewDoc({ ...newDoc, title: e.target.value })}
                className="input-base"
                placeholder="Ex : FAQ Produits, Catalogue Tissus 2026..."
              />
            </div>

            {/* Type selector with icons */}
            <div>
              <label className="section-label mb-1.5 block">Type de document</label>
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setTypePickerOpen(!typePickerOpen)}
                  className="input-base w-full flex items-center gap-3 text-left cursor-pointer hover:border-brand-300 transition-colors"
                >
                  <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg shrink-0", activeDocType.iconBg)}>
                    <activeDocType.icon className={cn("h-4 w-4", activeDocType.iconColor)} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-800">{activeDocType.label}</p>
                    <p className="text-xs text-gray-400 truncate">{activeDocType.description}</p>
                  </div>
                  <ChevronDown className={cn("h-4 w-4 text-gray-400 transition-transform", typePickerOpen && "rotate-180")} />
                </button>

                {/* Dropdown */}
                {typePickerOpen && (
                  <div className="absolute z-20 mt-1.5 w-full rounded-xl bg-white border border-gray-200 shadow-lg overflow-hidden">
                    {Object.entries(docTypeConfigs).map(([key, cfg]) => (
                      <button
                        key={key}
                        type="button"
                        onClick={() => {
                          setNewDoc({ ...newDoc, doc_type: key });
                          setTypePickerOpen(false);
                        }}
                        className={cn(
                          "w-full flex items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-gray-50",
                          key === newDoc.doc_type && "bg-brand-50/50"
                        )}
                      >
                        <div className={cn("flex h-9 w-9 items-center justify-center rounded-lg shrink-0", cfg.iconBg)}>
                          <cfg.icon className={cn("h-4.5 w-4.5", cfg.iconColor)} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-gray-800">{cfg.label}</p>
                          <p className="text-xs text-gray-400">{cfg.description}</p>
                        </div>
                        {key === newDoc.doc_type && (
                          <CheckCircle className="h-4 w-4 text-brand-500 shrink-0" />
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Inline tip for selected doc type */}
            <div className="flex gap-3 rounded-xl bg-sky-50 border border-sky-100 p-4">
              <Lightbulb className="h-4 w-4 text-sky-600 shrink-0 mt-0.5" />
              <div className="text-xs text-sky-700 leading-relaxed">
                <span className="font-semibold">Astuce \u2014 </span>
                {activeDocType.tip}
                {newDoc.doc_type === "faq" && (
                  <div className="mt-2 rounded-lg bg-sky-100/70 p-2.5 font-mono text-[11px]">
                    <code>Quel est le prix du wax?,Le wax n\u00b05 est \u00e0 3500 FCFA le m\u00e8tre.</code>
                  </div>
                )}
              </div>
            </div>

            {/* Drag-and-drop zone + textarea */}
            <div>
              <label className="section-label mb-1.5 block">Contenu du document</label>
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={cn(
                  "relative rounded-xl border-2 border-dashed transition-all duration-200",
                  isDragOver
                    ? "border-brand-400 bg-brand-50/50 shadow-[0_0_0_3px_rgba(99,102,241,0.1)]"
                    : "border-gray-200 hover:border-gray-300"
                )}
              >
                {/* Drop overlay */}
                {isDragOver && (
                  <div className="absolute inset-0 z-10 flex flex-col items-center justify-center rounded-xl bg-brand-50/80 backdrop-blur-sm">
                    <ClipboardPaste className="h-8 w-8 text-brand-500 mb-2" />
                    <p className="text-sm font-semibold text-brand-700">D\u00e9posez votre texte ici</p>
                    <p className="text-xs text-brand-500">Le contenu sera ajout\u00e9 au document</p>
                  </div>
                )}

                <textarea
                  value={newDoc.raw_content}
                  onChange={(e) => setNewDoc({ ...newDoc, raw_content: e.target.value })}
                  onPaste={handlePaste}
                  rows={10}
                  className="w-full resize-none rounded-xl border-0 bg-transparent p-4 font-mono text-xs text-gray-700 placeholder-gray-300 focus:outline-none focus:ring-0"
                  placeholder={activeDocType.placeholder}
                />

                {/* Bottom info bar */}
                <div className="flex items-center justify-between border-t border-dashed border-gray-200 px-4 py-2">
                  <div className="flex items-center gap-1.5 text-[11px] text-gray-400">
                    <ClipboardPaste className="h-3 w-3" />
                    Glissez-d\u00e9posez du texte ou collez depuis le presse-papiers
                  </div>
                  {newDoc.raw_content.length > 0 && (
                    <span className="text-[11px] text-gray-400 tabular-nums">
                      {newDoc.raw_content.length.toLocaleString("fr-FR")} caract\u00e8res
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Live CSV preview */}
            {newDoc.doc_type === "faq" && csvPreview.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <BarChart3 className="h-3.5 w-3.5 text-gray-400" />
                  <span className="text-xs font-semibold text-gray-600">
                    Aper\u00e7u CSV \u2014 {csvPreview.length} paire{csvPreview.length !== 1 ? "s" : ""} Q/R d\u00e9tect\u00e9e{csvPreview.length !== 1 ? "s" : ""}
                  </span>
                </div>
                <div className="rounded-xl border border-gray-200 overflow-hidden">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-gray-50 border-b border-gray-200">
                        <th className="text-left px-4 py-2.5 font-semibold text-gray-500 w-[40%]">Question</th>
                        <th className="text-left px-4 py-2.5 font-semibold text-gray-500">R\u00e9ponse</th>
                      </tr>
                    </thead>
                    <tbody>
                      {csvPreview.slice(0, 10).map((row, i) => (
                        <tr key={i} className="border-b border-gray-100 last:border-0">
                          <td className="px-4 py-2.5 text-gray-700 font-medium">{row.question}</td>
                          <td className="px-4 py-2.5 text-gray-600">{row.answer}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {csvPreview.length > 10 && (
                    <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 text-[11px] text-gray-400 text-center">
                      + {csvPreview.length - 10} autres lignes
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Submit */}
            <div className="flex items-center gap-3 pt-1">
              <button
                onClick={handleCreate}
                disabled={creating || !newDoc.title.trim() || !newDoc.raw_content.trim()}
                className="btn-primary"
              >
                {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                Importer et indexer
              </button>
              <button onClick={() => setShowAdd(false)} className="btn-ghost">
                Annuler
              </button>
              {newDoc.raw_content.trim() && newDoc.title.trim() && (
                <span className="text-xs text-emerald-600 flex items-center gap-1 ml-auto">
                  <CheckCircle className="h-3.5 w-3.5" /> Pr\u00eat \u00e0 importer
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ═══ AI Search ═══ */}
      <div className="surface rounded-2xl overflow-hidden">
        <div className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50">
              <Sparkles className="h-4 w-4 text-brand-500" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-gray-900">Tester la recherche IA</h2>
              <p className="text-[11px] text-gray-400">Simulez une question client pour v\u00e9rifier les r\u00e9ponses</p>
            </div>
          </div>

          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="Ex : Combien co\u00fbte le wax n\u00b05 ?"
                className="input-base pl-10"
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={!query.trim() || searching || !brandId}
              className="btn-primary"
            >
              {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Search className="h-4 w-4" /> Rechercher</>}
            </button>
          </div>

          {/* Search results */}
          {results !== null && results.length > 0 && (
            <div className="mt-5 space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-gray-500">
                  {results.length} r\u00e9sultat{results.length !== 1 ? "s" : ""} trouv\u00e9{results.length !== 1 ? "s" : ""}
                </p>
                <button
                  onClick={() => setResults(null)}
                  className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
                >
                  Effacer
                </button>
              </div>
              {results.map((r, i) => (
                <div
                  key={i}
                  className="rounded-xl bg-gradient-to-br from-brand-50/80 to-blue-50/40 border border-brand-100 p-4 transition-all hover:shadow-sm"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <FileText className="h-3.5 w-3.5 text-brand-500" />
                      <p className="text-xs font-bold text-brand-700">
                        {r.document_title}
                        {r.section_title ? <span className="font-normal text-brand-500"> \u2014 {r.section_title}</span> : ""}
                      </p>
                    </div>
                    <ScoreBar score={r.score} />
                  </div>
                  <p className="text-sm text-gray-700 leading-relaxed">
                    <HighlightedText text={r.content} query={query} />
                  </p>
                </div>
              ))}
            </div>
          )}

          {results !== null && results.length === 0 && (
            <div className="mt-5 flex flex-col items-center py-6 text-center">
              <Search className="h-8 w-8 text-gray-200 mb-2" />
              <p className="text-sm text-gray-500">Aucun r\u00e9sultat</p>
              <p className="text-xs text-gray-400 mt-0.5">Essayez avec d&apos;autres termes ou ajoutez plus de documents</p>
            </div>
          )}
        </div>
      </div>

      {/* ═══ Document list ═══ */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <p className="text-sm font-bold text-gray-900">Documents</p>
            {!loading && (
              <span className="text-[11px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full font-medium">
                {documents.length}
              </span>
            )}
          </div>
        </div>

        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <DocCardSkeleton key={i} />
            ))}
          </div>
        ) : documents.length === 0 ? (
          <div className="surface rounded-2xl flex flex-col items-center py-16 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gray-50 mb-4">
              <FileText className="h-8 w-8 text-gray-200" />
            </div>
            <p className="text-base font-semibold text-gray-700">Aucun document</p>
            <p className="text-sm text-gray-400 mt-1 max-w-xs">
              Importez votre FAQ ou catalogue produits pour que l&apos;IA puisse r\u00e9pondre \u00e0 vos clients
            </p>
            <button onClick={() => setShowAdd(true)} className="btn-primary mt-5">
              <Plus className="h-4 w-4" /> Ajouter votre premier document
            </button>
          </div>
        ) : (
          <div className="grid gap-3">
            {documents.map((doc: any) => {
              const st = statusMap[doc.status] || statusMap.pending;
              const typeConfig = docTypeConfigs[doc.doc_type] || docTypeConfigs.custom;
              const TypeIcon = typeConfig.icon;
              const StatusIcon = st.icon;

              return (
                <div
                  key={doc.id}
                  className="surface rounded-2xl p-5 transition-all hover:shadow-sm group"
                >
                  <div className="flex items-start gap-4">
                    {/* Type icon */}
                    <div className={cn("flex h-11 w-11 items-center justify-center rounded-xl shrink-0", typeConfig.iconBg)}>
                      <TypeIcon className={cn("h-5 w-5", typeConfig.iconColor)} />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-bold text-gray-800 truncate">{doc.title}</p>
                        <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium", st.bg, st.color)}>
                          <StatusIcon className={cn("h-3 w-3", doc.status === "processing" && "animate-spin")} />
                          {st.label}
                        </span>
                      </div>
                      <p className="text-xs text-gray-400 mt-1">
                        {typeConfig.label}
                        {" \u00b7 "}
                        {new Date(doc.created_at).toLocaleDateString("fr-FR", {
                          day: "numeric",
                          month: "long",
                          year: "numeric",
                        })}
                      </p>
                      {doc.chunk_count > 0 && (
                        <div className="mt-2">
                          <ChunkIndicator count={doc.chunk_count} />
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => handleReindex(doc.id)}
                        disabled={actionId === doc.id}
                        className="rounded-lg border border-gray-200 p-2 text-gray-400 hover:text-sky-600 hover:border-sky-200 hover:bg-sky-50 transition-all"
                        title="R\u00e9indexer"
                      >
                        {actionId === doc.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <RefreshCw className="h-3.5 w-3.5" />
                        )}
                      </button>
                      <button
                        onClick={() => setDeleteTarget({ id: doc.id, title: doc.title })}
                        disabled={actionId === doc.id}
                        className="rounded-lg border border-gray-200 p-2 text-gray-400 hover:text-red-500 hover:border-red-200 hover:bg-red-50 transition-all"
                        title="Supprimer"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ═══ Delete confirmation dialog ═══ */}
      <ConfirmDialog
        open={deleteTarget !== null}
        title="Supprimer ce document ?"
        message={`Le document \u00ab ${deleteTarget?.title ?? ""} \u00bb et tous ses fragments index\u00e9s seront d\u00e9finitivement supprim\u00e9s. Cette action est irr\u00e9versible.`}
        variant="danger"
        confirmLabel="Supprimer"
        cancelLabel="Annuler"
        onConfirm={async () => { if (deleteTarget) await handleDelete(deleteTarget.id); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

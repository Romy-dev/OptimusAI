import { useState } from "react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import {
  Zap, ArrowRight, ArrowLeft, Palette, BookOpen, Sparkles,
  CheckCircle, Loader2, Building2, Globe, MessageSquare,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { brands as brandsApi, knowledge as knowledgeApi, posts as postsApi } from "@/lib/api";

const STEPS = [
  { id: "brand", label: "Votre marque", icon: Palette },
  { id: "knowledge", label: "Base de connaissances", icon: BookOpen },
  { id: "generate", label: "Premier post IA", icon: Sparkles },
];

const INDUSTRIES = [
  "Mode & Textile", "Alimentation", "Commerce", "Services",
  "Technologie", "Beaute", "Education", "Sante", "Transport", "Autre",
];

interface Props {
  onComplete: () => void;
}

export function OnboardingWizard({ onComplete }: Props) {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [brandId, setBrandId] = useState<string | null>(null);
  const [generatedPostId, setGeneratedPostId] = useState<string | null>(null);

  // Step 1 — Brand
  const [brand, setBrand] = useState({
    name: "",
    description: "",
    industry: "",
    tone: "professionnel",
    language: "fr",
    target_country: "BF",
  });

  // Step 2 — FAQ
  const [faq, setFaq] = useState("");

  // Step 3 — Brief
  const [brief, setBrief] = useState("");
  const [generatedContent, setGeneratedContent] = useState("");

  const handleCreateBrand = async () => {
    if (!brand.name) { toast.error("Le nom est obligatoire"); return; }
    setLoading(true);
    try {
      const result = await brandsApi.create({
        name: brand.name,
        description: brand.description,
        industry: brand.industry,
        tone: brand.tone,
        language: brand.language,
        target_country: brand.target_country,
        colors: { primary: "#0D9488", secondary: "#0EA5E9", accent: "#F59E0B" },
        guidelines: {},
      });
      setBrandId(result.id);
      toast.success("Marque creee");
      setStep(1);
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddFAQ = async () => {
    if (!faq.trim() || !brandId) { setStep(2); return; }
    setLoading(true);
    try {
      await knowledgeApi.create({
        brand_id: brandId,
        title: "FAQ - " + brand.name,
        doc_type: "faq",
        raw_content: faq,
        language: "fr",
      });
      toast.success("FAQ indexee");
      setStep(2);
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGeneratePost = async () => {
    if (!brief.trim() || !brandId) return;
    setLoading(true);
    try {
      const post = await postsApi.generate({
        brand_id: brandId,
        brief: brief,
        channels: ["facebook"],
        language: "fr",
      });
      setGeneratedContent(post.content_text || "");
      setGeneratedPostId(post.id);
      toast.success("Post genere par l'IA");
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFinish = () => {
    localStorage.setItem("onboarding_done", "true");
    onComplete();
    navigate("/dashboard");
    toast.success("Bienvenue sur OptimusAI !");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-900 to-brand-900">
      <div className="w-full max-w-2xl mx-4">
        {/* Progress */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {STEPS.map((s, i) => (
            <div key={s.id} className="flex items-center gap-2">
              <div className={cn(
                "flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-all",
                i < step ? "bg-brand-500 text-white" :
                i === step ? "bg-white text-brand-600 ring-4 ring-brand-500/20" :
                "bg-white/10 text-white/40"
              )}>
                {i < step ? <CheckCircle className="h-4 w-4" /> : i + 1}
              </div>
              <span className={cn("text-xs font-medium hidden sm:block", i <= step ? "text-white" : "text-white/30")}>{s.label}</span>
              {i < STEPS.length - 1 && <div className={cn("w-8 h-0.5 rounded", i < step ? "bg-brand-500" : "bg-white/10")} />}
            </div>
          ))}
        </div>

        <div className="rounded-2xl bg-white p-8 shadow-2xl">
          {/* Step 1: Brand */}
          {step === 0 && (
            <div className="space-y-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
                  <Building2 className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-gray-900">Creez votre marque</h2>
                  <p className="text-xs text-gray-500">L'IA utilisera ces informations pour personnaliser tous vos contenus</p>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-xs font-semibold text-gray-700 mb-1 block">Nom de la marque *</label>
                  <input value={brand.name} onChange={(e) => setBrand(p => ({ ...p, name: e.target.value }))} className="input-base" placeholder="Wax Elegance" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-700 mb-1 block">Secteur d'activite</label>
                  <select value={brand.industry} onChange={(e) => setBrand(p => ({ ...p, industry: e.target.value }))} className="input-base">
                    <option value="">Choisir...</option>
                    {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-gray-700 mb-1 block">Description</label>
                <textarea value={brand.description} onChange={(e) => setBrand(p => ({ ...p, description: e.target.value }))} className="input-base" rows={2} placeholder="Decrivez votre activite en quelques mots..." />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-xs font-semibold text-gray-700 mb-1 block">Ton de communication</label>
                  <select value={brand.tone} onChange={(e) => setBrand(p => ({ ...p, tone: e.target.value }))} className="input-base">
                    <option value="professionnel">Professionnel</option>
                    <option value="amical">Amical</option>
                    <option value="decontracte">Decontracte</option>
                    <option value="inspirant">Inspirant</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-700 mb-1 block">Pays cible</label>
                  <div className="flex items-center gap-2">
                    <Globe className="h-4 w-4 text-gray-400" />
                    <select value={brand.target_country} onChange={(e) => setBrand(p => ({ ...p, target_country: e.target.value }))} className="input-base">
                      <option value="BF">Burkina Faso</option>
                      <option value="CI">Cote d'Ivoire</option>
                      <option value="SN">Senegal</option>
                      <option value="ML">Mali</option>
                      <option value="CM">Cameroun</option>
                      <option value="FR">France</option>
                    </select>
                  </div>
                </div>
              </div>

              <button onClick={handleCreateBrand} disabled={loading || !brand.name} className="btn-primary w-full py-3">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <><span>Continuer</span><ArrowRight className="h-4 w-4" /></>}
              </button>
            </div>
          )}

          {/* Step 2: Knowledge Base */}
          {step === 1 && (
            <div className="space-y-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-600">
                  <BookOpen className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-gray-900">Ajoutez vos FAQ</h2>
                  <p className="text-xs text-gray-500">L'IA utilisera ces reponses pour le support client automatique</p>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-gray-700 mb-1 block">Questions / Reponses (format CSV)</label>
                <textarea
                  value={faq}
                  onChange={(e) => setFaq(e.target.value)}
                  className="input-base font-mono text-xs"
                  rows={8}
                  placeholder={"Quels sont vos horaires?,Nous sommes ouverts du lundi au samedi de 8h a 18h\nLivrez-vous a domicile?,Oui nous livrons dans tout Ouagadougou\nComment commander?,Envoyez un message WhatsApp au +226 XX XX XX XX"}
                />
              </div>

              <div className="flex gap-3">
                <button onClick={() => setStep(0)} className="btn-secondary flex-1"><ArrowLeft className="h-4 w-4" /> Retour</button>
                <button onClick={handleAddFAQ} disabled={loading} className="btn-primary flex-1">
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <>{faq.trim() ? "Indexer et continuer" : "Passer"}<ArrowRight className="h-4 w-4" /></>}
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Generate first post */}
          {step === 2 && (
            <div className="space-y-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-100 text-brand-600">
                  <Sparkles className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-gray-900">Votre premier post IA</h2>
                  <p className="text-xs text-gray-500">Decrivez ce que vous voulez communiquer</p>
                </div>
              </div>

              {!generatedContent ? (
                <>
                  <div>
                    <label className="text-xs font-semibold text-gray-700 mb-1 block">Brief</label>
                    <textarea
                      value={brief}
                      onChange={(e) => setBrief(e.target.value)}
                      className="input-base"
                      rows={3}
                      placeholder="Ex: Annonce de notre nouvelle collection de tissus wax pour la saison des pluies, avec des motifs exclusifs inspires de la culture burkinabe..."
                    />
                  </div>
                  <div className="flex gap-3">
                    <button onClick={() => setStep(1)} className="btn-secondary flex-1"><ArrowLeft className="h-4 w-4" /> Retour</button>
                    <button onClick={handleGeneratePost} disabled={loading || !brief.trim()} className="btn-primary flex-1">
                      {loading ? <><Loader2 className="h-4 w-4 animate-spin" /> L'IA redige...</> : <><Zap className="h-4 w-4" /> Generer</>}
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="rounded-xl bg-gray-50 border border-gray-200 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Zap className="h-4 w-4 text-brand-500" />
                      <span className="text-xs font-bold text-brand-600">Genere par IA</span>
                    </div>
                    <p className="text-sm text-gray-800 whitespace-pre-wrap">{generatedContent}</p>
                  </div>
                  <button onClick={handleFinish} className="btn-primary w-full py-3">
                    <CheckCircle className="h-4 w-4" /> C'est parti ! Acceder au dashboard
                  </button>
                </>
              )}
            </div>
          )}
        </div>

        {/* Skip link */}
        <button onClick={handleFinish} className="mt-4 mx-auto block text-sm text-white/40 hover:text-white/60 transition-colors">
          Passer l'onboarding
        </button>
      </div>
    </div>
  );
}

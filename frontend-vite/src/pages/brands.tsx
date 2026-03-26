import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import {
  Save,
  Plus,
  Trash2,
  Palette,
  Loader2,
  Check,
  Package,
  ShieldCheck,
  MessageSquare,
  Sparkles,
  ImagePlus,
  Upload,
  ClipboardPaste,
  Eye,
  Building2,
  Megaphone,
  Hash,
  X,
  type LucideIcon,
} from "lucide-react";
import { toast } from "sonner";
import { useApi } from "@/hooks/use-api";
import { brands as brandsApi, commerce as commerceApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { TagInput } from "@/components/ui/tag-input";
import { Skeleton, FormSkeleton } from "@/components/ui/skeleton";

// ── Types ──

interface Product {
  name: string;
  price: string;
  description?: string;
}

type TabKey = "identity" | "products" | "rules" | "channels" | "examples";

// ── Tone preview examples ──

const TONE_PREVIEWS: Record<string, { label: string; example: string; emoji: string }> = {
  professional: {
    label: "Professionnel",
    example:
      "Nous vous remercions de votre confiance. Notre equipe est a votre disposition pour repondre a toutes vos questions.",
    emoji: "briefcase",
  },
  friendly: {
    label: "Amical",
    example:
      "Salut ! Ravi de vous retrouver ici. N'hesitez pas a nous ecrire, on est la pour vous aider avec le sourire.",
    emoji: "wave",
  },
  casual: {
    label: "Decontracte",
    example:
      "Hey ! Nouveau produit dispo, venez checker ca. C'est du lourd, vous allez adorer !",
    emoji: "sunglasses",
  },
  inspiring: {
    label: "Inspirant",
    example:
      "Chaque jour est une nouvelle opportunite de creer quelque chose d'extraordinaire. Ensemble, construisons l'avenir.",
    emoji: "sparkles",
  },
  formal: {
    label: "Formel",
    example:
      "Nous avons le plaisir de vous informer que nos services sont desormais disponibles. Veuillez nous contacter pour plus de details.",
    emoji: "scroll",
  },
};

const INDUSTRY_OPTIONS = [
  { value: "", label: "-- Selectionnez --" },
  { value: "textile", label: "Textile & Mode" },
  { value: "food", label: "Restauration & Alimentation" },
  { value: "commerce", label: "Commerce & Distribution" },
  { value: "services", label: "Services & Conseil" },
  { value: "tech", label: "Technologie & Digital" },
  { value: "beauty", label: "Beaute & Cosmetique" },
  { value: "education", label: "Education & Formation" },
  { value: "health", label: "Sante & Bien-etre" },
  { value: "real_estate", label: "Immobilier" },
  { value: "transport", label: "Transport & Logistique" },
  { value: "agriculture", label: "Agriculture & Elevage" },
  { value: "events", label: "Evenementiel & Spectacles" },
  { value: "construction", label: "Construction & BTP" },
  { value: "media", label: "Media & Communication" },
  { value: "finance", label: "Finance & Assurance" },
  { value: "art", label: "Art & Artisanat" },
  { value: "sport", label: "Sport & Loisirs" },
  { value: "other", label: "Autre (saisie libre)" },
];

const CHANNEL_META: Record<string, { color: string; bg: string; border: string }> = {
  facebook: { color: "text-blue-600", bg: "bg-blue-50", border: "border-blue-200" },
  instagram: { color: "text-pink-600", bg: "bg-pink-50", border: "border-pink-200" },
  whatsapp: { color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-200" },
};

// ── Section wrapper component ──

function Section({
  icon: Icon,
  title,
  subtitle,
  badge,
  children,
  className,
}: {
  icon: LucideIcon;
  title: string;
  subtitle?: string;
  badge?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("surface rounded-2xl border border-gray-100 p-6", className)}>
      <div className="flex items-start justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-50">
            <Icon className="h-4.5 w-4.5 text-brand-600" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
            {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
          </div>
        </div>
        {badge}
      </div>
      {children}
    </div>
  );
}

// ── Tab button ──

function TabButton({
  active,
  icon: Icon,
  label,
  onClick,
}: {
  active: boolean;
  icon: LucideIcon;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all",
        active
          ? "bg-brand-50 text-brand-700 shadow-sm border border-brand-200"
          : "text-gray-500 hover:text-gray-700 hover:bg-gray-50 border border-transparent",
      )}
    >
      <Icon className="h-4 w-4" />
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}

// ── Color swatch component ──

function ColorSwatch({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-4 group">
      <div className="relative">
        <div
          className="h-12 w-12 rounded-xl border-2 border-white shadow-md cursor-pointer transition-transform group-hover:scale-105"
          style={{ backgroundColor: value }}
        />
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="absolute inset-0 h-12 w-12 opacity-0 cursor-pointer"
        />
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium text-gray-700">{label}</p>
        <input
          type="text"
          value={value}
          onChange={(e) => {
            const v = e.target.value;
            if (/^#[0-9A-Fa-f]{0,6}$/.test(v)) onChange(v);
          }}
          className="mt-0.5 text-xs font-mono text-gray-400 bg-transparent border-0 p-0 focus:outline-none focus:text-gray-600 w-20"
          maxLength={7}
        />
      </div>
    </div>
  );
}

// ── Loading skeleton ──

function BrandPageSkeleton() {
  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-4 w-80" />
        </div>
        <Skeleton className="h-10 w-32 rounded-xl" />
      </div>
      <div className="flex gap-2">
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-10 w-28 rounded-xl" />
        ))}
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <div className="surface rounded-2xl p-6 space-y-4">
          <Skeleton className="h-9 w-9 rounded-xl" />
          <FormSkeleton />
        </div>
        <div className="surface rounded-2xl p-6 space-y-4">
          <Skeleton className="h-9 w-9 rounded-xl" />
          <FormSkeleton />
        </div>
      </div>
    </div>
  );
}

// ── Empty state ──

function EmptyBrandState({
  onCreate,
  saving,
}: {
  onCreate: () => void;
  saving: boolean;
}) {
  return (
    <div className="max-w-md mx-auto py-24 text-center">
      <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-50 to-brand-100 mb-6">
        <Building2 className="h-10 w-10 text-brand-500" />
      </div>
      <h2 className="text-xl font-bold text-gray-900">Configurez votre marque</h2>
      <p className="mt-2 text-sm text-gray-500 max-w-xs mx-auto">
        Creez votre profil de marque pour que l&apos;IA communique avec la voix de votre entreprise.
      </p>
      <button
        onClick={onCreate}
        disabled={saving}
        className="btn-primary mt-6 px-6 py-2.5 text-sm"
      >
        {saving ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <>
            <Plus className="h-4 w-4" /> Creer ma marque
          </>
        )}
      </button>
    </div>
  );
}

// ══════════════════════════════════════
// ── Main page component ──
// ══════════════════════════════════════

export default function BrandsPage() {
  const { data: brandList, loading, refetch } = useApi(() => brandsApi.list(), []);
  const [brandId, setBrandId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<TabKey>("identity");

  // Identity
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [industry, setIndustry] = useState("");
  const [tone, setTone] = useState("professional");
  const [colors, setColors] = useState({
    primary: "#14B8A6",
    secondary: "#1F2937",
    accent: "#0EA5E9",
  });

  // Logo
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const logoInputRef = useRef<HTMLInputElement>(null);

  // Products
  const [products, setProducts] = useState<Product[]>([]);
  const [newProduct, setNewProduct] = useState({ name: "", price: "" });
  const [bulkInput, setBulkInput] = useState("");
  const [showBulkAdd, setShowBulkAdd] = useState(false);

  // Rules
  const [greetingStyle, setGreetingStyle] = useState("");
  const [closingStyle, setClosingStyle] = useState("");
  const [bannedWords, setBannedWords] = useState<string[]>([]);
  const [bannedTopics, setBannedTopics] = useState<string[]>([]);

  // Examples
  const [examplePosts, setExamplePosts] = useState<{ channel: string; content: string }[]>([]);
  const [newExample, setNewExample] = useState({ channel: "facebook", content: "" });

  // Channel tones
  const [channelTones, setChannelTones] = useState<Record<string, string>>({});

  // ── Load brand data ──

  const loadBrandProfile = useCallback(async (id: string) => {
    try {
      const profile = await brandsApi.getProfile(id);
      if (profile) {
        setProducts((profile.products || []).map((p: any) => ({ name: p.name, price: p.price || "", description: p.description })));
        setGreetingStyle(profile.greeting_style || "");
        setClosingStyle(profile.closing_style || "");
        setBannedWords(profile.banned_words || []);
        setBannedTopics(profile.banned_topics || []);
        setExamplePosts(profile.example_posts || []);
        setChannelTones(profile.tone_by_channel || {});
      }
    } catch {
      // Profile may not exist yet — fall back to guidelines
      console.log("No brand profile found, using guidelines fallback");
    }
  }, []);

  useEffect(() => {
    if (brandList && brandList.length > 0 && !brandId) {
      const b = brandList[0];
      setBrandId(b.id);
      setName(b.name || "");
      setDescription(b.description || "");
      setIndustry(b.industry || "");
      setTone(b.tone || "professional");
      setLogoUrl(b.logo_url || null);
      setColors(
        b.colors && Object.keys(b.colors).length > 0
          ? (b.colors as typeof colors)
          : { primary: "#14B8A6", secondary: "#1F2937", accent: "#0EA5E9" },
      );

      // Load profile data from dedicated endpoint
      loadBrandProfile(b.id).then(() => {
        // If profile load failed, the catch block already logged it.
        // Fall back to guidelines only if state is still empty after profile load attempt.
      }).catch(() => {
        // Fallback: use guidelines from brand object
        const g = b.guidelines || {};
        setProducts((prev) => prev.length > 0 ? prev : (g.products || []));
        setGreetingStyle((prev) => prev || g.greeting_style || "");
        setClosingStyle((prev) => prev || g.closing_style || "");
        setBannedWords((prev) => prev.length > 0 ? prev : (g.banned_words || []));
        setBannedTopics((prev) => prev.length > 0 ? prev : (g.banned_topics || []));
        setExamplePosts((prev) => prev.length > 0 ? prev : (g.example_posts || []));
        setChannelTones((prev) => Object.keys(prev).length > 0 ? prev : (g.channel_tones || {}));
      });
    }
  }, [brandList, loadBrandProfile]);

  // ── Handlers ──

  const handleSave = async () => {
    if (!brandId) return;
    setSaving(true);
    try {
      // 1. Save brand basic info
      await brandsApi.update(brandId, {
        name,
        description,
        industry,
        tone,
        colors,
        logo_url: logoUrl || undefined,
      } as any);

      // 2. Save profile data (greeting, closing, banned words, products, examples, channel tones)
      await brandsApi.updateProfile(brandId, {
        greeting_style: greetingStyle,
        closing_style: closingStyle,
        banned_words: bannedWords,
        banned_topics: bannedTopics,
        products: products.map((p) => ({
          name: p.name,
          price: p.price || undefined,
          description: p.description || undefined,
        })),
        example_posts: examplePosts.map((ex) => ({
          channel: ex.channel,
          content: ex.content,
          approved: true,
        })),
        tone_by_channel: channelTones,
        default_tone: tone,
      });

      // 3. Sync products to commerce API (best-effort, don't block save on failure)
      try {
        // Get existing commerce products for this brand
        const existingProducts = await commerceApi.listProducts(brandId);
        const existingNames = new Set(existingProducts.map((p) => p.name.toLowerCase()));
        const currentNames = new Set(products.map((p) => p.name.toLowerCase()));

        // Create new products that don't exist yet
        for (const p of products) {
          if (!existingNames.has(p.name.toLowerCase())) {
            const priceNum = parseFloat(p.price.replace(/[^\d.]/g, ""));
            await commerceApi.createProduct({
              brand_id: brandId,
              name: p.name,
              description: p.description || undefined,
              price: isNaN(priceNum) || priceNum <= 0 ? 1 : priceNum,
              currency: "XOF",
            });
          }
        }

        // Delete products that were removed from the inline editor
        for (const existing of existingProducts) {
          if (!currentNames.has(existing.name.toLowerCase())) {
            await commerceApi.deleteProduct(existing.id);
          }
        }
      } catch (commerceErr) {
        // Commerce sync is best-effort
        console.warn("Commerce product sync failed:", commerceErr);
      }

      toast.success("Marque enregistree", {
        description: "Les modifications ont ete sauvegardees avec succes.",
      });
    } catch (err: any) {
      toast.error("Erreur de sauvegarde", {
        description: err.message || "Une erreur est survenue.",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleCreate = async () => {
    setSaving(true);
    try {
      const b = await brandsApi.create({
        name: "Nouvelle marque",
        tone: "professional",
        language: "fr",
        target_country: "BF",
      });
      setBrandId(b.id);
      setName(b.name);
      refetch();
      toast.success("Marque creee", {
        description: "Commencez a configurer votre profil de marque.",
      });
    } catch (err: any) {
      toast.error("Erreur de creation", {
        description: err.message || "Impossible de creer la marque.",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleLogoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowed = ["image/png", "image/jpeg", "image/jpg", "image/svg+xml", "image/webp"];
    if (!allowed.includes(file.type)) {
      toast.error("Format non supporte", {
        description: "Utilisez PNG, JPG, SVG ou WebP.",
      });
      return;
    }

    // Validate file size (2 MB max)
    if (file.size > 2 * 1024 * 1024) {
      toast.error("Fichier trop volumineux", {
        description: "La taille maximale est de 2 Mo.",
      });
      return;
    }

    // Convert to base64 data URL
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      setLogoUrl(dataUrl);
      toast.success("Logo charge", {
        description: "N'oubliez pas d'enregistrer pour sauvegarder.",
      });
    };
    reader.onerror = () => {
      toast.error("Erreur de lecture du fichier");
    };
    reader.readAsDataURL(file);

    // Reset input so the same file can be selected again
    e.target.value = "";
  };

  const addProduct = () => {
    if (!newProduct.name.trim()) return;
    setProducts([...products, { ...newProduct, name: newProduct.name.trim(), price: newProduct.price.trim() }]);
    setNewProduct({ name: "", price: "" });
    toast.success("Produit ajoute");
  };

  const handleBulkAdd = () => {
    const lines = bulkInput
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    if (lines.length === 0) {
      toast.error("Aucune ligne valide detectee");
      return;
    }
    const newProducts: Product[] = [];
    const errors: string[] = [];
    lines.forEach((line, idx) => {
      const dashIdx = line.lastIndexOf(" - ");
      if (dashIdx > 0) {
        const pName = line.slice(0, dashIdx).trim();
        const pPrice = line.slice(dashIdx + 3).trim();
        if (pName) {
          newProducts.push({ name: pName, price: pPrice });
        } else {
          errors.push(`Ligne ${idx + 1}: nom vide`);
        }
      } else {
        // Treat full line as product name with no price
        newProducts.push({ name: line, price: "" });
      }
    });
    if (newProducts.length > 0) {
      setProducts([...products, ...newProducts]);
      setBulkInput("");
      setShowBulkAdd(false);
      toast.success(`${newProducts.length} produit${newProducts.length > 1 ? "s" : ""} ajoute${newProducts.length > 1 ? "s" : ""}`, {
        description: errors.length > 0 ? `${errors.length} ligne(s) ignoree(s)` : undefined,
      });
    }
  };

  const addExample = () => {
    if (!newExample.content.trim()) return;
    setExamplePosts([...examplePosts, { ...newExample, content: newExample.content.trim() }]);
    setNewExample({ channel: "facebook", content: "" });
    toast.success("Exemple ajoute");
  };

  // ── Derived ──

  const colorPreviewGradient = useMemo(
    () => `linear-gradient(135deg, ${colors.primary} 0%, ${colors.secondary} 50%, ${colors.accent} 100%)`,
    [colors],
  );

  const TABS: { key: TabKey; icon: LucideIcon; label: string }[] = [
    { key: "identity", icon: Building2, label: "Identite" },
    { key: "products", icon: Package, label: "Produits" },
    { key: "rules", icon: ShieldCheck, label: "Regles" },
    { key: "channels", icon: MessageSquare, label: "Canaux" },
    { key: "examples", icon: Sparkles, label: "Exemples" },
  ];

  // ── Render states ──

  if (loading) return <BrandPageSkeleton />;

  if (!brandId && (!brandList || brandList.length === 0)) {
    return <EmptyBrandState onCreate={handleCreate} saving={saving} />;
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Configuration de la marque</h1>
          <p className="mt-1 text-sm text-gray-500">
            L&apos;IA utilisera ce profil pour communiquer avec la voix de votre entreprise
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className={cn(
            "btn-primary flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-xl transition-all",
            saving && "opacity-75 cursor-not-allowed",
          )}
        >
          {saving ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Enregistrement...
            </>
          ) : (
            <>
              <Save className="h-4 w-4" />
              Enregistrer
            </>
          )}
        </button>
      </div>

      {/* ── Brand color preview bar ── */}
      <div className="rounded-xl overflow-hidden h-2" style={{ background: colorPreviewGradient }} />

      {/* ── Tab navigation ── */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
        {TABS.map((tab) => (
          <TabButton
            key={tab.key}
            active={activeTab === tab.key}
            icon={tab.icon}
            label={tab.label}
            onClick={() => setActiveTab(tab.key)}
          />
        ))}
      </div>

      {/* ══════════════════════════════════ */}
      {/* ── TAB: Identity ── */}
      {/* ══════════════════════════════════ */}

      {activeTab === "identity" && (
        <div className="grid gap-5 lg:grid-cols-2">
          {/* Brand info */}
          <Section icon={Building2} title="Informations generales" subtitle="Identite de votre entreprise">
            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-500">Nom de la marque</label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="input-base"
                  placeholder="Ex: AfrikaShop"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-500">Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  className="input-base resize-none"
                  placeholder="Decrivez votre entreprise en quelques mots..."
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-500">Secteur d&apos;activite</label>
                <select
                  value={INDUSTRY_OPTIONS.some(o => o.value === industry) ? industry : "other"}
                  onChange={(e) => {
                    if (e.target.value === "other") {
                      setIndustry("");
                    } else {
                      setIndustry(e.target.value);
                    }
                  }}
                  className="input-base"
                >
                  {INDUSTRY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                {(!INDUSTRY_OPTIONS.some(o => o.value === industry) || industry === "") && (
                  <input
                    type="text"
                    value={industry === "other" ? "" : industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    placeholder="Ex: Pharmacie, Tourisme, ONG..."
                    className="input-base mt-2"
                  />
                )}
              </div>
            </div>
          </Section>

          {/* Logo upload */}
          <Section icon={ImagePlus} title="Logo de la marque" subtitle="Utilisee dans les publications et le support">
            {/* Hidden file input */}
            <input
              ref={logoInputRef}
              type="file"
              accept="image/png,image/jpeg,image/jpg,image/svg+xml,image/webp"
              onChange={handleLogoSelect}
              className="hidden"
            />

            {logoUrl ? (
              /* Logo preview */
              <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-brand-200 bg-brand-50/30 p-6 relative group">
                <button
                  onClick={() => setLogoUrl(null)}
                  className="absolute top-3 right-3 flex h-7 w-7 items-center justify-center rounded-full bg-white border border-gray-200 text-gray-400 opacity-0 group-hover:opacity-100 hover:text-red-500 hover:border-red-200 transition-all shadow-sm"
                  title="Supprimer le logo"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
                <img
                  src={logoUrl}
                  alt="Logo de la marque"
                  className="h-28 w-28 object-contain rounded-xl"
                />
                <button
                  onClick={() => logoInputRef.current?.click()}
                  className="mt-4 text-xs font-medium text-brand-600 hover:text-brand-700 transition-colors"
                >
                  Changer le logo
                </button>
              </div>
            ) : (
              /* Upload drop zone */
              <div
                onClick={() => logoInputRef.current?.click()}
                className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-gray-200 bg-gray-50/50 p-8 transition-colors hover:border-brand-300 hover:bg-brand-50/30 cursor-pointer"
              >
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white shadow-sm border border-gray-100">
                  <Upload className="h-7 w-7 text-gray-300" />
                </div>
                <p className="mt-4 text-sm font-medium text-gray-600">
                  Deposez votre logo ici
                </p>
                <p className="mt-1 text-xs text-gray-400">PNG, SVG ou JPG (max 2 Mo)</p>
                <span className="mt-4 text-xs font-medium text-brand-600 hover:text-brand-700 transition-colors">
                  Parcourir les fichiers
                </span>
              </div>
            )}
          </Section>

          {/* Colors */}
          <Section icon={Palette} title="Palette de couleurs" subtitle="Couleurs utilisees dans vos visuels">
            <div className="space-y-4">
              <ColorSwatch
                label="Couleur principale"
                value={colors.primary}
                onChange={(v) => setColors({ ...colors, primary: v })}
              />
              <ColorSwatch
                label="Couleur secondaire"
                value={colors.secondary}
                onChange={(v) => setColors({ ...colors, secondary: v })}
              />
              <ColorSwatch
                label="Couleur d'accent"
                value={colors.accent}
                onChange={(v) => setColors({ ...colors, accent: v })}
              />

              {/* Live preview */}
              <div className="mt-5 pt-5 border-t border-gray-100">
                <p className="text-xs font-medium text-gray-500 mb-3">Apercu</p>
                <div className="flex items-center gap-2">
                  {Object.entries(colors).map(([key, value]) => (
                    <div
                      key={key}
                      className="h-14 flex-1 rounded-xl shadow-inner transition-colors duration-200"
                      style={{ backgroundColor: value }}
                    />
                  ))}
                </div>
                <div className="mt-3 flex items-center gap-2">
                  <div
                    className="flex-1 h-8 rounded-lg text-center text-xs font-semibold text-white flex items-center justify-center"
                    style={{ backgroundColor: colors.primary }}
                  >
                    Bouton
                  </div>
                  <div
                    className="flex-1 h-8 rounded-lg text-center text-xs font-semibold text-white flex items-center justify-center"
                    style={{ backgroundColor: colors.secondary }}
                  >
                    En-tete
                  </div>
                  <div
                    className="flex-1 h-8 rounded-lg text-center text-xs font-semibold text-white flex items-center justify-center"
                    style={{ backgroundColor: colors.accent }}
                  >
                    Lien
                  </div>
                </div>
              </div>
            </div>
          </Section>

          {/* Tone */}
          <Section icon={Megaphone} title="Ton de voix" subtitle="Comment votre marque s'exprime">
            <div className="space-y-3">
              {Object.entries(TONE_PREVIEWS).map(([key, info]) => (
                <button
                  key={key}
                  onClick={() => setTone(key)}
                  className={cn(
                    "w-full text-left rounded-xl border-2 p-4 transition-all",
                    tone === key
                      ? "border-brand-400 bg-brand-50/50 shadow-sm"
                      : "border-gray-100 bg-white hover:border-gray-200 hover:bg-gray-50",
                  )}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-gray-800">{info.label}</span>
                    {tone === key && (
                      <div className="flex h-5 w-5 items-center justify-center rounded-full bg-brand-500">
                        <Check className="h-3 w-3 text-white" />
                      </div>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 leading-relaxed italic">
                    &ldquo;{info.example}&rdquo;
                  </p>
                </button>
              ))}
            </div>
          </Section>
        </div>
      )}

      {/* ══════════════════════════════════ */}
      {/* ── TAB: Products ── */}
      {/* ══════════════════════════════════ */}

      {activeTab === "products" && (
        <Section
          icon={Package}
          title="Produits & Services"
          subtitle="L'IA mentionnera ces produits dans ses reponses"
          badge={
            <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">
              {products.length} produit{products.length !== 1 ? "s" : ""}
            </span>
          }
        >
          {/* Product list */}
          {products.length > 0 && (
            <div className="space-y-2 mb-5">
              {products.map((p, i) => (
                <div
                  key={i}
                  className="group flex items-center justify-between rounded-xl bg-gray-50 border border-gray-100 px-4 py-3 hover:border-gray-200 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white border border-gray-100 text-xs font-bold text-gray-400">
                      {i + 1}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-800">{p.name}</p>
                      {p.price && (
                        <p className="text-xs text-gray-400 font-mono">{p.price}</p>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      setProducts(products.filter((_, j) => j !== i));
                      toast("Produit supprime", { icon: <Trash2 className="h-4 w-4 text-red-500" /> });
                    }}
                    className="text-gray-300 opacity-0 group-hover:opacity-100 hover:text-red-500 transition-all"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {products.length === 0 && (
            <div className="flex flex-col items-center justify-center py-10 mb-5 rounded-xl bg-gray-50/50 border border-dashed border-gray-200">
              <Package className="h-8 w-8 text-gray-200 mb-3" />
              <p className="text-sm text-gray-400">Aucun produit ajoute</p>
              <p className="text-xs text-gray-300 mt-1">
                Ajoutez vos produits un par un ou en masse
              </p>
            </div>
          )}

          {/* Add single product */}
          <div className="space-y-3">
            <p className="text-xs font-medium text-gray-500">Ajouter un produit</p>
            <div className="flex gap-2">
              <input
                value={newProduct.name}
                onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
                onKeyDown={(e) => e.key === "Enter" && addProduct()}
                placeholder="Nom du produit"
                className="input-base flex-1"
              />
              <input
                value={newProduct.price}
                onChange={(e) => setNewProduct({ ...newProduct, price: e.target.value })}
                onKeyDown={(e) => e.key === "Enter" && addProduct()}
                placeholder="Prix (ex: 5 000 FCFA)"
                className="input-base w-44"
              />
              <button
                onClick={addProduct}
                disabled={!newProduct.name.trim()}
                className="btn-primary py-2 px-4 rounded-xl"
              >
                <Plus className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Bulk add */}
          <div className="mt-5 pt-5 border-t border-gray-100">
            <button
              onClick={() => setShowBulkAdd(!showBulkAdd)}
              className="flex items-center gap-2 text-xs font-medium text-brand-600 hover:text-brand-700 transition-colors"
            >
              <ClipboardPaste className="h-3.5 w-3.5" />
              {showBulkAdd ? "Masquer l'ajout en masse" : "Ajout en masse (copier-coller)"}
            </button>

            {showBulkAdd && (
              <div className="mt-3 space-y-3">
                <div className="rounded-xl bg-amber-50 border border-amber-100 px-4 py-3">
                  <p className="text-xs text-amber-700">
                    <strong>Format :</strong> un produit par ligne, avec le format{" "}
                    <code className="rounded bg-amber-100 px-1.5 py-0.5 font-mono text-[11px]">
                      Nom du produit - Prix
                    </code>
                  </p>
                  <p className="text-xs text-amber-600 mt-1">
                    Exemple :<br />
                    Tee-shirt Wax - 15 000 FCFA<br />
                    Robe Ankara - 25 000 FCFA<br />
                    Sac en cuir - 35 000 FCFA
                  </p>
                </div>
                <textarea
                  value={bulkInput}
                  onChange={(e) => setBulkInput(e.target.value)}
                  rows={5}
                  className="input-base resize-none font-mono text-xs"
                  placeholder={"Tee-shirt Wax - 15 000 FCFA\nRobe Ankara - 25 000 FCFA\nSac en cuir - 35 000 FCFA"}
                />
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleBulkAdd}
                    disabled={!bulkInput.trim()}
                    className="btn-primary py-2 px-4 text-xs rounded-xl"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Importer {bulkInput.split("\n").filter((l) => l.trim()).length} ligne
                    {bulkInput.split("\n").filter((l) => l.trim()).length !== 1 ? "s" : ""}
                  </button>
                  <button
                    onClick={() => {
                      setBulkInput("");
                      setShowBulkAdd(false);
                    }}
                    className="btn-ghost text-xs"
                  >
                    Annuler
                  </button>
                </div>
              </div>
            )}
          </div>
        </Section>
      )}

      {/* ══════════════════════════════════ */}
      {/* ── TAB: Rules ── */}
      {/* ══════════════════════════════════ */}

      {activeTab === "rules" && (
        <div className="grid gap-5 lg:grid-cols-2">
          {/* Communication style */}
          <Section icon={MessageSquare} title="Style de communication" subtitle="Comment l'IA salue et termine les conversations">
            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-500">
                  Style d&apos;accueil
                </label>
                <textarea
                  value={greetingStyle}
                  onChange={(e) => setGreetingStyle(e.target.value)}
                  className="input-base resize-none"
                  rows={2}
                  placeholder="Ex: Toujours commencer par Bonjour + nom du client"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-500">
                  Style de cloture
                </label>
                <textarea
                  value={closingStyle}
                  onChange={(e) => setClosingStyle(e.target.value)}
                  className="input-base resize-none"
                  rows={2}
                  placeholder="Ex: Merci de votre confiance ! A tres bientot."
                />
              </div>

              {/* Preview of greeting + closing */}
              {(greetingStyle || closingStyle) && (
                <div className="rounded-xl bg-gray-50 border border-gray-100 p-4">
                  <div className="flex items-center gap-1.5 mb-2">
                    <Eye className="h-3.5 w-3.5 text-gray-400" />
                    <span className="text-[10px] font-semibold uppercase text-gray-400 tracking-wide">Apercu conversation</span>
                  </div>
                  <div className="space-y-2 text-xs text-gray-600">
                    {greetingStyle && (
                      <div className="rounded-lg bg-white border border-gray-100 px-3 py-2">
                        <span className="text-brand-600 font-medium">IA:</span>{" "}
                        {greetingStyle}
                      </div>
                    )}
                    <div className="rounded-lg bg-gray-100 px-3 py-2 text-gray-400 italic">
                      ... conversation ...
                    </div>
                    {closingStyle && (
                      <div className="rounded-lg bg-white border border-gray-100 px-3 py-2">
                        <span className="text-brand-600 font-medium">IA:</span>{" "}
                        {closingStyle}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </Section>

          {/* Banned words & topics */}
          <Section icon={ShieldCheck} title="Garde-fous" subtitle="Protegez la reputation de votre marque">
            <div className="space-y-5">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-500">
                  Mots interdits
                </label>
                <p className="text-[11px] text-gray-400 mb-2">
                  L&apos;IA n&apos;utilisera jamais ces mots dans ses messages
                </p>
                <TagInput
                  tags={bannedWords}
                  onChange={setBannedWords}
                  placeholder="Tapez un mot puis Entree..."
                  className="bg-red-50/30 border-red-100 focus-within:border-red-300 focus-within:ring-red-500/10"
                />
              </div>

              <div className="pt-4 border-t border-gray-100">
                <label className="mb-1.5 block text-xs font-medium text-gray-500">
                  Sujets sensibles
                </label>
                <p className="text-[11px] text-gray-400 mb-2">
                  Escalade automatique vers un humain si ces sujets sont detectes
                </p>
                <TagInput
                  tags={bannedTopics}
                  onChange={setBannedTopics}
                  placeholder="Ex: remboursement, reclamation..."
                  className="bg-amber-50/30 border-amber-100 focus-within:border-amber-300 focus-within:ring-amber-500/10"
                />
              </div>
            </div>
          </Section>
        </div>
      )}

      {/* ══════════════════════════════════ */}
      {/* ── TAB: Channels ── */}
      {/* ══════════════════════════════════ */}

      {activeTab === "channels" && (
        <Section
          icon={MessageSquare}
          title="Ton par canal"
          subtitle="Adaptez la voix de votre marque selon chaque plateforme"
        >
          <div className="space-y-4">
            <div className="rounded-xl bg-gray-50 border border-gray-100 px-4 py-3 mb-2">
              <p className="text-xs text-gray-500">
                <strong>Ton par defaut :</strong>{" "}
                <span className="text-brand-600 font-medium">{TONE_PREVIEWS[tone]?.label || tone}</span>
                — utilise si aucun ton specifique n&apos;est configure pour un canal.
              </p>
            </div>

            {["facebook", "instagram", "whatsapp"].map((ch) => {
              const meta = CHANNEL_META[ch];
              const selectedTone = channelTones[ch] || "";
              const effectiveTone = selectedTone || tone;
              const tonePreview = TONE_PREVIEWS[effectiveTone];

              return (
                <div
                  key={ch}
                  className={cn(
                    "rounded-xl border p-4 transition-colors",
                    selectedTone ? meta.border : "border-gray-100",
                    selectedTone ? meta.bg : "bg-white",
                  )}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Hash className={cn("h-4 w-4", meta.color)} />
                      <span className={cn("text-sm font-semibold capitalize", meta.color)}>
                        {ch}
                      </span>
                    </div>
                    {selectedTone && (
                      <button
                        onClick={() => {
                          const newTones = { ...channelTones };
                          delete newTones[ch];
                          setChannelTones(newTones);
                        }}
                        className="text-[10px] text-gray-400 hover:text-gray-600 transition-colors"
                      >
                        Reinitialiser
                      </button>
                    )}
                  </div>
                  <select
                    value={selectedTone}
                    onChange={(e) =>
                      setChannelTones({ ...channelTones, [ch]: e.target.value })
                    }
                    className="input-base mb-3"
                  >
                    <option value="">Par defaut ({TONE_PREVIEWS[tone]?.label || tone})</option>
                    {Object.entries(TONE_PREVIEWS).map(([key, info]) => (
                      <option key={key} value={key}>
                        {info.label}
                      </option>
                    ))}
                  </select>

                  {/* Tone preview for this channel */}
                  {tonePreview && (
                    <div className="rounded-lg bg-white/60 border border-gray-100 px-3 py-2.5">
                      <div className="flex items-center gap-1.5 mb-1.5">
                        <Eye className="h-3 w-3 text-gray-400" />
                        <span className="text-[10px] font-semibold uppercase text-gray-400 tracking-wide">
                          Apercu {ch}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 italic leading-relaxed">
                        &ldquo;{tonePreview.example}&rdquo;
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Section>
      )}

      {/* ══════════════════════════════════ */}
      {/* ── TAB: Examples ── */}
      {/* ══════════════════════════════════ */}

      {activeTab === "examples" && (
        <Section
          icon={Sparkles}
          title="Exemples de posts approuves"
          subtitle="L'IA s'en inspire pour garder la coherence de votre communication"
          badge={
            <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">
              {examplePosts.length} exemple{examplePosts.length !== 1 ? "s" : ""}
            </span>
          }
        >
          {/* Existing examples */}
          {examplePosts.length > 0 && (
            <div className="space-y-3 mb-5">
              {examplePosts.map((ex, i) => {
                const meta = CHANNEL_META[ex.channel] || CHANNEL_META.facebook;
                return (
                  <div
                    key={i}
                    className="group rounded-xl border border-gray-100 bg-gray-50 p-4 hover:border-gray-200 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                            meta.bg,
                            meta.color,
                          )}
                        >
                          {ex.channel}
                        </span>
                      </div>
                      <button
                        onClick={() => {
                          setExamplePosts(examplePosts.filter((_, j) => j !== i));
                          toast("Exemple supprime", { icon: <Trash2 className="h-4 w-4 text-red-500" /> });
                        }}
                        className="text-gray-300 opacity-0 group-hover:opacity-100 hover:text-red-500 transition-all"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                    <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
                      {ex.content}
                    </p>
                  </div>
                );
              })}
            </div>
          )}

          {examplePosts.length === 0 && (
            <div className="flex flex-col items-center justify-center py-10 mb-5 rounded-xl bg-gray-50/50 border border-dashed border-gray-200">
              <Sparkles className="h-8 w-8 text-gray-200 mb-3" />
              <p className="text-sm text-gray-400">Aucun exemple de post</p>
              <p className="text-xs text-gray-300 mt-1">
                Ajoutez vos meilleurs posts pour guider l&apos;IA
              </p>
            </div>
          )}

          {/* Add new example */}
          <div className="space-y-3 pt-1">
            <p className="text-xs font-medium text-gray-500">Ajouter un exemple</p>
            <div className="flex gap-2 items-start">
              <select
                value={newExample.channel}
                onChange={(e) => setNewExample({ ...newExample, channel: e.target.value })}
                className="input-base w-36 shrink-0"
              >
                <option value="facebook">Facebook</option>
                <option value="instagram">Instagram</option>
                <option value="whatsapp">WhatsApp</option>
              </select>
              <textarea
                value={newExample.content}
                onChange={(e) => setNewExample({ ...newExample, content: e.target.value })}
                placeholder="Collez un de vos meilleurs posts..."
                rows={3}
                className="input-base flex-1 resize-none"
              />
            </div>
            <button
              onClick={addExample}
              disabled={!newExample.content.trim()}
              className={cn(
                "btn-primary py-2 px-4 text-xs rounded-xl flex items-center gap-1.5",
                !newExample.content.trim() && "opacity-50 cursor-not-allowed",
              )}
            >
              <Plus className="h-3.5 w-3.5" />
              Ajouter l&apos;exemple
            </button>
          </div>
        </Section>
      )}
    </div>
  );
}

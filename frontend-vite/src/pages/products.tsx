import { useState, useMemo, useCallback } from "react";
import {
  Package, Search, Plus, Edit3, Trash2, ShoppingCart, BarChart3,
  Tag, Check, X, DollarSign, TrendingUp, Loader2, Upload, ImageIcon,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useApi } from "@/hooks/use-api";
import {
  commerce as commerceApi,
  CommerceProduct, CommerceOrder, CommerceStats,
} from "@/lib/api";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";

// ── Constants ──

const CATEGORIES = ["Vetements", "Alimentation", "Cosmetique", "Electronique", "Services", "Autre"];

const ORDER_STATUSES: Record<string, { label: string; color: string; bg: string }> = {
  pending:   { label: "En attente",  color: "text-amber-700",   bg: "bg-amber-50 border-amber-200" },
  confirmed: { label: "Confirme",    color: "text-blue-700",    bg: "bg-blue-50 border-blue-200" },
  paid:      { label: "Paye",        color: "text-emerald-700", bg: "bg-emerald-50 border-emerald-200" },
  shipped:   { label: "Expedie",     color: "text-purple-700",  bg: "bg-purple-50 border-purple-200" },
  delivered: { label: "Livre",       color: "text-teal-700",    bg: "bg-teal-50 border-teal-200" },
  cancelled: { label: "Annule",      color: "text-red-700",     bg: "bg-red-50 border-red-200" },
};

type Tab = "products" | "orders" | "stats";

// ── Helpers ──

function formatFCFA(amount: number): string {
  return amount.toLocaleString("fr-FR").replace(/,/g, " ") + " FCFA";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR", {
    day: "2-digit", month: "short", year: "numeric",
  });
}

// ── Product Card Skeleton ──

function ProductCardSkeleton() {
  return (
    <div className="surface rounded-2xl overflow-hidden">
      <Skeleton className="h-40 w-full" />
      <div className="p-4 space-y-2.5">
        <Skeleton className="h-4 w-3/5" />
        <Skeleton className="h-3 w-2/5" />
        <div className="flex gap-2">
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-12 rounded-full" />
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// ═══ PRODUCT MODAL ═══
// ══════════════════════════════════════════════════════════

interface ProductForm {
  name: string;
  description: string;
  price: string;
  category: string;
  sku: string;
  in_stock: boolean;
  image_url: string;
}

const emptyForm: ProductForm = {
  name: "", description: "", price: "", category: "",
  sku: "", in_stock: true, image_url: "",
};

function ProductModal({
  open, onClose, onSave, initial, saving,
}: {
  open: boolean;
  onClose: () => void;
  onSave: (form: ProductForm) => void;
  initial: ProductForm;
  saving: boolean;
}) {
  const [form, setForm] = useState<ProductForm>(initial);
  const [showCategorySuggestions, setShowCategorySuggestions] = useState(false);
  const [imagePreview, setImagePreview] = useState<string | null>(initial.image_url || null);

  // Reset form when initial changes (opening with different product)
  const resetKey = initial.name + initial.price;
  useState(() => {
    setForm(initial);
    setImagePreview(initial.image_url || null);
  });

  if (!open) return null;

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      toast.error("Image trop volumineuse (max 5 Mo)");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result as string;
      setImagePreview(base64);
      setForm((f) => ({ ...f, image_url: base64 }));
    };
    reader.readAsDataURL(file);
  };

  const valid = form.name.trim() && form.price && Number(form.price) > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative w-full max-w-lg mx-4 bg-white rounded-2xl shadow-xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">
            {initial.name ? "Modifier le produit" : "Ajouter un produit"}
          </h2>
          <button onClick={onClose} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          {/* Name */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">Nom du produit *</label>
            <input
              className="input-base w-full"
              placeholder="Ex: T-shirt Premium"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">Description</label>
            <textarea
              className="input-base w-full min-h-[80px] resize-y"
              placeholder="Description du produit..."
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
          </div>

          {/* Price + SKU row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">Prix (FCFA) *</label>
              <div className="relative">
                <input
                  type="number"
                  min="0"
                  className="input-base w-full pr-16"
                  placeholder="0"
                  value={form.price}
                  onChange={(e) => setForm((f) => ({ ...f, price: e.target.value }))}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-medium text-gray-400">FCFA</span>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">SKU <span className="text-gray-400">(optionnel)</span></label>
              <input
                className="input-base w-full"
                placeholder="REF-001"
                value={form.sku}
                onChange={(e) => setForm((f) => ({ ...f, sku: e.target.value }))}
              />
            </div>
          </div>

          {/* Category */}
          <div className="relative">
            <label className="text-sm font-medium text-gray-700 mb-1 block">Categorie</label>
            <input
              className="input-base w-full"
              placeholder="Ex: Vetements"
              value={form.category}
              onChange={(e) => {
                setForm((f) => ({ ...f, category: e.target.value }));
                setShowCategorySuggestions(true);
              }}
              onFocus={() => setShowCategorySuggestions(true)}
              onBlur={() => setTimeout(() => setShowCategorySuggestions(false), 200)}
            />
            {showCategorySuggestions && (
              <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-xl shadow-lg py-1 max-h-48 overflow-y-auto">
                {CATEGORIES.filter((c) =>
                  !form.category || c.toLowerCase().includes(form.category.toLowerCase())
                ).map((cat) => (
                  <button
                    key={cat}
                    className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                    onMouseDown={() => {
                      setForm((f) => ({ ...f, category: cat }));
                      setShowCategorySuggestions(false);
                    }}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Stock toggle */}
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700">Disponibilite</label>
            <button
              type="button"
              onClick={() => setForm((f) => ({ ...f, in_stock: !f.in_stock }))}
              className={cn(
                "flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-medium border transition-colors",
                form.in_stock
                  ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                  : "bg-red-50 border-red-200 text-red-700",
              )}
            >
              {form.in_stock ? <Check className="h-3.5 w-3.5" /> : <X className="h-3.5 w-3.5" />}
              {form.in_stock ? "En stock" : "Rupture de stock"}
            </button>
          </div>

          {/* Image upload */}
          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">Image du produit</label>
            <div className="flex items-start gap-4">
              {imagePreview ? (
                <div className="relative w-24 h-24 rounded-xl overflow-hidden border border-gray-200 shrink-0">
                  <img src={imagePreview} alt="Preview" className="w-full h-full object-cover" />
                  <button
                    onClick={() => { setImagePreview(null); setForm((f) => ({ ...f, image_url: "" })); }}
                    className="absolute top-1 right-1 rounded-full bg-white/80 p-0.5 text-gray-500 hover:bg-white hover:text-red-500 transition-colors"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ) : (
                <label className="flex flex-col items-center justify-center w-24 h-24 rounded-xl border-2 border-dashed border-gray-200 hover:border-brand-300 cursor-pointer transition-colors shrink-0">
                  <Upload className="h-5 w-5 text-gray-400" />
                  <span className="text-[10px] text-gray-400 mt-1">Upload</span>
                  <input type="file" accept="image/*" className="hidden" onChange={handleImageChange} />
                </label>
              )}
              <p className="text-xs text-gray-400 mt-2">JPG, PNG ou WebP. Max 5 Mo.</p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-100">
          <button onClick={onClose} className="btn-ghost px-4 py-2 text-sm">Annuler</button>
          <button
            disabled={!valid || saving}
            onClick={() => onSave(form)}
            className="btn-primary px-5 py-2 text-sm disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            {initial.name ? "Enregistrer" : "Ajouter"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// ═══ STATS TAB ═══
// ══════════════════════════════════════════════════════════

function StatsTab() {
  const { data: stats, loading } = useApi(() => commerceApi.stats(), [], "commerce-stats");

  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="surface rounded-2xl p-5 space-y-3">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-32" />
          </div>
        ))}
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center py-16 text-gray-400">
        <BarChart3 className="h-12 w-12 mx-auto mb-3 opacity-40" />
        <p className="text-sm">Aucune statistique disponible</p>
      </div>
    );
  }

  const statCards = [
    {
      label: "Chiffre d'affaires",
      value: formatFCFA(stats.total_revenue),
      icon: DollarSign,
      iconColor: "text-emerald-600",
      iconBg: "bg-emerald-50",
    },
    {
      label: "Commandes",
      value: stats.orders_count.toString(),
      icon: ShoppingCart,
      iconColor: "text-blue-600",
      iconBg: "bg-blue-50",
    },
    {
      label: "Panier moyen",
      value: formatFCFA(stats.average_order_value),
      icon: TrendingUp,
      iconColor: "text-purple-600",
      iconBg: "bg-purple-50",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {statCards.map((s) => (
          <div key={s.label} className="surface rounded-2xl p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl", s.iconBg)}>
                <s.icon className={cn("h-5 w-5", s.iconColor)} />
              </div>
              <span className="text-sm text-gray-500">{s.label}</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{s.value}</p>
          </div>
        ))}
      </div>

      {/* Top products */}
      {stats.top_products && stats.top_products.length > 0 && (
        <div className="surface rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Produits les plus vendus</h3>
          <div className="space-y-3">
            {stats.top_products.map((p, i) => {
              const maxRevenue = stats.top_products[0]?.revenue || 1;
              const pct = Math.round((p.revenue / maxRevenue) * 100);
              return (
                <div key={i} className="flex items-center gap-3">
                  <span className="text-xs font-medium text-gray-400 w-5 text-right">{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-800 truncate">{p.name}</span>
                      <span className="text-xs text-gray-500 shrink-0 ml-2">
                        {p.quantity} vendu{p.quantity > 1 ? "s" : ""} &middot; {formatFCFA(p.revenue)}
                      </span>
                    </div>
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-brand-500 transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// ═══ ORDERS TAB ═══
// ══════════════════════════════════════════════════════════

function OrdersTab() {
  const { data: orders, loading, refetch } = useApi(() => commerceApi.orders(), [], "commerce-orders");
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const handleStatusChange = useCallback(async (orderId: string, newStatus: string) => {
    setUpdatingId(orderId);
    try {
      await commerceApi.updateOrderStatus(orderId, newStatus);
      toast.success("Statut mis a jour");
      refetch();
    } catch (err: any) {
      toast.error(err.message || "Erreur lors de la mise a jour");
    } finally {
      setUpdatingId(null);
    }
  }, [refetch]);

  if (loading) {
    return (
      <div className="surface rounded-2xl overflow-hidden">
        <div className="p-4 space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex gap-4">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-4 w-16" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!orders || orders.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <ShoppingCart className="h-12 w-12 mx-auto mb-3 opacity-40" />
        <p className="text-sm">Aucune commande pour le moment</p>
        <p className="text-xs mt-1">Les commandes via WhatsApp apparaitront ici</p>
      </div>
    );
  }

  return (
    <div className="surface rounded-2xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="text-left text-xs font-semibold text-gray-500 px-4 py-3">Client</th>
              <th className="text-left text-xs font-semibold text-gray-500 px-4 py-3">Telephone</th>
              <th className="text-center text-xs font-semibold text-gray-500 px-4 py-3">Articles</th>
              <th className="text-right text-xs font-semibold text-gray-500 px-4 py-3">Total</th>
              <th className="text-center text-xs font-semibold text-gray-500 px-4 py-3">Statut</th>
              <th className="text-right text-xs font-semibold text-gray-500 px-4 py-3">Date</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((order) => {
              const st = ORDER_STATUSES[order.status] || ORDER_STATUSES.pending;
              const itemCount = order.items?.length ?? 0;
              return (
                <tr key={order.id} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                  <td className="px-4 py-3">
                    <span className="text-sm font-medium text-gray-800">{order.customer_name || "—"}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-gray-500">{order.customer_phone || "—"}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-sm text-gray-600">{itemCount} article{itemCount > 1 ? "s" : ""}</span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="text-sm font-semibold text-gray-800">{formatFCFA(order.total)}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-center">
                      <select
                        value={order.status}
                        onChange={(e) => handleStatusChange(order.id, e.target.value)}
                        disabled={updatingId === order.id}
                        className={cn(
                          "text-xs font-semibold rounded-full px-3 py-1 border cursor-pointer appearance-none text-center",
                          st.bg, st.color,
                          updatingId === order.id && "opacity-50",
                        )}
                      >
                        {Object.entries(ORDER_STATUSES).map(([key, val]) => (
                          <option key={key} value={key}>{val.label}</option>
                        ))}
                      </select>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="text-xs text-gray-400">{formatDate(order.created_at)}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════
// ═══ MAIN PAGE ═══
// ══════════════════════════════════════════════════════════

export default function ProductsPage() {
  const { data: products, loading, refetch } = useApi(() => commerceApi.listProducts(), [], "commerce-products");

  // Tab state
  const [tab, setTab] = useState<Tab>("products");

  // Search & filter
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<CommerceProduct | null>(null);
  const [saving, setSaving] = useState(false);

  // Delete confirm
  const [deleteTarget, setDeleteTarget] = useState<CommerceProduct | null>(null);

  // Filtered products
  const filtered = useMemo(() => {
    if (!products) return [];
    let list = [...products];
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((p) =>
        p.name.toLowerCase().includes(q) ||
        (p.description && p.description.toLowerCase().includes(q)) ||
        (p.sku && p.sku.toLowerCase().includes(q))
      );
    }
    if (categoryFilter) {
      list = list.filter((p) => p.category === categoryFilter);
    }
    return list;
  }, [products, search, categoryFilter]);

  // Stats counters
  const totalProducts = products?.length ?? 0;
  const inStock = products?.filter((p) => p.in_stock).length ?? 0;
  const outOfStock = totalProducts - inStock;

  // Unique categories for filter dropdown
  const categories = useMemo(() => {
    if (!products) return [];
    const cats = new Set(products.map((p) => p.category).filter(Boolean));
    return Array.from(cats).sort() as string[];
  }, [products]);

  // Open modal for new product
  const openCreate = useCallback(() => {
    setEditingProduct(null);
    setModalOpen(true);
  }, []);

  // Open modal for editing
  const openEdit = useCallback((product: CommerceProduct) => {
    setEditingProduct(product);
    setModalOpen(true);
  }, []);

  // Save product (create or update)
  const handleSave = useCallback(async (form: ProductForm) => {
    setSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        price: Number(form.price),
        category: form.category.trim() || undefined,
        sku: form.sku.trim() || undefined,
        in_stock: form.in_stock,
        image_url: form.image_url || undefined,
      };
      if (editingProduct) {
        await commerceApi.updateProduct(editingProduct.id, payload);
        toast.success("Produit mis a jour");
      } else {
        await commerceApi.createProduct(payload as any);
        toast.success("Produit ajoute");
      }
      setModalOpen(false);
      setEditingProduct(null);
      refetch();
    } catch (err: any) {
      toast.error(err.message || "Erreur lors de l'enregistrement");
    } finally {
      setSaving(false);
    }
  }, [editingProduct, refetch]);

  // Delete product
  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    try {
      await commerceApi.deleteProduct(deleteTarget.id);
      toast.success("Produit supprime");
      setDeleteTarget(null);
      refetch();
    } catch (err: any) {
      toast.error(err.message || "Erreur lors de la suppression");
    }
  }, [deleteTarget, refetch]);

  // Build modal initial form
  const modalInitial: ProductForm = editingProduct
    ? {
        name: editingProduct.name,
        description: editingProduct.description || "",
        price: String(editingProduct.price),
        category: editingProduct.category || "",
        sku: editingProduct.sku || "",
        in_stock: editingProduct.in_stock,
        image_url: editingProduct.image_url || "",
      }
    : emptyForm;

  const tabs: { key: Tab; label: string; icon: React.ElementType }[] = [
    { key: "products", label: "Produits", icon: Package },
    { key: "orders", label: "Commandes", icon: ShoppingCart },
    { key: "stats", label: "Statistiques", icon: BarChart3 },
  ];

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50">
            <Package className="h-5 w-5 text-brand-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Catalogue Produits</h1>
            <p className="text-sm text-gray-500">Gerez vos produits pour le commerce WhatsApp</p>
          </div>
        </div>
        {tab === "products" && (
          <button onClick={openCreate} className="btn-primary px-4 py-2.5 text-sm flex items-center gap-2 shrink-0">
            <Plus className="h-4 w-4" /> Ajouter un produit
          </button>
        )}
      </div>

      {/* ── Stats bar ── */}
      <div className="flex items-center gap-4 text-sm">
        <span className="flex items-center gap-1.5 text-gray-600">
          <Package className="h-4 w-4 text-gray-400" />
          <strong>{totalProducts}</strong> produit{totalProducts > 1 ? "s" : ""}
        </span>
        <span className="h-4 w-px bg-gray-200" />
        <span className="flex items-center gap-1.5 text-emerald-600">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          <strong>{inStock}</strong> en stock
        </span>
        <span className="h-4 w-px bg-gray-200" />
        <span className="flex items-center gap-1.5 text-red-500">
          <span className="h-2 w-2 rounded-full bg-red-500" />
          <strong>{outOfStock}</strong> en rupture
        </span>
      </div>

      {/* ── Tabs ── */}
      <div className="flex items-center gap-1 border-b border-gray-200">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px",
              tab === t.key
                ? "border-brand-500 text-brand-700"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300",
            )}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Tab Content ── */}
      {tab === "products" && (
        <>
          {/* Search & filter */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                className="input-base w-full pl-10"
                placeholder="Rechercher un produit..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <select
              className="input-base w-full sm:w-48"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              <option value="">Toutes les categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          {/* Product grid */}
          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3, 4, 5, 6].map((i) => <ProductCardSkeleton key={i} />)}
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <Package className="h-12 w-12 mx-auto mb-3 opacity-40" />
              {products && products.length > 0 ? (
                <>
                  <p className="text-sm font-medium">Aucun produit trouve</p>
                  <p className="text-xs mt-1">Essayez un autre terme de recherche</p>
                </>
              ) : (
                <>
                  <p className="text-sm font-medium">Aucun produit</p>
                  <p className="text-xs mt-1">Ajoutez votre premier produit pour le commerce WhatsApp</p>
                  <button onClick={openCreate} className="btn-primary px-4 py-2 text-sm mt-4 inline-flex items-center gap-2">
                    <Plus className="h-4 w-4" /> Ajouter un produit
                  </button>
                </>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map((product) => (
                <div
                  key={product.id}
                  onClick={() => openEdit(product)}
                  className="surface rounded-2xl overflow-hidden cursor-pointer hover:shadow-md transition-shadow group"
                >
                  {/* Image area */}
                  <div className="h-40 bg-gray-50 flex items-center justify-center overflow-hidden">
                    {product.image_url ? (
                      <img
                        src={product.image_url}
                        alt={product.name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                    ) : (
                      <Package className="h-12 w-12 text-gray-200" />
                    )}
                  </div>

                  {/* Card body */}
                  <div className="p-4">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <h3 className="text-sm font-semibold text-gray-900 line-clamp-1">{product.name}</h3>
                      <span className={cn(
                        "flex items-center gap-1 shrink-0",
                        product.in_stock ? "text-emerald-600" : "text-red-500",
                      )}>
                        <span className={cn(
                          "h-2 w-2 rounded-full",
                          product.in_stock ? "bg-emerald-500" : "bg-red-500",
                        )} />
                        <span className="text-[11px] font-medium">
                          {product.in_stock ? "En stock" : "Rupture"}
                        </span>
                      </span>
                    </div>

                    <p className="text-lg font-bold text-gray-900 mb-2">
                      {formatFCFA(product.price)}
                    </p>

                    <div className="flex items-center justify-between">
                      {product.category ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-0.5 text-[11px] font-medium text-gray-600">
                          <Tag className="h-3 w-3" />
                          {product.category}
                        </span>
                      ) : (
                        <span />
                      )}

                      {/* Action buttons */}
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => { e.stopPropagation(); openEdit(product); }}
                          className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-brand-600 transition-colors"
                          title="Modifier"
                        >
                          <Edit3 className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); setDeleteTarget(product); }}
                          className="rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                          title="Supprimer"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {tab === "orders" && <OrdersTab />}
      {tab === "stats" && <StatsTab />}

      {/* ── Product Modal ── */}
      <ProductModal
        key={editingProduct?.id ?? "new"}
        open={modalOpen}
        onClose={() => { setModalOpen(false); setEditingProduct(null); }}
        onSave={handleSave}
        initial={modalInitial}
        saving={saving}
      />

      {/* ── Delete Confirmation ── */}
      <ConfirmDialog
        open={!!deleteTarget}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Supprimer ce produit ?"
        message={`Le produit "${deleteTarget?.name}" sera supprime definitivement. Cette action est irreversible.`}
        confirmLabel="Supprimer"
        variant="danger"
      />
    </div>
  );
}

import { useEffect, useState } from "react";
import { admin } from "@/lib/api";
import { toast } from "sonner";
import { ToggleLeft, ToggleRight, Plus, Trash2, Flag } from "lucide-react";

export default function FeatureFlagsPage() {
  const [flags, setFlags] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formEnabled, setFormEnabled] = useState(false);
  const [creating, setCreating] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const loadFlags = () => {
    admin.featureFlags().then(setFlags).catch(() => {});
  };

  useEffect(() => {
    loadFlags();
  }, []);

  const handleToggle = async (flag: any) => {
    try {
      await admin.updateFlag(flag.id, { enabled_globally: !flag.enabled_globally });
      toast.success(`Flag "${flag.name}" ${!flag.enabled_globally ? "active" : "desactive"}`);
      loadFlags();
    } catch (err: any) {
      toast.error(err.message || "Erreur de mise a jour");
    }
  };

  const handleCreate = async () => {
    if (!formName.trim()) {
      toast.error("Le nom est requis");
      return;
    }
    setCreating(true);
    try {
      await admin.createFlag({
        name: formName.trim(),
        description: formDescription.trim(),
        enabled_globally: formEnabled,
      });
      toast.success("Flag cree avec succes");
      setFormName("");
      setFormDescription("");
      setFormEnabled(false);
      setShowForm(false);
      loadFlags();
    } catch (err: any) {
      toast.error(err.message || "Erreur de creation");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await admin.deleteFlag(id);
      toast.success("Flag supprime");
      setDeleteConfirm(null);
      loadFlags();
    } catch (err: any) {
      toast.error(err.message || "Erreur de suppression");
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Feature Flags</h1>
          <p className="text-sm text-gray-500 mt-1">{flags.length} flag(s) configures</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Ajouter un flag
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Flag className="h-5 w-5 text-brand-400" />
            Nouveau Feature Flag
          </h2>

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Nom</label>
            <input
              type="text"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="ex: enable_ai_images"
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-white placeholder:text-gray-500 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Description</label>
            <input
              type="text"
              value={formDescription}
              onChange={(e) => setFormDescription(e.target.value)}
              placeholder="Description du flag..."
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-white placeholder:text-gray-500 focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setFormEnabled(!formEnabled)}
              className="text-gray-400 hover:text-brand-400 transition-colors"
            >
              {formEnabled ? (
                <ToggleRight className="h-8 w-8 text-brand-400" />
              ) : (
                <ToggleLeft className="h-8 w-8" />
              )}
            </button>
            <span className="text-sm text-gray-300">
              {formEnabled ? "Active globalement" : "Desactive globalement"}
            </span>
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleCreate}
              disabled={creating}
              className="flex items-center gap-2 rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creating ? "Creation..." : "Creer le flag"}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="rounded-lg bg-gray-800 px-5 py-2.5 text-sm text-gray-300 hover:bg-gray-700 transition-colors"
            >
              Annuler
            </button>
          </div>
        </div>
      )}

      {/* Flags List */}
      <div className="space-y-3">
        {flags.map((flag) => (
          <div key={flag.id} className="rounded-xl bg-gray-900 border border-gray-800 p-5">
            <div className="flex items-center gap-4">
              <button
                onClick={() => handleToggle(flag)}
                className="flex-shrink-0 transition-colors"
                title={flag.enabled_globally ? "Desactiver" : "Activer"}
              >
                {flag.enabled_globally ? (
                  <ToggleRight className="h-8 w-8 text-brand-400" />
                ) : (
                  <ToggleLeft className="h-8 w-8 text-gray-500" />
                )}
              </button>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-bold text-white">{flag.name}</p>
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                    flag.enabled_globally ? "bg-emerald-500/10 text-emerald-400" : "bg-gray-700 text-gray-400"
                  }`}>
                    {flag.enabled_globally ? "ON" : "OFF"}
                  </span>
                </div>
                {flag.description && (
                  <p className="text-xs text-gray-500 mt-0.5">{flag.description}</p>
                )}
              </div>

              {flag.tenant_overrides_count != null && (
                <div className="text-right">
                  <p className="text-xs text-gray-500">Overrides</p>
                  <p className="text-sm font-semibold text-gray-300">{flag.tenant_overrides_count}</p>
                </div>
              )}

              <button
                onClick={() => setDeleteConfirm(deleteConfirm === flag.id ? null : flag.id)}
                className="rounded-lg p-2 text-gray-500 hover:text-red-400 hover:bg-gray-800 transition-colors"
                title="Supprimer"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>

            {/* Delete Confirmation */}
            {deleteConfirm === flag.id && (
              <div className="mt-4 flex items-center gap-3 rounded-lg bg-red-500/5 border border-red-500/20 p-3">
                <p className="text-xs text-red-400 flex-1">Supprimer definitivement le flag "{flag.name}" ?</p>
                <button
                  onClick={() => handleDelete(flag.id)}
                  className="rounded-lg bg-red-500/20 px-4 py-1.5 text-xs font-medium text-red-400 hover:bg-red-500/30 transition-colors"
                >
                  Confirmer
                </button>
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className="rounded-lg bg-gray-800 px-4 py-1.5 text-xs text-gray-400 hover:bg-gray-700 transition-colors"
                >
                  Annuler
                </button>
              </div>
            )}
          </div>
        ))}

        {flags.length === 0 && (
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-8 text-center">
            <Flag className="h-8 w-8 text-gray-600 mx-auto mb-3" />
            <p className="text-sm text-gray-500">Aucun feature flag configure</p>
          </div>
        )}
      </div>
    </div>
  );
}

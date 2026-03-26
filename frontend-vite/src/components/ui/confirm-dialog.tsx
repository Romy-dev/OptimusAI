import { AlertTriangle, Loader2 } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "warning" | "default";
  onConfirm: () => void | Promise<void>;
  onCancel: () => void;
}

export function ConfirmDialog({
  open, title, message, confirmLabel = "Confirmer", cancelLabel = "Annuler",
  variant = "default", onConfirm, onCancel,
}: ConfirmDialogProps) {
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  const handleConfirm = async () => {
    setLoading(true);
    try { await onConfirm(); } finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onCancel}>
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl animate-in fade-in zoom-in-95 duration-200" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start gap-3">
          {variant === "danger" && (
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-100 text-red-600 shrink-0">
              <AlertTriangle className="h-5 w-5" />
            </div>
          )}
          <div>
            <h3 className="text-base font-bold text-gray-900">{title}</h3>
            <p className="mt-1 text-sm text-gray-500">{message}</p>
          </div>
        </div>
        <div className="mt-5 flex gap-3">
          <button onClick={onCancel} disabled={loading} className="btn-secondary flex-1">{cancelLabel}</button>
          <button
            onClick={handleConfirm}
            disabled={loading}
            className={cn("flex-1 inline-flex items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all duration-150 disabled:opacity-50",
              variant === "danger" ? "bg-red-500 hover:bg-red-600" : "bg-brand-500 hover:bg-brand-600"
            )}
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

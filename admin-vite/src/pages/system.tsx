import { useEffect, useState } from "react";
import { admin } from "@/lib/api";
import { toast } from "sonner";
import {
  Wifi, HardDrive, Database, RefreshCw, Loader2,
} from "lucide-react";

export default function SystemPage() {
  const [ws, setWs] = useState<any>(null);
  const [queue, setQueue] = useState<any>(null);
  const [storage, setStorage] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    try {
      const [w, q, s] = await Promise.all([
        admin.websockets(),
        admin.queue(),
        admin.storage(),
      ]);
      setWs(w);
      setQueue(q);
      setStorage(s);
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  return (
    <div className="space-y-8 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Systeme</h1>
          <p className="text-sm text-gray-500 mt-1">WebSockets, queue ARQ, stockage MinIO</p>
        </div>
        <button onClick={refresh} disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg bg-gray-800 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 disabled:opacity-50 transition-colors">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          Rafraichir
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* WebSockets */}
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Wifi className="h-4 w-4 text-brand-400" />
            <h2 className="text-sm font-semibold text-white">WebSockets</h2>
          </div>
          {ws && (
            <>
              <p className="text-3xl font-bold text-white">{ws.total_connections}</p>
              <p className="text-xs text-gray-500 mt-1">connexions actives</p>
              {Object.keys(ws.by_tenant || {}).length > 0 && (
                <div className="mt-4 space-y-2">
                  {Object.entries(ws.by_tenant).map(([tenantId, users]: [string, any]) => (
                    <div key={tenantId} className="rounded-lg bg-gray-800/50 p-2">
                      <p className="text-[10px] text-gray-500 font-mono">{tenantId.slice(0, 8)}...</p>
                      <p className="text-xs text-gray-400">{users.length} user(s)</p>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {/* Queue */}
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Database className="h-4 w-4 text-amber-400" />
            <h2 className="text-sm font-semibold text-white">Queue ARQ</h2>
          </div>
          {queue && (
            <>
              <div className="space-y-3">
                <div>
                  <p className="text-3xl font-bold text-white">{queue.pending_jobs}</p>
                  <p className="text-xs text-gray-500">jobs en attente</p>
                </div>
                <div>
                  <p className="text-xl font-bold text-gray-400">{queue.completed_results}</p>
                  <p className="text-xs text-gray-500">resultats en cache</p>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Storage */}
        <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
          <div className="flex items-center gap-2 mb-4">
            <HardDrive className="h-4 w-4 text-sky-400" />
            <h2 className="text-sm font-semibold text-white">Stockage MinIO</h2>
          </div>
          {storage && storage.status === "ok" ? (
            <>
              <p className="text-3xl font-bold text-white">{storage.total_size_mb} <span className="text-lg text-gray-500">MB</span></p>
              <p className="text-xs text-gray-500 mt-1">{storage.total_objects} objets dans {storage.bucket}</p>
            </>
          ) : storage ? (
            <p className="text-sm text-red-400">{storage.error || "Erreur"}</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

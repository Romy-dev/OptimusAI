import { useState, useEffect, useCallback, useRef } from "react";

/**
 * Global in-memory cache for API responses.
 * Persists across component mounts/unmounts (stale-while-revalidate).
 */
const cache = new Map<string, { data: any; timestamp: number }>();
const CACHE_TTL = 30_000; // 30s — data older than this triggers a background refetch

/**
 * Hook for fetching data with instant navigation via cache.
 *
 * On mount:
 * 1. If cached data exists → show immediately (loading = false)
 * 2. Refetch in background → update silently when done
 * 3. If no cache → show loading spinner → fetch → display
 *
 * @param key Unique cache key (e.g. "posts-list", "approvals")
 * @param fetcher Async function that returns data
 * @param deps Dependencies that trigger a refetch
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: any[] = [],
  key?: string,
) {
  // Generate a stable cache key from the fetcher toString + deps
  const cacheKey = key || fetcher.toString() + JSON.stringify(deps);

  const cached = cache.get(cacheKey);
  const [data, setData] = useState<T | null>(cached?.data ?? null);
  const [loading, setLoading] = useState(!cached);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  const refetch = useCallback(async () => {
    // If we already have cached data, don't show loading (background refresh)
    const hasCached = cache.has(cacheKey);
    if (!hasCached) setLoading(true);
    setError(null);

    try {
      const result = await fetcher();
      if (!mountedRef.current) return;

      cache.set(cacheKey, { data: result, timestamp: Date.now() });
      setData(result);
    } catch (err: any) {
      if (!mountedRef.current) return;
      setError(err.message || "Erreur de connexion");
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [cacheKey, ...deps]);

  useEffect(() => {
    mountedRef.current = true;

    // If cache is fresh enough, just use it
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      setData(cached.data);
      setLoading(false);
      // Still refetch in background after a short delay
      const timer = setTimeout(refetch, 100);
      return () => { mountedRef.current = false; clearTimeout(timer); };
    }

    // Otherwise fetch now
    refetch();
    return () => { mountedRef.current = false; };
  }, [refetch]);

  return { data, loading, error, refetch, setData };
}

/**
 * Invalidate specific cache entries.
 * Call after mutations (create, update, delete) to force refetch.
 */
export function invalidateCache(keyPattern?: string) {
  if (!keyPattern) {
    cache.clear();
    return;
  }
  for (const key of cache.keys()) {
    if (key.includes(keyPattern)) cache.delete(key);
  }
}

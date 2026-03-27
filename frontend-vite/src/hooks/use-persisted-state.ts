/**
 * usePersistedState — like useState but persists to localStorage.
 * Survives page refreshes. Automatically syncs across tabs.
 * Keys are ISOLATED PER TENANT to prevent data leaking between accounts.
 *
 * Usage:
 *   const [value, setValue] = usePersistedState("my-key", defaultValue);
 */

import { useState, useEffect } from "react";

/**
 * Get the current tenant prefix from the JWT token.
 * This ensures localStorage keys are unique per account.
 */
function getTenantPrefix(): string {
  try {
    const token = localStorage.getItem("token");
    if (!token) return "anon";
    const payload = JSON.parse(atob(token.split(".")[1]));
    // Use tenant_id (short) to prefix keys
    return payload.tenant_id?.slice(0, 8) || payload.sub?.slice(0, 8) || "anon";
  } catch {
    return "anon";
  }
}

function tenantKey(key: string): string {
  return `optimus-${getTenantPrefix()}-${key}`;
}

export function usePersistedState<T>(
  key: string,
  defaultValue: T,
): [T, (value: T | ((prev: T) => T)) => void] {
  const fullKey = tenantKey(key);

  // Initialize from localStorage
  const [state, setState] = useState<T>(() => {
    try {
      const saved = localStorage.getItem(fullKey);
      if (saved !== null) {
        return JSON.parse(saved);
      }
    } catch {}
    return defaultValue;
  });

  // Persist to localStorage on change
  useEffect(() => {
    try {
      if (state === null || state === undefined) {
        localStorage.removeItem(fullKey);
      } else {
        localStorage.setItem(fullKey, JSON.stringify(state));
      }
    } catch {}
  }, [fullKey, state]);

  // Listen for changes from other tabs
  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === fullKey && e.newValue !== null) {
        try {
          setState(JSON.parse(e.newValue));
        } catch {}
      }
    };
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, [fullKey]);

  return [state, setState];
}

/**
 * Tenant-aware localStorage get/set for non-hook usage.
 */
export function getPersistedValue<T>(key: string, defaultValue: T): T {
  try {
    const saved = localStorage.getItem(tenantKey(key));
    return saved !== null ? JSON.parse(saved) : defaultValue;
  } catch {
    return defaultValue;
  }
}

export function setPersistedValue(key: string, value: any) {
  try {
    if (value === null || value === undefined) {
      localStorage.removeItem(tenantKey(key));
    } else {
      localStorage.setItem(tenantKey(key), JSON.stringify(value));
    }
  } catch {}
}

/**
 * clearPersistedState — remove a specific key or all keys for current tenant.
 */
export function clearPersistedState(key?: string) {
  if (key) {
    localStorage.removeItem(tenantKey(key));
  } else {
    const prefix = `optimus-${getTenantPrefix()}-`;
    const keys = Object.keys(localStorage).filter((k) => k.startsWith(prefix));
    keys.forEach((k) => localStorage.removeItem(k));
  }
}

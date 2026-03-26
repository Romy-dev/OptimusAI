/**
 * usePersistedState — like useState but persists to localStorage.
 * Survives page refreshes. Automatically syncs across tabs.
 *
 * Usage:
 *   const [value, setValue] = usePersistedState("my-key", defaultValue);
 */

import { useState, useEffect, useCallback } from "react";

export function usePersistedState<T>(
  key: string,
  defaultValue: T,
): [T, (value: T | ((prev: T) => T)) => void] {
  // Initialize from localStorage
  const [state, setState] = useState<T>(() => {
    try {
      const saved = localStorage.getItem(key);
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
        localStorage.removeItem(key);
      } else {
        localStorage.setItem(key, JSON.stringify(state));
      }
    } catch {}
  }, [key, state]);

  // Listen for changes from other tabs
  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === key && e.newValue !== null) {
        try {
          setState(JSON.parse(e.newValue));
        } catch {}
      }
    };
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, [key]);

  return [state, setState];
}

/**
 * clearPersistedState — remove a specific key or all optimus keys.
 */
export function clearPersistedState(key?: string) {
  if (key) {
    localStorage.removeItem(key);
  } else {
    // Clear all optimus-related keys
    const keys = Object.keys(localStorage).filter((k) => k.startsWith("optimus-"));
    keys.forEach((k) => localStorage.removeItem(k));
  }
}

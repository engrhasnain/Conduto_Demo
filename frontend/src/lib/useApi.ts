"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

const cache = new Map<string, unknown>();
const RETRY_DELAYS = [1000, 2000, 3000, 4000, 5000, 6000, 8000, 10000, 10000, 15000, 15000, 15000, 15000]; // about two minutes
const EVENT = "conduto:invalidate";

/** Drop every cached response and make mounted hooks refetch (after imports / reset). */
export function invalidateAll() {
  cache.clear();
  window.dispatchEvent(new Event(EVENT));
}

interface State<T> {
  path: string | null;
  data: T | null;
  error: string | null;
  loading: boolean;
}

export function useApi<T>(path: string | null) {
  const [state, setState] = useState<State<T>>(() => ({
    path,
    data: path && cache.has(path) ? (cache.get(path) as T) : null,
    error: null,
    loading: !!path && !cache.has(path),
  }));
  const [tick, setTick] = useState(0);

  // path changed: show the cached copy for the new path (or nothing) right away
  if (state.path !== path) {
    setState({ path, data: path && cache.has(path) ? (cache.get(path) as T) : null, error: null, loading: !!path && !cache.has(path) });
  }

  useEffect(() => {
    if (!path) return;
    let alive = true;
    let attempt = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const run = () => {
      api<T>(path)
        .then((d) => {
          cache.set(path, d);
          if (alive) setState({ path, data: d, error: null, loading: false });
        })
        .catch((e: Error) => {
          if (!alive) return;
          // the server may be starting or waking up (free hosting sleeps when idle): keep trying for about two minutes
          if (e.message === "network" && attempt < RETRY_DELAYS.length) {
            timer = setTimeout(run, RETRY_DELAYS[attempt++]);
            return;
          }
          setState((s) => ({ ...s, path, error: e.message, loading: false }));
        });
    };
    run();
    return () => {
      alive = false;
      if (timer) clearTimeout(timer);
    };
  }, [path, tick]);

  useEffect(() => {
    const h = () => setTick((x) => x + 1);
    window.addEventListener(EVENT, h);
    return () => window.removeEventListener(EVENT, h);
  }, []);

  const reload = useCallback(() => setTick((x) => x + 1), []);
  return { data: state.data, error: state.error, loading: state.loading, reload };
}

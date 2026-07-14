/**
 * useFrameworkProfile — module-level singleton that caches the active EA
 * framework profile ("togaf" | "nora"). Same pattern as useGrcEnabled /
 * useBpmEnabled. Primed from /settings/bootstrap on app boot.
 *
 * [FORK FEATURE] — NORA profile support (noraPlan.md WP1.1).
 */
import { useState, useEffect, useCallback } from "react";
import { api } from "@/api/client";

export type FrameworkProfile = "togaf" | "nora";

let _cached: FrameworkProfile | null = null;
let _inflight: Promise<void> | null = null;
let _listeners: Array<(v: FrameworkProfile) => void> = [];

function _notify(v: FrameworkProfile) {
  _cached = v;
  _listeners.forEach((fn) => fn(v));
}

/**
 * Prime the cache from outside the hook (e.g. /settings/bootstrap on app boot)
 * so first-mount consumers skip their own GET.
 */
export function invalidateFrameworkProfile(v: FrameworkProfile) {
  _notify(v);
}

function _fetch(): Promise<void> {
  if (_inflight) return _inflight;
  _inflight = (async () => {
    try {
      const res = await api.get<{ profile: FrameworkProfile }>("/settings/framework-profile");
      _notify(res.profile);
    } catch {
      if (_cached === null) _notify("togaf");
    }
  })().finally(() => {
    _inflight = null;
  });
  return _inflight;
}

export function useFrameworkProfile() {
  const [profile, setProfile] = useState<FrameworkProfile>(_cached ?? "togaf");
  const [loaded, setLoaded] = useState<boolean>(_cached !== null);

  useEffect(() => {
    const listener = (v: FrameworkProfile) => {
      setProfile(v);
      setLoaded(true);
    };
    _listeners.push(listener);
    if (_cached === null) {
      _fetch();
    } else {
      setProfile(_cached);
      setLoaded(true);
    }
    return () => {
      _listeners = _listeners.filter((fn) => fn !== listener);
    };
  }, []);

  const invalidate = useCallback((newVal?: FrameworkProfile) => {
    if (newVal !== undefined) {
      _notify(newVal);
    } else {
      _cached = null;
      _fetch();
    }
  }, []);

  return { profile, profileLoaded: loaded, invalidateProfile: invalidate };
}

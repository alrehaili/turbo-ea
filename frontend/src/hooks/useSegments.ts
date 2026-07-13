import { useEffect, useState, useRef } from "react";
import { api } from "@/api/client";
import type { NoraSegment } from "@/types";

let _cache: NoraSegment[] | null = null;
let _inflight: Promise<NoraSegment[]> | null = null;

/**
 * Module-level singleton hook for NORA segments (boot-time fetch, cached).
 * Fetches segments once and shares across all components.
 */
export function useSegments() {
  const [segments, setSegments] = useState<NoraSegment[] | null>(_cache);
  const [isLoading, setIsLoading] = useState(!_cache && !_inflight);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Return cached value immediately
    if (_cache !== null) {
      setSegments(_cache);
      setIsLoading(false);
      return;
    }

    // Return inflight promise if already fetching
    if (_inflight !== null) {
      _inflight
        .then((data) => {
          setSegments(data);
          setIsLoading(false);
          setError(null);
        })
        .catch((err) => {
          setError(err?.message || "Failed to fetch segments");
          setIsLoading(false);
        });
      return;
    }

    // Start new fetch
    setIsLoading(true);
    _inflight = api.get<NoraSegment[]>("/nora-segments")
      .then((data) => {
        _cache = data;
        _inflight = null;
        setSegments(data);
        setIsLoading(false);
        setError(null);
        return data;
      })
      .catch((err) => {
        _inflight = null;
        const msg = err?.message || "Failed to fetch segments";
        setError(msg);
        setIsLoading(false);
        throw err;
      });
  }, []);

  return { segments: segments || [], isLoading, error };
}

/** Invalidate the segments cache (for when segments are created/updated/deleted). */
export function invalidateSegments() {
  _cache = null;
  _inflight = null;
}

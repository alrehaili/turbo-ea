/**
 * useActiveReferenceModels — module-level singleton caching which of the six
 * NEA domains currently has a *published* reference model (the cheap
 * `/reference-models/active-summary` probe). Backs the card-detail RM code
 * pickers: a text field only upgrades to an autocomplete when its domain has
 * a published RM. Fetched lazily on first use (not bootstrap — only card
 * detail pages with code fields need it), inflight-guarded per project
 * convention.
 *
 * [FORK FEATURE] — Reference Models (noraPlan.md WP100.3).
 */
import { useState, useEffect } from "react";
import { api } from "@/api/client";
import type { ReferenceModelDomain } from "@/types";

export type ActiveRmSummary = Partial<Record<ReferenceModelDomain, boolean>>;

/** Card-attribute code-field key → the RM domain whose published model backs it. */
export const RM_CODE_FIELD_DOMAINS: Record<string, ReferenceModelDomain> = {
  brmCode: "business",
  bxrmCode: "beneficiaryExperience",
  armCode: "applications",
  drmCode: "data",
  trmCode: "technology",
  srmCode: "security",
};

let _cached: ActiveRmSummary | null = null;
let _inflight: Promise<void> | null = null;
let _listeners: Array<(v: ActiveRmSummary) => void> = [];

function _notify(v: ActiveRmSummary) {
  _cached = v;
  _listeners.forEach((fn) => fn(v));
}

/** Drop the cache (e.g. after publish/archive) so consumers refetch. */
export function invalidateActiveReferenceModels() {
  _cached = null;
  if (_listeners.length > 0) _fetch();
}

function _fetch(): Promise<void> {
  if (_inflight) return _inflight;
  _inflight = (async () => {
    try {
      const res = await api.get<ActiveRmSummary>("/reference-models/active-summary");
      _notify(res);
    } catch {
      // Endpoint gated by reference_models.view — treat a failure as "none
      // published" so code fields stay plain text.
      if (_cached === null) _notify({});
    }
  })().finally(() => {
    _inflight = null;
  });
  return _inflight;
}

export function useActiveReferenceModels() {
  const [summary, setSummary] = useState<ActiveRmSummary>(_cached ?? {});
  const [loaded, setLoaded] = useState<boolean>(_cached !== null);

  useEffect(() => {
    const listener = (v: ActiveRmSummary) => {
      setSummary(v);
      setLoaded(true);
    };
    _listeners.push(listener);
    if (_cached === null) {
      _fetch();
    } else {
      setSummary(_cached);
      setLoaded(true);
    }
    return () => {
      _listeners = _listeners.filter((fn) => fn !== listener);
    };
  }, []);

  return { summary, loaded };
}

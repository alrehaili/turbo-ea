import { useCallback } from "react";
import { useSearchParams } from "react-router";

const PERIOD_KEY = /^FY(\d{4})(?:-Q([1-4]))?$/;

/**
 * The reporting period shared by every Executive page, kept in the URL
 * (`?tab=executive&page=…&period=FY2026-Q3`) so it survives a reload, a shared
 * link and a switch between Overview, Decisions and Details. `null` means the
 * default (the current fiscal quarter on the overview, the current fiscal year
 * on Details). A malformed value is treated as absent rather than sent on.
 */
export function useExecutivePeriod(): {
  period: string | null;
  setPeriod: (key: string | null) => void;
} {
  const [params, setParams] = useSearchParams();
  const raw = params.get("period");
  const period = raw && PERIOD_KEY.test(raw) ? raw : null;
  const setPeriod = useCallback(
    (key: string | null) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (key) next.set("period", key);
          else next.delete("period");
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );
  return { period, setPeriod };
}

/** The fiscal year a period key belongs to (`FY2026-Q3` → 2026), or `null`. */
export function fiscalYearOfPeriod(key: string | null): number | null {
  const m = key ? PERIOD_KEY.exec(key) : null;
  return m ? Number(m[1]) : null;
}

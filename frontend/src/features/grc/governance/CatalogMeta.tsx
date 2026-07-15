/**
 * CatalogMeta — shared display of a governance item's domain, adoption status,
 * and authoritative-source traceability. Used by both the read-only GRC
 * Governance panels and the admin editors so principles and standards render
 * their metadata consistently.
 *
 * The authoritative-source register (code → record) is fetched once and cached
 * at module level so the many CatalogMeta instances on a page share one request.
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { api } from "@/api/client";
import MaterialSymbol from "@/components/MaterialSymbol";
import type { AuthoritativeSource } from "@/types";

let _cache: Map<string, AuthoritativeSource> | null = null;
let _inflight: Promise<Map<string, AuthoritativeSource>> | null = null;

async function loadSources(): Promise<Map<string, AuthoritativeSource>> {
  if (_cache) return _cache;
  if (_inflight) return _inflight;
  _inflight = api
    .get<AuthoritativeSource[]>("/metamodel/authoritative-sources")
    .then((rows) => {
      _cache = new Map(rows.map((r) => [r.code, r]));
      return _cache;
    })
    .finally(() => {
      _inflight = null;
    });
  return _inflight;
}

/** Adoption-status → chip colour. Falls back to a neutral chip. */
function adoptionColor(adoption: string): "error" | "warning" | "info" | "default" {
  const a = adoption.toLowerCase();
  if (a.startsWith("mandatory")) return "error";
  if (a.startsWith("conditional")) return "warning";
  if (a.startsWith("preferred") || a.startsWith("recommended")) return "info";
  return "default";
}

interface Props {
  domain?: string | null;
  adoption?: string | null;
  sourceIds?: string[];
}

export default function CatalogMeta({ domain, adoption, sourceIds }: Props) {
  const { t } = useTranslation("grc");
  const [sources, setSources] = useState<Map<string, AuthoritativeSource> | null>(_cache);

  const hasSources = (sourceIds?.length ?? 0) > 0;

  useEffect(() => {
    if (!hasSources || sources) return;
    let cancelled = false;
    loadSources().then((m) => {
      if (!cancelled) setSources(m);
    });
    return () => {
      cancelled = true;
    };
  }, [hasSources, sources]);

  if (!domain && !adoption && !hasSources) return null;

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, flexWrap: "wrap", mt: 0.75 }}>
      {domain && (
        <Chip
          size="small"
          icon={<MaterialSymbol icon="category" size={13} />}
          label={domain}
          variant="outlined"
          sx={{ height: 22, fontSize: 11 }}
        />
      )}
      {adoption && (
        <Chip
          size="small"
          color={adoptionColor(adoption)}
          label={adoption}
          sx={{ height: 22, fontSize: 11, fontWeight: 600 }}
        />
      )}
      {hasSources && (
        <>
          <Typography variant="caption" color="text.secondary" fontWeight={600}>
            {t("governance.sources.label")}:
          </Typography>
          {sourceIds!.map((code) => {
            const src = sources?.get(code);
            const chip = (
              <Chip
                key={code}
                size="small"
                variant="outlined"
                icon={<MaterialSymbol icon="gavel" size={13} />}
                label={code}
                clickable={!!src?.url}
                component={src?.url ? Link : "div"}
                href={src?.url ?? undefined}
                target={src?.url ? "_blank" : undefined}
                rel={src?.url ? "noopener noreferrer" : undefined}
                sx={{ height: 22, fontSize: 11 }}
              />
            );
            const label = src
              ? `${src.title}${src.authority ? ` — ${src.authority}` : ""}`
              : code;
            return (
              <Tooltip key={code} title={label} arrow>
                {chip}
              </Tooltip>
            );
          })}
        </>
      )}
    </Box>
  );
}

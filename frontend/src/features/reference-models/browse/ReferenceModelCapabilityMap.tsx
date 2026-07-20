/**
 * Reference Model — banded capability-map (RMPlan Phase 3, dark poster style).
 *
 * Renders the model as the dark teal capability-map poster: top-level items
 * become full-width bands with a dark header, each band's children become
 * categories (titled columns), and each category's children become clickable
 * capability boxes with a mapped-inventory count. Two-level models degrade to
 * a band whose children are boxes directly. A bottom domain bar switches
 * between the six reference-model domains. Generated entirely from stored
 * data; RTL-aware (columns and text flip with the document direction).
 *
 * [FORK FEATURE] — Reference Models capability map (RMPlan/rmPlan.md §18).
 */
import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import type { ReferenceModelDomain, ReferenceModelItemWithCounts } from "@/types";
import { RM_DOMAIN_META, RM_DOMAIN_ORDER } from "./domainMeta";

// Fixed dark-teal band chrome — the committed poster look, theme-independent.
const BAND_BG = "#15514a";
const BAND_BG_2 = "#1a5c53";

type Coverage = "covered" | "partial" | "notMapped";
function coverageOf(item: ReferenceModelItemWithCounts): Coverage {
  if (item.mapped_direct > 0) return "covered";
  if (item.mapped_total > 0) return "partial";
  return "notMapped";
}
const DOT_COLOR: Record<Coverage, string> = {
  covered: "#2e7d32",
  partial: "#ed6c02",
  notMapped: "#c2ccc9",
};

interface Props {
  domain: ReferenceModelDomain;
  items: ReferenceModelItemWithCounts[];
  itemName: (i: { name: string; name_ar: string | null }) => string;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function ReferenceModelCapabilityMap({
  domain,
  items,
  itemName,
  selectedId,
  onSelect,
}: Props) {
  const { t } = useTranslation(["reports", "nav"]);
  const icon = RM_DOMAIN_META[domain].icon;

  const { bands, childrenOf } = useMemo(() => {
    const byParent = new Map<string | null, ReferenceModelItemWithCounts[]>();
    const known = new Set(items.map((i) => i.id));
    for (const item of items) {
      const parent = item.parent_id && known.has(item.parent_id) ? item.parent_id : null;
      const bucket = byParent.get(parent) ?? [];
      bucket.push(item);
      byParent.set(parent, bucket);
    }
    for (const bucket of byParent.values())
      bucket.sort((a, b) => a.sort_order - b.sort_order || a.code.localeCompare(b.code));
    const childrenOf = (id: string | null) => byParent.get(id) ?? [];
    return { bands: childrenOf(null), childrenOf };
  }, [items]);

  const box = (item: ReferenceModelItemWithCounts) => {
    const cov = coverageOf(item);
    return (
      <Box
        key={item.id}
        onClick={() => onSelect(item.id)}
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 0.75,
          px: 1,
          py: 0.75,
          borderRadius: 1.5,
          bgcolor: "background.paper",
          border: "1px solid",
          borderColor: selectedId === item.id ? BAND_BG : "divider",
          borderInlineStartWidth: 3,
          borderInlineStartColor: DOT_COLOR[cov],
          cursor: "pointer",
          "&:hover": { bgcolor: "action.hover", borderColor: BAND_BG },
        }}
      >
        <MaterialSymbol icon={icon} size={15} style={{ color: BAND_BG, flexShrink: 0 }} />
        <Typography variant="caption" sx={{ flex: 1, minWidth: 0, lineHeight: 1.25 }}>
          {itemName(item)}
        </Typography>
        <Tooltip title={t("rmBrowse.mappedTotalHint")}>
          <Chip size="small" label={item.mapped_total} sx={{ height: 18, minWidth: 26, fontWeight: 700 }} />
        </Tooltip>
      </Box>
    );
  };

  return (
    <Box>
      {bands.map((band) => {
        const cats = childrenOf(band.id);
        const anyCatHasChildren = cats.some((c) => childrenOf(c.id).length > 0);
        return (
          <Paper key={band.id} variant="outlined" sx={{ overflow: "hidden", mb: 1.5 }}>
            <Box
              onClick={() => onSelect(band.id)}
              sx={{
                background: `linear-gradient(0deg, ${BAND_BG}, ${BAND_BG_2})`,
                color: "#fff",
                px: 1.5,
                py: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 1,
                cursor: "pointer",
                position: "relative",
              }}
            >
              <Typography variant="subtitle1" fontWeight={700}>
                {itemName(band)}
              </Typography>
              <Chip
                size="small"
                label={band.mapped_total}
                sx={{
                  position: "absolute",
                  insetInlineEnd: 12,
                  bgcolor: "rgba(255,255,255,0.22)",
                  color: "#fff",
                  fontWeight: 700,
                }}
              />
            </Box>

            <Box sx={{ p: 1.25 }}>
              {cats.length === 0 ? (
                <Typography variant="caption" color="text.secondary">
                  —
                </Typography>
              ) : !anyCatHasChildren ? (
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr 1fr", sm: "repeat(auto-fit, minmax(150px, 1fr))" },
                    gap: 0.75,
                  }}
                >
                  {cats.map(box)}
                </Box>
              ) : (
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", sm: "repeat(auto-fit, minmax(180px, 1fr))" },
                    gap: 1.25,
                    alignItems: "start",
                  }}
                >
                  {cats.map((cat) => {
                    const caps = childrenOf(cat.id);
                    return (
                      <Box key={cat.id} sx={{ minWidth: 0 }}>
                        <Typography
                          onClick={() => onSelect(cat.id)}
                          variant="caption"
                          sx={{
                            display: "block",
                            textAlign: "center",
                            fontWeight: 700,
                            color: "text.primary",
                            mb: 0.75,
                            cursor: "pointer",
                            "&:hover": { color: BAND_BG },
                          }}
                        >
                          {itemName(cat)}
                        </Typography>
                        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.6 }}>
                          {(caps.length > 0 ? caps : [cat]).map(box)}
                        </Box>
                      </Box>
                    );
                  })}
                </Box>
              )}
            </Box>
          </Paper>
        );
      })}

      {/* Bottom domain bar — switch between the reference-model domains. */}
      <Paper
        variant="outlined"
        sx={{
          mt: 0.5,
          px: 1.5,
          py: 1.25,
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "space-around",
          gap: 1.5,
        }}
      >
        {RM_DOMAIN_ORDER.map((d) => (
          <Box
            key={d}
            component={Link}
            to={`/reference-models/${d}`}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 0.75,
              textDecoration: "none",
              color: d === domain ? BAND_BG : "text.secondary",
              fontWeight: d === domain ? 700 : 500,
              fontSize: 13,
              "&:hover": { color: BAND_BG },
            }}
          >
            <MaterialSymbol icon={RM_DOMAIN_META[d].icon} size={18} />
            {t(`nav:noraProgram.domain.${d}`)}
          </Box>
        ))}
      </Paper>
    </Box>
  );
}

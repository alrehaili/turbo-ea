/**
 * Reference Model — poster composition (RMPlan Phase 3 / §18).
 *
 * Wraps the capability map with the editable narrative panels (mission,
 * vision, objectives, stakeholders, principles, KPIs, value, …) so the
 * published model reads like the reference-image slide — but every panel is
 * data authored in the management console, not a static image. Panels with
 * placement "header" render above the map; "grid" panels render below in a
 * responsive grid. With no narrative the poster degrades to just the map.
 *
 * [FORK FEATURE] — Reference Models poster (RMPlan/rmPlan.md).
 */
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import type {
  ReferenceModel,
  ReferenceModelItemWithCounts,
  ReferenceModelNarrativePanel,
} from "@/types";
import { RM_DOMAIN_META } from "./domainMeta";
import ReferenceModelCapabilityMap from "./ReferenceModelCapabilityMap";

interface Props {
  model: ReferenceModel;
  items: ReferenceModelItemWithCounts[];
  itemName: (i: { name: string; name_ar: string | null }) => string;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function ReferenceModelPoster({
  model,
  items,
  itemName,
  selectedId,
  onSelect,
}: Props) {
  const { i18n } = useTranslation(["reports"]);
  const isAr = i18n.language === "ar";
  const color = RM_DOMAIN_META[model.domain].color;

  const panels = model.narrative?.panels ?? [];
  const header = panels.filter((p) => p.placement === "header");
  const grid = panels.filter((p) => p.placement !== "header");

  const panelTitle = (p: ReferenceModelNarrativePanel) =>
    (isAr && p.title_ar ? p.title_ar : p.title) || "";
  const panelText = (p: ReferenceModelNarrativePanel) => (isAr && p.text_ar ? p.text_ar : p.text);
  const panelItems = (p: ReferenceModelNarrativePanel) =>
    isAr && p.items_ar.length === p.items.length && p.items_ar.length > 0 ? p.items_ar : p.items;

  const renderPanel = (p: ReferenceModelNarrativePanel) => (
    <Paper key={p.id} variant="outlined" sx={{ overflow: "hidden", height: "100%" }}>
      <Box sx={{ bgcolor: color, color: "#fff", px: 1.25, py: 0.75 }}>
        <Typography variant="subtitle2" fontWeight={700} sx={{ lineHeight: 1.2 }}>
          {panelTitle(p)}
        </Typography>
      </Box>
      <Box sx={{ p: 1.25 }}>
        {p.kind === "list" ? (
          <Box component="ul" sx={{ m: 0, ps: 2, paddingInlineStart: "18px" }}>
            {panelItems(p).map((it, idx) => (
              <Typography key={idx} component="li" variant="body2" sx={{ mb: 0.25 }}>
                {it}
              </Typography>
            ))}
          </Box>
        ) : (
          <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
            {panelText(p)}
          </Typography>
        )}
      </Box>
    </Paper>
  );

  return (
    <Box>
      {header.length > 0 && (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: `repeat(auto-fit, minmax(200px, 1fr))` },
            gap: 1.5,
            mb: 1.5,
            alignItems: "stretch",
          }}
        >
          {header.map(renderPanel)}
        </Box>
      )}

      <ReferenceModelCapabilityMap
        domain={model.domain}
        items={items}
        itemName={itemName}
        selectedId={selectedId}
        onSelect={onSelect}
      />

      {grid.length > 0 && (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: `repeat(auto-fit, minmax(220px, 1fr))` },
            gap: 1.5,
            mt: 1.5,
            alignItems: "stretch",
          }}
        >
          {grid.map(renderPanel)}
        </Box>
      )}
    </Box>
  );
}

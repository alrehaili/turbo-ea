/**
 * LayerCardDrawer — the "component details" side view of the layer overview
 * pages, in the ea-ui-mvp drawer style: badges + health pill, description, a
 * metamodel-driven field grid, stakeholders, and the list of connected
 * components (clickable — the drawer re-targets in place). A footer button
 * opens the full card page for deep editing.
 * [FORK FEATURE] — noraPlan.md (layer overviews).
 */
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonBase from "@mui/material/ButtonBase";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "@/components/MaterialSymbol";
import ApprovalStatusBadge from "@/components/ApprovalStatusBadge";
import LifecycleBadge, { getCurrentPhase } from "@/components/LifecycleBadge";
import { api } from "@/api/client";
import { useMetamodel } from "@/hooks/useMetamodel";
import {
  useFieldLabel,
  useOptionLabel,
  useRelationLabel,
  useSubtypeLabel,
  useTypeLabel,
} from "@/hooks/useResolveLabel";
import { LAYER_COLORS, STATUS_COLORS } from "@/theme/tokens";
import type { Card, FieldDef } from "@/types";

interface StakeholderRef {
  id: string;
  user_id: string;
  role: string;
  user_display_name?: string | null;
  user_email?: string | null;
}

type CardDetail = Card & { stakeholders?: StakeholderRef[] };

interface DrawerRel {
  relTypeKey: string;
  other: { id: string; type: string; name: string };
  /** true when the drawer card is the relation target (incoming edge). */
  incoming: boolean;
}

interface RelRowResponse {
  type: string;
  source: { id: string; type: string; name: string } | null;
  target: { id: string; type: string; name: string } | null;
}

const STATUS_COLOR: Record<string, string> = {
  healthy: STATUS_COLORS.success,
  warning: STATUS_COLORS.warning,
  risk: STATUS_COLORS.error,
};

export default function LayerCardDrawer({
  cardId,
  layerName,
  onClose,
  onOpenCard,
}: {
  cardId: string | null;
  /** Localized layer name for a card-type category. */
  layerName: (cat: string) => string;
  onClose: () => void;
  /** Re-target the drawer to a connected card. */
  onOpenCard: (id: string) => void;
}) {
  const { t } = useTranslation(["reports", "common"]);
  const navigate = useNavigate();
  const { types, relationTypes } = useMetamodel();
  const typeLabel = useTypeLabel();
  const subtypeLabel = useSubtypeLabel();
  const fieldLabel = useFieldLabel();
  const optionLabel = useOptionLabel();
  const relationLabel = useRelationLabel();
  const [card, setCard] = useState<CardDetail | null>(null);
  const [connections, setConnections] = useState<DrawerRel[]>([]);

  useEffect(() => {
    setCard(null);
    setConnections([]);
    if (!cardId) return;
    let cancelled = false;
    api
      .get<CardDetail>(`/cards/${cardId}`)
      .then((c) => {
        if (!cancelled) setCard(c);
      })
      .catch(() => {
        if (!cancelled) onClose();
      });
    api
      .get<RelRowResponse[]>(`/relations?card_id=${cardId}`)
      .then((rows) => {
        if (cancelled) return;
        const out: DrawerRel[] = [];
        for (const r of rows) {
          if (!r.source || !r.target) continue;
          if (r.source.id === cardId) {
            out.push({ relTypeKey: r.type, other: r.target, incoming: false });
          } else if (r.target.id === cardId) {
            out.push({ relTypeKey: r.type, other: r.source, incoming: true });
          }
        }
        setConnections(out);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cardId]);

  const ty = useMemo(() => types.find((x) => x.key === card?.type), [types, card]);
  const layer = ty?.category;
  const layerColor = layer
    ? ((LAYER_COLORS as Record<string, string>)[layer] ?? STATUS_COLORS.neutral)
    : STATUS_COLORS.neutral;
  const sub = ty?.subtypes?.find((s) => s.key === card?.subtype);
  const relTypeByKey = useMemo(
    () => new Map(relationTypes.map((rt) => [rt.key, rt])),
    [relationTypes],
  );
  const typeByKey = useMemo(() => new Map(types.map((x) => [x.key, x])), [types]);

  /** Scalar attribute values resolved through the metamodel field schema. */
  const fields = useMemo(() => {
    if (!card || !ty) return [];
    const out: { label: string; value: string }[] = [];
    const attrs = card.attributes ?? {};
    for (const section of ty.fields_schema ?? []) {
      for (const f of section.fields ?? []) {
        const raw = attrs[f.key];
        if (raw === undefined || raw === null || raw === "") continue;
        out.push({ label: fieldLabel(f), value: formatValue(f, raw, optionLabel) });
        if (out.length >= 12) return out;
      }
    }
    return out;
  }, [card, ty, fieldLabel, optionLabel]);

  const q = Math.round(card?.data_quality ?? 0);
  const phase = card ? getCurrentPhase(card.lifecycle) : null;
  const status =
    phase === "endOfLife" || q < 50
      ? "risk"
      : phase === "phaseOut" || q < 75
        ? "warning"
        : "healthy";
  const statusColor = STATUS_COLOR[status] ?? STATUS_COLORS.neutral;

  return (
    <Drawer anchor="right" open={Boolean(cardId)} onClose={onClose}>
      <Box sx={{ width: { xs: 340, sm: 420 }, p: 2.5, display: "flex", flexDirection: "column", height: "100%" }}>
        {!card ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            {/* Head */}
            <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1 }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography
                  variant="overline"
                  color="text.secondary"
                  sx={{ lineHeight: 1.4, letterSpacing: 0.8 }}
                  display="block"
                >
                  {t("layerOverview.drawer.title")}
                </Typography>
                <Typography variant="h6" fontWeight={800}>
                  {card.name}
                </Typography>
              </Box>
              <IconButton size="small" onClick={onClose} aria-label={t("common:close")}>
                <MaterialSymbol icon="close" size={20} />
              </IconButton>
            </Box>

            {/* Badges + health */}
            <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
              {layer && (
                <Chip
                  size="small"
                  label={layerName(layer)}
                  sx={{ bgcolor: layerColor, color: "#fff" }}
                />
              )}
              {ty && <Chip size="small" variant="outlined" label={typeLabel(ty)} />}
              {sub && <Chip size="small" variant="outlined" label={subtypeLabel(sub)} />}
            </Stack>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 1.25 }}>
              <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: statusColor }} />
              <Box sx={{ flex: 1, height: 6, borderRadius: 3, bgcolor: "action.hover", overflow: "hidden" }}>
                <Box sx={{ width: `${q}%`, height: "100%", bgcolor: statusColor }} />
              </Box>
              <Typography variant="caption" fontWeight={800}>
                {q}%
              </Typography>
              <LifecycleBadge lifecycle={card.lifecycle} />
              <ApprovalStatusBadge status={card.approval_status} />
            </Box>

            {card.description && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
                {card.description}
              </Typography>
            )}

            <Box sx={{ flex: 1, overflowY: "auto", mt: 1.5 }}>
              {/* Field grid */}
              {fields.length > 0 && (
                <>
                  <Divider sx={{ mb: 1.5 }} />
                  <Typography variant="subtitle2" fontWeight={800} mb={1}>
                    {t("layerOverview.drawer.details")}
                  </Typography>
                  <Box
                    sx={{
                      display: "grid",
                      gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                      gap: 1,
                      mb: 1.5,
                    }}
                  >
                    {fields.map((f) => (
                      <Box key={f.label} sx={{ minWidth: 0 }}>
                        <Typography variant="caption" color="text.secondary" display="block" noWrap>
                          {f.label}
                        </Typography>
                        <Typography variant="body2" fontWeight={700} sx={{ overflowWrap: "anywhere" }}>
                          {f.value}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </>
              )}

              {/* Stakeholders */}
              {(card.stakeholders?.length ?? 0) > 0 && (
                <>
                  <Divider sx={{ mb: 1.5 }} />
                  <Typography variant="subtitle2" fontWeight={800} mb={1}>
                    {t("layerOverview.drawer.stakeholders")}
                  </Typography>
                  <Stack spacing={0.5} sx={{ mb: 1.5 }}>
                    {card.stakeholders!.map((s) => (
                      <Box key={s.id} sx={{ display: "flex", gap: 1, alignItems: "baseline" }}>
                        <Typography variant="body2" fontWeight={700}>
                          {s.user_display_name || s.user_email || s.user_id}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {s.role}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                </>
              )}

              {/* Connected components */}
              <Divider sx={{ mb: 1.5 }} />
              <Typography variant="subtitle2" fontWeight={800} mb={1}>
                {t("layerOverview.drawer.connected")}
              </Typography>
              {connections.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  {t("layerOverview.drawer.noConnections")}
                </Typography>
              ) : (
                <Stack spacing={0.75}>
                  {connections.map((cn, i) => {
                    const otherTy = typeByKey.get(cn.other.type);
                    const otherLayer = otherTy?.category;
                    const oColor = otherLayer
                      ? ((LAYER_COLORS as Record<string, string>)[otherLayer] ??
                        STATUS_COLORS.neutral)
                      : STATUS_COLORS.neutral;
                    const rt = relTypeByKey.get(cn.relTypeKey);
                    const verb = rt ? relationLabel(rt, cn.incoming) : cn.relTypeKey;
                    return (
                      <ButtonBase
                        key={`${cn.other.id}-${i}`}
                        onClick={() => onOpenCard(cn.other.id)}
                        sx={{
                          display: "block",
                          width: "100%",
                          textAlign: "start",
                          border: "1px solid",
                          borderColor: "divider",
                          borderInlineStart: `4px solid ${oColor}`,
                          borderRadius: 1,
                          px: 1.25,
                          py: 0.75,
                          "&:hover": { bgcolor: "action.hover" },
                        }}
                      >
                        <Typography variant="body2" fontWeight={700} noWrap>
                          {cn.other.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" noWrap display="block">
                          {otherLayer ? `${layerName(otherLayer)} • ` : ""}
                          {verb}
                        </Typography>
                      </ButtonBase>
                    );
                  })}
                </Stack>
              )}
            </Box>

            <Button
              variant="contained"
              startIcon={<MaterialSymbol icon="open_in_new" size={18} />}
              onClick={() => navigate(`/cards/${card.id}`)}
              sx={{ mt: 1.5 }}
            >
              {t("layerOverview.drawer.openCard")}
            </Button>
          </>
        )}
      </Box>
    </Drawer>
  );
}

function formatValue(
  f: FieldDef,
  raw: unknown,
  optionLabel: (o: { key: string; label: string } | null | undefined) => string,
): string {
  const resolve = (key: unknown): string => {
    const opt = f.options?.find((o) => o.key === key);
    return opt ? optionLabel(opt) : String(key);
  };
  if (Array.isArray(raw)) return raw.map(resolve).join(", ");
  if (typeof raw === "boolean") return raw ? "✓" : "✗";
  if (f.type === "single_select") return resolve(raw);
  return String(raw);
}

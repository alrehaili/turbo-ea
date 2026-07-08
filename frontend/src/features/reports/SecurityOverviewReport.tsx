/**
 * SecurityOverviewReport — the Security layer overview. Since the NORA 2.0
 * six-layer model, Security is a real card-type category (SecurityControl
 * etc. from the NORA profile); this view lists the layer's cards and layers
 * the GRC posture on top: the EA Risk Register (levels, overdue) and the
 * regulation-driven compliance scanner (per-regulation scores). All halves
 * are best-effort so the page still renders for users without GRC access
 * or before the NORA profile is applied.
 * [FORK FEATURE] — noraPlan.md (security layer).
 */
import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import LinearProgress from "@mui/material/LinearProgress";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import { useMetamodel } from "@/hooks/useMetamodel";
import { useTypeLabel } from "@/hooks/useResolveLabel";
import { SEVERITY_COLORS, STATUS_COLORS } from "@/theme/tokens";
import type { Card } from "@/types";

interface RiskMetrics {
  total: number;
  by_status: Record<string, number>;
  by_level: Record<string, number>;
  overdue: number;
  created_this_month: number;
}

interface ComplianceOverview {
  compliance_scores: Record<string, number>;
}

const LEVEL_ORDER = ["critical", "high", "medium", "low"];
const LEVEL_COLOR: Record<string, string> = {
  critical: SEVERITY_COLORS.critical,
  high: SEVERITY_COLORS.high,
  medium: SEVERITY_COLORS.medium,
  low: SEVERITY_COLORS.low,
};
const OPEN_STATUSES = ["identified", "assessed", "mitigating", "monitoring"];

function scoreColor(score: number): string {
  if (score >= 80) return STATUS_COLORS.success;
  if (score >= 50) return STATUS_COLORS.warning;
  return STATUS_COLORS.error;
}

export default function SecurityOverviewReport() {
  const { t } = useTranslation(["reports", "common"]);
  const { types } = useMetamodel();
  const typeLabel = useTypeLabel();
  const [risk, setRisk] = useState<RiskMetrics | null>(null);
  const [compliance, setCompliance] = useState<ComplianceOverview | null>(null);
  const [layerCards, setLayerCards] = useState<Record<string, Card[]>>({});
  const [loading, setLoading] = useState(true);

  const securityTypes = useMemo(
    () => types.filter((ty) => ty.category === "Security" && !ty.is_hidden),
    [types],
  );

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      api.get<RiskMetrics>("/risks/metrics"),
      api.get<ComplianceOverview>("/compliance/overview"),
    ]).then(([r, c]) => {
      if (!active) return;
      if (r.status === "fulfilled") setRisk(r.value);
      if (c.status === "fulfilled") setCompliance(c.value);
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    if (securityTypes.length === 0) return undefined;
    Promise.allSettled(
      securityTypes.map((ty) =>
        api
          .get<{ items: Card[] }>(`/cards?type=${encodeURIComponent(ty.key)}&page_size=500`)
          .then((r) => [ty.key, r.items] as const),
      ),
    ).then((results) => {
      if (!active) return;
      const byType: Record<string, Card[]> = {};
      for (const res of results) {
        if (res.status === "fulfilled") byType[res.value[0]] = res.value[1];
      }
      setLayerCards(byType);
    });
    return () => {
      active = false;
    };
  }, [securityTypes]);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const openRisks = risk
    ? OPEN_STATUSES.reduce((s, k) => s + (risk.by_status[k] ?? 0), 0) || risk.total
    : 0;
  const critHigh = risk ? (risk.by_level.critical ?? 0) + (risk.by_level.high ?? 0) : 0;
  const scores = compliance ? Object.entries(compliance.compliance_scores) : [];
  const avgCompliance = scores.length
    ? Math.round(scores.reduce((s, [, v]) => s + v, 0) / scores.length)
    : null;
  const maxLevel = Math.max(1, ...(risk ? Object.values(risk.by_level) : [1]));

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 0.5 }}>
        <Box sx={{ width: 8, height: 32, borderRadius: 1, bgcolor: STATUS_COLORS.error }} />
        <Typography variant="h5" fontWeight={800}>
          <MaterialSymbol icon="security" size={26} style={{ verticalAlign: "middle", marginInlineEnd: 8 }} />
          {t("securityLayer.title")}
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("securityLayer.subtitle")}
      </Typography>

      {!risk && !compliance && <Alert severity="info">{t("securityLayer.noAccess")}</Alert>}

      {/* Metric tiles */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(4, 1fr)" },
          gap: 1.5,
          mb: 2,
        }}
      >
        <Tile icon="gpp_maybe" label={t("securityLayer.openRisks")} value={openRisks} color={STATUS_COLORS.info} />
        <Tile
          icon="priority_high"
          label={t("securityLayer.critHigh")}
          value={critHigh}
          color={critHigh ? STATUS_COLORS.error : STATUS_COLORS.neutral}
        />
        <Tile
          icon="schedule"
          label={t("securityLayer.overdue")}
          value={risk?.overdue ?? 0}
          color={risk?.overdue ? STATUS_COLORS.warning : STATUS_COLORS.neutral}
        />
        <Tile
          icon="verified_user"
          label={t("securityLayer.avgCompliance")}
          value={avgCompliance === null ? "—" : `${avgCompliance}%`}
          color={avgCompliance === null ? STATUS_COLORS.neutral : scoreColor(avgCompliance)}
        />
      </Box>

      {/* Security-layer cards (SecurityControl etc. — NORA profile v3) */}
      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" fontWeight={700} mb={1}>
          {t("securityLayer.cardsTitle")}
        </Typography>
        {securityTypes.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {t("securityLayer.cardsEmpty")}
          </Typography>
        ) : (
          <Stack spacing={1.5}>
            {securityTypes.map((ty) => {
              const cards = layerCards[ty.key] ?? [];
              return (
                <Box key={ty.key}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                    <MaterialSymbol icon={ty.icon || "shield"} size={18} color={ty.color || undefined} />
                    <Typography variant="body2" fontWeight={700}>
                      {typeLabel(ty)}
                    </Typography>
                    <Chip size="small" label={cards.length} sx={{ height: 20 }} />
                  </Box>
                  {cards.length === 0 ? (
                    <Typography variant="caption" color="text.secondary">
                      {t("common:none", { defaultValue: "—" })}
                    </Typography>
                  ) : (
                    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
                      {cards.slice(0, 24).map((c) => (
                        <Chip
                          key={c.id}
                          size="small"
                          label={c.name}
                          component={RouterLink}
                          to={`/cards/${c.id}`}
                          clickable
                          sx={{ borderColor: ty.color || undefined }}
                          variant="outlined"
                        />
                      ))}
                      {cards.length > 24 && (
                        <Chip size="small" label={`+${cards.length - 24}`} variant="outlined" />
                      )}
                    </Box>
                  )}
                </Box>
              );
            })}
          </Stack>
        )}
      </Paper>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 2 }}>
        {/* Risk by level */}
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle1" fontWeight={700} mb={1}>
            {t("securityLayer.risksByLevel")}
          </Typography>
          {!risk || risk.total === 0 ? (
            <Typography variant="body2" color="text.secondary">
              {t("securityLayer.noRisks")}
            </Typography>
          ) : (
            <Stack spacing={1}>
              {LEVEL_ORDER.filter((lvl) => (risk.by_level[lvl] ?? 0) > 0).map((lvl) => {
                const count = risk.by_level[lvl] ?? 0;
                return (
                  <Box key={lvl}>
                    <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.25 }}>
                      <Typography variant="body2">{t(`securityLayer.level.${lvl}`)}</Typography>
                      <Typography variant="body2" fontWeight={700}>
                        {count}
                      </Typography>
                    </Box>
                    <Box sx={{ height: 8, borderRadius: 1, bgcolor: "action.hover" }}>
                      <Box
                        sx={{
                          height: 8,
                          borderRadius: 1,
                          width: `${(count / maxLevel) * 100}%`,
                          bgcolor: LEVEL_COLOR[lvl],
                        }}
                      />
                    </Box>
                  </Box>
                );
              })}
            </Stack>
          )}
          <Button
            component={RouterLink}
            to="/grc?tab=risk"
            size="small"
            sx={{ mt: 1.5 }}
            startIcon={<MaterialSymbol icon="open_in_new" size={16} />}
          >
            {t("securityLayer.openRegister")}
          </Button>
        </Paper>

        {/* Compliance by regulation */}
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle1" fontWeight={700} mb={1}>
            {t("securityLayer.compliance")}
          </Typography>
          {scores.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              {t("securityLayer.noCompliance")}
            </Typography>
          ) : (
            <Stack spacing={1.25}>
              {scores
                .sort((a, b) => a[1] - b[1])
                .map(([reg, score]) => (
                  <Box key={reg}>
                    <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.25 }}>
                      <Typography variant="body2">{reg}</Typography>
                      <Typography variant="body2" fontWeight={700} sx={{ color: scoreColor(score) }}>
                        {score}%
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={score}
                      sx={{
                        height: 8,
                        borderRadius: 1,
                        "& .MuiLinearProgress-bar": { bgcolor: scoreColor(score) },
                      }}
                    />
                  </Box>
                ))}
            </Stack>
          )}
          <Button
            component={RouterLink}
            to="/grc?tab=compliance"
            size="small"
            sx={{ mt: 1.5 }}
            startIcon={<MaterialSymbol icon="open_in_new" size={16} />}
          >
            {t("securityLayer.openCompliance")}
          </Button>
        </Paper>
      </Box>
    </Box>
  );
}

function Tile({
  icon,
  label,
  value,
  color,
}: {
  icon: string;
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <Paper variant="outlined" sx={{ p: 2, display: "flex", alignItems: "center", gap: 1.5 }}>
      <MaterialSymbol icon={icon} size={30} color={color} />
      <Box>
        <Typography variant="h5" fontWeight={800} lineHeight={1.1}>
          {value}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
      </Box>
    </Paper>
  );
}

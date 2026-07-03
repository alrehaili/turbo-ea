import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link as RouterLink } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import LinearProgress from "@mui/material/LinearProgress";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import type { Card, CardListResponse, Relation } from "@/types";

interface LayerData {
  apps: Card[];
  capabilities: Card[];
  dataObjects: Card[];
  interfaces: Card[];
  technology: Card[];
  relations: Relation[];
}

interface Segment {
  label: string;
  value: number;
  color: string;
}

const EMPTY_DATA: LayerData = {
  apps: [],
  capabilities: [],
  dataObjects: [],
  interfaces: [],
  technology: [],
  relations: [],
};

const LIFECYCLE_STEPS = [
  ["plan", "description"],
  ["build", "construction"],
  ["test", "science"],
  ["deploy", "rocket_launch"],
  ["operate", "settings"],
  ["retire", "delete"],
];

function attr(card: Card, keys: string[]) {
  for (const key of keys) {
    const value = card.attributes?.[key];
    if (typeof value === "string" && value.trim()) return value;
    if (typeof value === "number") return String(value);
    if (typeof value === "boolean") return value ? "Yes" : "No";
  }
  return undefined;
}

function containsAny(value: string | undefined, words: string[]) {
  const text = (value ?? "").toLowerCase();
  return words.some((word) => text.includes(word));
}

function criticality(card: Card) {
  return attr(card, ["businessCriticality", "criticality", "criticalityLevel", "importance"]);
}

function lifecyclePhase(card: Card) {
  const lifecycle = card.lifecycle;
  if (!lifecycle) return "unknown";
  if (lifecycle.endOfLife) return "retired";
  if (lifecycle.phaseOut) return "atRisk";
  if (lifecycle.active) return "healthy";
  if (lifecycle.phaseIn || lifecycle.plan) return "changing";
  return "unknown";
}

function isCritical(card: Card) {
  return containsAny(criticality(card), ["critical", "high", "mission", "strategic"]);
}

function healthSegments(apps: Card[]): Segment[] {
  const healthy = apps.filter((app) => app.data_quality >= 80 && lifecyclePhase(app) === "healthy").length;
  const atRisk = apps.filter((app) => app.data_quality < 80 || lifecyclePhase(app) === "atRisk").length;
  const retired = apps.filter((app) => lifecyclePhase(app) === "retired").length;
  const unknown = Math.max(apps.length - healthy - atRisk - retired, 0);
  return [
    { label: "Healthy", value: healthy, color: "#2e7d32" },
    { label: "At Risk", value: atRisk, color: "#f9a825" },
    { label: "Retired", value: retired, color: "#78909c" },
    { label: "Unknown", value: unknown, color: "#90a4ae" },
  ].filter((segment) => segment.value > 0);
}

function portfolioSegments(apps: Card[]): Segment[] {
  const counts = new Map<string, number>();
  for (const app of apps) {
    const label =
      attr(app, ["applicationCategory", "category", "portfolioCategory", "businessCriticality"]) ??
      app.subtype ??
      "Unclassified";
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  const colors = ["#2563eb", "#16a34a", "#7c3aed", "#f97316", "#64748b"];
  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([label, value], index) => ({ label, value, color: colors[index] }));
}

function ownerCount(apps: Card[]) {
  const owners = new Set<string>();
  for (const app of apps) {
    for (const stakeholder of app.stakeholders ?? []) {
      owners.add(stakeholder.user_id || stakeholder.user_email || stakeholder.user_display_name || stakeholder.id);
    }
  }
  return owners.size;
}

function relationshipCount(relations: Relation[], type: string) {
  return relations.filter((rel) => rel.source?.type === type || rel.target?.type === type).length;
}

function appGroups(apps: Card[]) {
  const engagement = apps.filter((app) =>
    containsAny(`${app.name} ${app.subtype ?? ""} ${attr(app, ["channel", "applicationCategory"]) ?? ""}`, [
      "portal",
      "mobile",
      "web",
      "customer",
      "engagement",
      "channel",
    ]),
  );
  const support = apps.filter((app) =>
    containsAny(`${app.name} ${app.subtype ?? ""} ${attr(app, ["applicationCategory"]) ?? ""}`, [
      "support",
      "document",
      "service desk",
      "hr",
      "workflow",
      "collaboration",
    ]),
  );
  const taken = new Set([...engagement, ...support].map((app) => app.id));
  const core = apps.filter((app) => !taken.has(app.id));
  return { engagement, core, support };
}

function percent(value: number, total: number) {
  if (!total) return 0;
  return Math.round((value / total) * 100);
}

function Donut({ segments, total }: { segments: Segment[]; total: number }) {
  let start = 0;
  const stops = segments.map((segment) => {
    const size = total ? (segment.value / total) * 100 : 0;
    const stop = `${segment.color} ${start}% ${start + size}%`;
    start += size;
    return stop;
  });
  return (
    <Box
      sx={{
        width: 132,
        height: 132,
        borderRadius: "50%",
        background: `conic-gradient(${stops.join(", ") || "#e2e8f0 0 100%"})`,
        display: "grid",
        placeItems: "center",
        flexShrink: 0,
      }}
    >
      <Box
        sx={{
          width: 82,
          height: 82,
          borderRadius: "50%",
          bgcolor: "background.paper",
          display: "grid",
          placeItems: "center",
          textAlign: "center",
          boxShadow: "inset 0 0 0 1px rgba(15, 23, 42, 0.08)",
        }}
      >
        <Typography variant="h5" sx={{ fontWeight: 800 }}>
          {total}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Total
        </Typography>
      </Box>
    </Box>
  );
}

function MetricCard({
  icon,
  label,
  value,
  helper,
  color,
}: {
  icon: string;
  label: string;
  value: string | number;
  helper?: string;
  color: string;
}) {
  return (
    <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 1, minHeight: 86 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.25 }}>
        <Box
          sx={{
            width: 38,
            height: 38,
            borderRadius: 1,
            bgcolor: `${color}14`,
            color,
            display: "grid",
            placeItems: "center",
            flexShrink: 0,
          }}
        >
          <MaterialSymbol icon={icon} size={23} color="inherit" />
        </Box>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
            {label}
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 850, lineHeight: 1.05 }}>
            {value}
          </Typography>
          {helper && (
            <Typography variant="caption" sx={{ color, fontWeight: 700 }}>
              {helper}
            </Typography>
          )}
        </Box>
      </Box>
    </Paper>
  );
}

function MiniCard({
  card,
  icon,
  color,
}: {
  card: Pick<Card, "id" | "name" | "type" | "subtype">;
  icon: string;
  color: string;
}) {
  return (
    <Box
      component={RouterLink}
      to={`/cards/${card.id}`}
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        minHeight: 52,
        p: 1,
        border: "1px solid",
        borderColor: `${color}33`,
        borderRadius: 1,
        color: "text.primary",
        textDecoration: "none",
        bgcolor: "background.paper",
        "&:hover": { borderColor: color, boxShadow: 1 },
      }}
    >
      <Box
        sx={{
          width: 34,
          height: 34,
          borderRadius: 1,
          bgcolor: `${color}12`,
          color,
          display: "grid",
          placeItems: "center",
          flexShrink: 0,
        }}
      >
        <MaterialSymbol icon={icon} size={21} color="inherit" />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="body2" sx={{ fontWeight: 750 }} noWrap>
          {card.name}
        </Typography>
        {card.subtype && (
          <Typography variant="caption" color="text.secondary" noWrap display="block">
            {card.subtype}
          </Typography>
        )}
      </Box>
    </Box>
  );
}

function LayerBand({
  title,
  subtitle,
  color,
  children,
}: {
  title: string;
  subtitle: string;
  color: string;
  children: ReactNode;
}) {
  return (
    <Box
      sx={{
        border: "1px solid",
        borderColor: `${color}33`,
        bgcolor: `${color}08`,
        borderRadius: 1,
        p: 1.5,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "baseline", gap: 0.75, mb: 1.25, flexWrap: "wrap" }}>
        <Typography variant="subtitle1" sx={{ color, fontWeight: 850 }}>
          {title}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {subtitle}
        </Typography>
      </Box>
      {children}
    </Box>
  );
}

export default function ApplicationLayerOverviewReport() {
  const { t } = useTranslation("reports");
  const [data, setData] = useState<LayerData>(EMPTY_DATA);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [apps, capabilities, dataObjects, interfaces, technology, relations] = await Promise.all([
          api.get<CardListResponse>("/cards?type=Application&page_size=10000"),
          api.get<CardListResponse>("/cards?type=BusinessCapability&page_size=10000"),
          api.get<CardListResponse>("/cards?type=DataObject&page_size=10000"),
          api.get<CardListResponse>("/cards?type=Interface&page_size=10000"),
          api.get<CardListResponse>("/cards?type=ITComponent&page_size=10000"),
          api.get<Relation[]>("/relations"),
        ]);
        if (!cancelled) {
          setData({
            apps: apps.items,
            capabilities: capabilities.items,
            dataObjects: dataObjects.items,
            interfaces: interfaces.items,
            technology: technology.items,
            relations,
          });
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Unable to load view data");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const groups = useMemo(() => appGroups(data.apps), [data.apps]);
  const portfolio = useMemo(() => portfolioSegments(data.apps), [data.apps]);
  const health = useMemo(() => healthSegments(data.apps), [data.apps]);
  const healthyCount = health.find((segment) => segment.label === "Healthy")?.value ?? 0;
  const healthScore = percent(healthyCount, data.apps.length);
  const criticalApps = useMemo(
    () =>
      [...data.apps]
        .filter(isCritical)
        .sort((a, b) => (a.data_quality ?? 0) - (b.data_quality ?? 0))
        .slice(0, 6),
    [data.apps],
  );
  const topCapabilities = data.capabilities.slice(0, 7);
  const topInterfaces = data.interfaces.slice(0, 5);
  const topTechnology = data.technology.slice(0, 8);
  const topData = data.dataObjects.slice(0, 6);
  const integrationCount =
    relationshipCount(data.relations, "Interface") ||
    data.relations.filter((rel) => rel.source?.type === "Application" || rel.target?.type === "Application").length;

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 10 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 1500, mx: "auto" }}>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1fr) 560px" },
          gap: 2,
          alignItems: "start",
          mb: 2,
        }}
      >
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 900, letterSpacing: 0 }}>
            {t("applicationLayer.title")}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
            {t("applicationLayer.subtitle")}
          </Typography>
        </Box>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "repeat(2, 1fr)", md: "repeat(4, 1fr)" },
            gap: 1.25,
          }}
        >
          <MetricCard
            icon="apps"
            label={t("applicationLayer.metric.totalApps")}
            value={data.apps.length}
            helper={t("applicationLayer.metric.critical", { count: criticalApps.length })}
            color="#16a34a"
          />
          <MetricCard
            icon="groups"
            label={t("applicationLayer.metric.owners")}
            value={ownerCount(data.apps)}
            color="#7c3aed"
          />
          <MetricCard
            icon="hub"
            label={t("applicationLayer.metric.integrations")}
            value={integrationCount}
            color="#2563eb"
          />
          <MetricCard
            icon="health_and_safety"
            label={t("applicationLayer.metric.health")}
            value={`${healthScore}%`}
            helper={t("applicationLayer.metric.healthy")}
            color={healthScore >= 75 ? "#16a34a" : "#f97316"}
          />
        </Box>
      </Box>

      {error && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1fr) 360px" },
          gap: 2,
        }}
      >
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 1 }}>
            <LayerBand
              title={t("applicationLayer.band.business")}
              subtitle={t("applicationLayer.band.businessHint")}
              color="#15803d"
            >
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", lg: "repeat(4, 1fr)" },
                  gap: 1,
                }}
              >
                {topCapabilities.map((card) => (
                  <MiniCard key={card.id} card={card} icon="groups" color="#15803d" />
                ))}
                {topCapabilities.length === 0 && (
                  <Typography variant="body2" color="text.secondary">
                    {t("applicationLayer.empty.capabilities")}
                  </Typography>
                )}
              </Box>
            </LayerBand>

            <Box sx={{ display: "grid", placeItems: "center", py: 0.75, color: "#64748b" }}>
              <MaterialSymbol icon="more_vert" size={22} color="inherit" />
            </Box>

            <LayerBand
              title={t("applicationLayer.band.application")}
              subtitle={t("applicationLayer.band.applicationHint")}
              color="#1d4ed8"
            >
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", lg: "1fr 1.45fr 1fr" },
                  gap: 1,
                }}
              >
                {[
                  ["applicationLayer.group.engagement", groups.engagement, "language"],
                  ["applicationLayer.group.core", groups.core, "deployed_code"],
                  ["applicationLayer.group.support", groups.support, "support_agent"],
                ].map(([labelKey, cards, icon]) => (
                  <Box
                    key={String(labelKey)}
                    sx={{
                      border: "1px solid",
                      borderColor: "#bfdbfe",
                      borderRadius: 1,
                      p: 1,
                      bgcolor: "rgba(255, 255, 255, 0.72)",
                    }}
                  >
                    <Typography variant="subtitle2" sx={{ color: "#1d4ed8", fontWeight: 850, mb: 1 }}>
                      {t(String(labelKey))}
                    </Typography>
                    <Box sx={{ display: "grid", gap: 1 }}>
                      {(cards as Card[]).slice(0, 4).map((card) => (
                        <MiniCard key={card.id} card={card} icon={String(icon)} color="#2563eb" />
                      ))}
                      {(cards as Card[]).length === 0 && (
                        <Typography variant="caption" color="text.secondary">
                          {t("applicationLayer.empty.appGroup")}
                        </Typography>
                      )}
                    </Box>
                  </Box>
                ))}
              </Box>

              <Box
                sx={{
                  mt: 1,
                  p: 1,
                  border: "1px solid",
                  borderColor: "#bfdbfe",
                  borderRadius: 1,
                  bgcolor: "background.paper",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 1,
                  color: "#1d4ed8",
                }}
              >
                <MaterialSymbol icon="api" size={24} color="inherit" />
                <Typography variant="subtitle2" sx={{ fontWeight: 850 }}>
                  {t("applicationLayer.integrationLayer")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {topInterfaces.map((item) => item.name).join(", ") || t("applicationLayer.empty.interfaces")}
                </Typography>
              </Box>
            </LayerBand>

            <Box sx={{ display: "grid", placeItems: "center", py: 0.75, color: "#64748b" }}>
              <MaterialSymbol icon="more_vert" size={22} color="inherit" />
            </Box>

            <LayerBand
              title={t("applicationLayer.band.technology")}
              subtitle={t("applicationLayer.band.technologyHint")}
              color="#6d28d9"
            >
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", lg: "repeat(4, 1fr)" },
                  gap: 1,
                }}
              >
                {topTechnology.map((card) => (
                  <MiniCard key={card.id} card={card} icon="memory" color="#6d28d9" />
                ))}
                {topTechnology.length === 0 && (
                  <Typography variant="body2" color="text.secondary">
                    {t("applicationLayer.empty.technology")}
                  </Typography>
                )}
              </Box>
            </LayerBand>

            <Box sx={{ display: "grid", placeItems: "center", py: 0.75, color: "#64748b" }}>
              <MaterialSymbol icon="more_vert" size={22} color="inherit" />
            </Box>

            <LayerBand
              title={t("applicationLayer.band.data")}
              subtitle={t("applicationLayer.band.dataHint")}
              color="#f97316"
            >
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", lg: "repeat(3, 1fr)" },
                  gap: 1,
                }}
              >
                {topData.map((card) => (
                  <MiniCard key={card.id} card={card} icon="database" color="#f97316" />
                ))}
                {topData.length === 0 && (
                  <Typography variant="body2" color="text.secondary">
                    {t("applicationLayer.empty.data")}
                  </Typography>
                )}
              </Box>
            </LayerBand>
          </Paper>

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", lg: "1fr 1.35fr 1.35fr" },
              gap: 1.5,
            }}
          >
            <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 1 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 850, mb: 1 }}>
                {t("applicationLayer.relationships.title")}
              </Typography>
              {[
                ["#16a34a", "dashed", "applicationLayer.relationships.realizes"],
                ["#2563eb", "solid", "applicationLayer.relationships.supports"],
                ["#7c3aed", "solid", "applicationLayer.relationships.integrates"],
                ["#f97316", "dashed", "applicationLayer.relationships.stores"],
              ].map(([color, style, key]) => (
                <Box key={key} sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.75 }}>
                  <Box sx={{ width: 42, borderTop: `2px ${style} ${color}` }} />
                  <Typography variant="caption" color="text.secondary">
                    {t(String(key))}
                  </Typography>
                </Box>
              ))}
            </Paper>

            <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 1 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 850, mb: 1.25 }}>
                {t("applicationLayer.lifecycle.title")}
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                {LIFECYCLE_STEPS.map(([step, icon], index) => (
                  <Box key={step} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Box sx={{ textAlign: "center" }}>
                      <Box
                        sx={{
                          width: 44,
                          height: 44,
                          borderRadius: "50%",
                          bgcolor: index === 5 ? "#fee2e2" : "#eff6ff",
                          color: index === 5 ? "#dc2626" : "#2563eb",
                          display: "grid",
                          placeItems: "center",
                        }}
                      >
                        <MaterialSymbol icon={icon} size={23} color="inherit" />
                      </Box>
                      <Typography variant="caption" sx={{ fontWeight: 700 }}>
                        {t(`applicationLayer.lifecycle.${step}`)}
                      </Typography>
                    </Box>
                    {index < LIFECYCLE_STEPS.length - 1 && (
                      <MaterialSymbol icon="arrow_forward" size={18} color="#94a3b8" />
                    )}
                  </Box>
                ))}
              </Box>
            </Paper>

            <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 1 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 850, mb: 1 }}>
                {t("applicationLayer.actions.title")}
              </Typography>
              <Box sx={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 1 }}>
                <Button component={RouterLink} to="/inventory?type=Application" variant="outlined" sx={{ textTransform: "none" }}>
                  {t("applicationLayer.actions.inventory")}
                </Button>
                <Button component={RouterLink} to="/reports/dependencies" variant="outlined" sx={{ textTransform: "none" }}>
                  {t("applicationLayer.actions.dependencies")}
                </Button>
                <Button component={RouterLink} to="/reports/application-summary" variant="outlined" sx={{ textTransform: "none" }}>
                  {t("applicationLayer.actions.summary")}
                </Button>
                <Button component={RouterLink} to="/reports/portfolio" variant="contained" sx={{ textTransform: "none" }}>
                  {t("applicationLayer.actions.portfolio")}
                </Button>
              </Box>
            </Paper>
          </Box>
        </Box>

        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 850, mb: 1.25 }}>
              {t("applicationLayer.portfolio.title")}
            </Typography>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
              <Donut segments={portfolio} total={data.apps.length} />
              <Box sx={{ flex: 1, minWidth: 0 }}>
                {portfolio.map((segment) => (
                  <Box key={segment.label} sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.75 }}>
                    <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: segment.color }} />
                    <Typography variant="body2" sx={{ flex: 1 }} noWrap>
                      {segment.label}
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 800 }}>
                      {segment.value}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Box>
            <Button component={RouterLink} to="/reports/portfolio" endIcon={<MaterialSymbol icon="arrow_forward" size={18} />} sx={{ mt: 1, textTransform: "none" }}>
              {t("applicationLayer.portfolio.open")}
            </Button>
          </Paper>

          <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 850, mb: 1.25 }}>
              {t("applicationLayer.health.title")}
            </Typography>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
              <Donut segments={health} total={data.apps.length} />
              <Box sx={{ flex: 1 }}>
                <Typography variant="h4" sx={{ fontWeight: 900 }}>
                  {healthScore}%
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  {t("applicationLayer.health.score")}
                </Typography>
                {health.map((segment) => (
                  <Box key={segment.label} sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.75 }}>
                    <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: segment.color }} />
                    <Typography variant="body2" sx={{ flex: 1 }}>
                      {segment.label}
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 800 }}>
                      {segment.value}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Box>
          </Paper>

          <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 850, mb: 1 }}>
              {t("applicationLayer.critical.title")}
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              {criticalApps.map((app) => (
                <Box key={app.id}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Typography
                      component={RouterLink}
                      to={`/cards/${app.id}`}
                      variant="body2"
                      sx={{ color: "primary.main", textDecoration: "none", fontWeight: 750, flex: 1 }}
                    >
                      {app.name}
                    </Typography>
                    <Chip size="small" label={criticality(app) ?? "Critical"} color="error" variant="outlined" />
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={Math.max(0, Math.min(100, app.data_quality ?? 0))}
                    sx={{ mt: 0.5, height: 5, borderRadius: 1 }}
                  />
                </Box>
              ))}
              {criticalApps.length === 0 && (
                <Typography variant="body2" color="text.secondary">
                  {t("applicationLayer.critical.empty")}
                </Typography>
              )}
            </Box>
          </Paper>

          <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 850, mb: 1 }}>
              {t("applicationLayer.value.title")}
            </Typography>
            {[
              ["groups", "applicationLayer.value.business"],
              ["shield", "applicationLayer.value.risk"],
              ["hub", "applicationLayer.value.integration"],
              ["database", "applicationLayer.value.data"],
            ].map(([icon, key]) => (
              <Box key={key} sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                <Box
                  sx={{
                    width: 34,
                    height: 34,
                    borderRadius: 1,
                    bgcolor: "#eff6ff",
                    color: "#2563eb",
                    display: "grid",
                    placeItems: "center",
                    flexShrink: 0,
                  }}
                >
                  <MaterialSymbol icon={icon} size={20} color="inherit" />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  {t(String(key))}
                </Typography>
              </Box>
            ))}
          </Paper>
        </Box>
      </Box>

      <Alert severity="info" icon={<MaterialSymbol icon="info" size={20} /> } sx={{ mt: 2 }}>
        {t("applicationLayer.note")}
      </Alert>
    </Box>
  );
}

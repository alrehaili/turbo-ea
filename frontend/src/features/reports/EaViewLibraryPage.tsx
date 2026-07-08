import { useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Breadcrumbs from "@mui/material/Breadcrumbs";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { useAuthContext } from "@/hooks/AuthContext";
import { useBpmEnabled } from "@/hooks/useBpmEnabled";
import { useGrcEnabled } from "@/hooks/useGrcEnabled";
import { usePpmEnabled } from "@/hooks/usePpmEnabled";
import { CARD_TYPE_COLORS, LAYER_COLORS, SEVERITY_COLORS, STATUS_COLORS } from "@/theme/tokens";

type DomainKey = "enterprise" | "business" | "application" | "data" | "technology" | "governance";
type DomainFilter = DomainKey | "all";

interface ViewCardDef {
  key: string;
  domain: DomainKey;
  titleKey: string;
  bodyKey: string;
  icon: string;
  path: string;
  permission?: string | string[];
  module?: "bpm" | "grc" | "ppm";
  depth?: "overview" | "analysis" | "summary";
}

/**
 * Design tokens for each EA domain. Colors map to the app's LAYER_COLORS /
 * CARD_TYPE_COLORS so the View Library visually reinforces the same layered
 * mental model users see on the Application Layer report and the Layered
 * Dependency View.
 */
const DOMAINS: Array<{ key: DomainKey; icon: string; color: string }> = [
  { key: "enterprise", icon: "account_balance", color: CARD_TYPE_COLORS.Objective },
  { key: "business", icon: "domain", color: LAYER_COLORS.Business },
  { key: "application", icon: "apps", color: LAYER_COLORS.Application },
  { key: "data", icon: "database", color: LAYER_COLORS.Data },
  { key: "technology", icon: "memory", color: LAYER_COLORS.Technology },
  { key: "governance", icon: "gavel", color: CARD_TYPE_COLORS.Provider },
];

const VIEWS: ViewCardDef[] = [
  {
    key: "strategy-map",
    domain: "enterprise",
    titleKey: "viewLibrary.view.strategyMap.title",
    bodyKey: "viewLibrary.view.strategyMap.body",
    icon: "flag",
    path: "/reports/strategy-map",
    depth: "overview",
  },
  {
    key: "roadmap",
    domain: "enterprise",
    titleKey: "viewLibrary.view.roadmap.title",
    bodyKey: "viewLibrary.view.roadmap.body",
    icon: "route",
    path: "/reports/transformation-roadmap",
    depth: "analysis",
  },
  {
    key: "capability-map",
    domain: "business",
    titleKey: "viewLibrary.view.capabilityMap.title",
    bodyKey: "viewLibrary.view.capabilityMap.body",
    icon: "grid_view",
    path: "/reports/capability-map",
    depth: "overview",
  },
  {
    key: "process-map",
    domain: "business",
    titleKey: "viewLibrary.view.processMap.title",
    bodyKey: "viewLibrary.view.processMap.body",
    icon: "account_tree",
    path: "/reports/process-map",
    permission: "reports.bpm_dashboard",
    module: "bpm",
    depth: "analysis",
  },
  {
    key: "service-traceability",
    domain: "business",
    titleKey: "viewLibrary.view.serviceTraceability.title",
    bodyKey: "viewLibrary.view.serviceTraceability.body",
    icon: "conversion_path",
    path: "/reports/service-traceability",
    depth: "summary",
  },
  {
    key: "application-layer",
    domain: "application",
    titleKey: "viewLibrary.view.applicationLayer.title",
    bodyKey: "viewLibrary.view.applicationLayer.body",
    icon: "layers",
    path: "/layers/application",
    permission: "inventory.view",
    depth: "overview",
  },
  {
    key: "application-summary",
    domain: "application",
    titleKey: "viewLibrary.view.applicationSummary.title",
    bodyKey: "viewLibrary.view.applicationSummary.body",
    icon: "article",
    path: "/layers/application-summary",
    permission: "inventory.view",
    depth: "summary",
  },
  {
    key: "portfolio",
    domain: "application",
    titleKey: "viewLibrary.view.portfolio.title",
    bodyKey: "viewLibrary.view.portfolio.body",
    icon: "dashboard",
    path: "/reports/portfolio",
    permission: "reports.portfolio",
    depth: "overview",
  },
  {
    key: "dependencies",
    domain: "application",
    titleKey: "viewLibrary.view.dependencies.title",
    bodyKey: "viewLibrary.view.dependencies.body",
    icon: "hub",
    path: "/reports/dependencies",
    depth: "analysis",
  },
  {
    key: "rationalization",
    domain: "application",
    titleKey: "viewLibrary.view.rationalization.title",
    bodyKey: "viewLibrary.view.rationalization.body",
    icon: "recycling",
    path: "/rationalization",
    permission: "rationalization.view",
    depth: "analysis",
  },
  {
    key: "data-flow",
    domain: "data",
    titleKey: "viewLibrary.view.dataFlow.title",
    bodyKey: "viewLibrary.view.dataFlow.body",
    icon: "schema",
    path: "/reports/data-flow",
    depth: "overview",
  },
  {
    key: "interoperability",
    domain: "data",
    titleKey: "viewLibrary.view.interop.title",
    bodyKey: "viewLibrary.view.interop.body",
    icon: "lan",
    path: "/reports/interoperability",
    depth: "analysis",
  },
  {
    key: "reference-models",
    domain: "technology",
    titleKey: "viewLibrary.view.referenceModels.title",
    bodyKey: "viewLibrary.view.referenceModels.body",
    icon: "hub",
    path: "/reports/reference-models",
    depth: "overview",
  },
  {
    key: "lifecycle",
    domain: "technology",
    titleKey: "viewLibrary.view.lifecycle.title",
    bodyKey: "viewLibrary.view.lifecycle.body",
    icon: "timeline",
    path: "/reports/lifecycle",
    depth: "analysis",
  },
  {
    key: "tech-standards",
    domain: "technology",
    titleKey: "viewLibrary.view.techStandards.title",
    bodyKey: "viewLibrary.view.techStandards.body",
    icon: "radar",
    path: "/tech-standards",
    permission: "tech_standards.view",
    depth: "analysis",
  },
  {
    key: "impact",
    domain: "governance",
    titleKey: "viewLibrary.view.impact.title",
    bodyKey: "viewLibrary.view.impact.body",
    icon: "electric_bolt",
    path: "/reports/impact",
    depth: "analysis",
  },
  {
    key: "gap-analysis",
    domain: "governance",
    titleKey: "viewLibrary.view.gap.title",
    bodyKey: "viewLibrary.view.gap.body",
    icon: "compare_arrows",
    path: "/reports/gap-analysis",
    depth: "analysis",
  },
  {
    key: "grc",
    domain: "governance",
    titleKey: "viewLibrary.view.grc.title",
    bodyKey: "viewLibrary.view.grc.body",
    icon: "policy",
    path: "/grc",
    permission: "grc.view",
    module: "grc",
    depth: "overview",
  },
];

function depthIcon(depth: ViewCardDef["depth"]) {
  if (depth === "summary") return "subject";
  if (depth === "analysis") return "analytics";
  return "travel_explore";
}

function depthColor(depth: ViewCardDef["depth"]) {
  if (depth === "summary") return STATUS_COLORS.neutral;
  if (depth === "analysis") return SEVERITY_COLORS.medium;
  return STATUS_COLORS.info;
}

function withAlpha(hex: string, alpha: string) {
  return `${hex}${alpha}`;
}

export default function EaViewLibraryPage() {
  const { t } = useTranslation(["reports", "nav"]);
  const { user } = useAuthContext();
  const { bpmEnabled } = useBpmEnabled();
  const { grcEnabled } = useGrcEnabled();
  const { ppmEnabled } = usePpmEnabled();
  const [selectedDomain, setSelectedDomain] = useState<DomainFilter>("all");
  const [search, setSearch] = useState("");

  const can = (permission?: string | string[]) => {
    if (!permission) return true;
    const perms = user?.permissions;
    if (!perms) return false;
    if (perms["*"]) return true;
    if (Array.isArray(permission)) return permission.some((p) => !!perms[p]);
    return !!perms[permission];
  };

  const moduleEnabled = (module?: ViewCardDef["module"]) => {
    if (module === "bpm") return bpmEnabled;
    if (module === "grc") return grcEnabled;
    if (module === "ppm") return ppmEnabled;
    return true;
  };

  const visibleViews = useMemo(
    () => VIEWS.filter((view) => can(view.permission) && moduleEnabled(view.module)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [user?.permissions, bpmEnabled, grcEnabled, ppmEnabled],
  );

  const domainColorFor = useMemo(() => {
    const map = new Map<DomainKey, string>();
    for (const d of DOMAINS) map.set(d.key, d.color);
    return (k: DomainKey) => map.get(k) ?? STATUS_COLORS.info;
  }, []);

  // Filter by domain + search. Search matches title and body against the
  // resolved translation strings so users searching in their own language hit.
  const filteredViews = useMemo(() => {
    const q = search.trim().toLowerCase();
    return visibleViews.filter((view) => {
      if (selectedDomain !== "all" && view.domain !== selectedDomain) return false;
      if (!q) return true;
      const title = t(view.titleKey).toLowerCase();
      const body = t(view.bodyKey).toLowerCase();
      return title.includes(q) || body.includes(q);
    });
  }, [visibleViews, selectedDomain, search, t]);

  const totalVisible = visibleViews.length;

  return (
    <Box sx={{ maxWidth: 1320, mx: "auto" }}>
      <Breadcrumbs
        aria-label={t("viewLibrary.breadcrumbs")}
        separator="›"
        sx={{ mb: 1 }}
      >
        <Link
          component={RouterLink}
          to="/"
          underline="hover"
          color="inherit"
          variant="body2"
        >
          {t("dashboard", { ns: "nav" })}
        </Link>
        <Typography variant="body2" color="text.primary" sx={{ fontWeight: 600 }}>
          {t("viewLibrary.title")}
        </Typography>
      </Breadcrumbs>

      <Box sx={{ mb: 2.5 }}>
        <Typography variant="h4" sx={{ fontWeight: 800, letterSpacing: 0 }}>
          {t("viewLibrary.title")}
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 0.75, maxWidth: 900 }}>
          {t("viewLibrary.subtitle")}
        </Typography>
      </Box>

      {/* Search + domain filter row */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "360px 1fr" },
          gap: 1.5,
          alignItems: "center",
          mb: 2,
        }}
      >
        <TextField
          size="small"
          fullWidth
          placeholder={t("viewLibrary.search.placeholder")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <MaterialSymbol icon="search" size={18} color="disabled" />
                </InputAdornment>
              ),
              endAdornment: search ? (
                <InputAdornment position="end">
                  <IconButton
                    size="small"
                    onClick={() => setSearch("")}
                    aria-label={t("viewLibrary.search.clear")}
                  >
                    <MaterialSymbol icon="close" size={16} />
                  </IconButton>
                </InputAdornment>
              ) : undefined,
            },
          }}
        />
        <Box sx={{ display: "flex", gap: 0.75, flexWrap: "wrap" }}>
          <Chip
            label={t("viewLibrary.all", { count: totalVisible })}
            onClick={() => setSelectedDomain("all")}
            variant={selectedDomain === "all" ? "filled" : "outlined"}
            color={selectedDomain === "all" ? "primary" : "default"}
            size="small"
          />
          {DOMAINS.map((domain) => {
            const count = visibleViews.filter((v) => v.domain === domain.key).length;
            if (count === 0) return null;
            const active = selectedDomain === domain.key;
            return (
              <Chip
                key={domain.key}
                icon={
                  <Box sx={{ display: "flex", color: active ? "#fff" : domain.color }}>
                    <MaterialSymbol icon={domain.icon} size={15} color="inherit" />
                  </Box>
                }
                label={`${t(`viewLibrary.domain.${domain.key}.title`)} · ${count}`}
                onClick={() => setSelectedDomain(domain.key)}
                variant={active ? "filled" : "outlined"}
                size="small"
                sx={{
                  borderColor: active ? domain.color : withAlpha(domain.color, "55"),
                  bgcolor: active ? domain.color : "transparent",
                  color: active ? "#fff" : "text.primary",
                  "&:hover": {
                    bgcolor: active ? domain.color : withAlpha(domain.color, "0d"),
                  },
                }}
              />
            );
          })}
        </Box>
      </Box>

      {/* Domain description strip — only when a single domain is selected */}
      {selectedDomain !== "all" && (
        <Paper
          variant="outlined"
          sx={{
            p: 1.5,
            mb: 2,
            borderLeft: `3px solid ${domainColorFor(selectedDomain)}`,
            borderRadius: 1,
            display: "flex",
            alignItems: "center",
            gap: 1.5,
          }}
        >
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: 1,
              bgcolor: domainColorFor(selectedDomain),
              color: "#fff",
              display: "grid",
              placeItems: "center",
              flexShrink: 0,
            }}
          >
            <MaterialSymbol
              icon={DOMAINS.find((d) => d.key === selectedDomain)?.icon ?? "category"}
              size={22}
              color="inherit"
            />
          </Box>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
              {t(`viewLibrary.domain.${selectedDomain}.title`)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t(`viewLibrary.domain.${selectedDomain}.body`)}
            </Typography>
          </Box>
        </Paper>
      )}

      {/* Views grid */}
      {filteredViews.length === 0 ? (
        <Paper
          variant="outlined"
          sx={{
            p: 4,
            borderRadius: 1,
            textAlign: "center",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 1,
          }}
        >
          <MaterialSymbol icon="search_off" size={32} color="disabled" />
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            {t("viewLibrary.search.emptyTitle")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t("viewLibrary.search.emptyBody")}
          </Typography>
          {(search || selectedDomain !== "all") && (
            <Chip
              size="small"
              onClick={() => {
                setSearch("");
                setSelectedDomain("all");
              }}
              icon={<MaterialSymbol icon="restart_alt" size={14} />}
              label={t("viewLibrary.search.reset")}
              sx={{ mt: 1 }}
            />
          )}
        </Paper>
      ) : (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)", xl: "repeat(3, 1fr)" },
            gap: 1.5,
          }}
        >
          {filteredViews.map((view) => {
            const domainColor = domainColorFor(view.domain);
            const dColor = depthColor(view.depth);
            return (
              <Paper
                key={view.key}
                variant="outlined"
                component={RouterLink}
                to={view.path}
                aria-label={`${t(view.titleKey)} — ${t(view.bodyKey)}`}
                sx={{
                  p: 1.75,
                  display: "flex",
                  flexDirection: "column",
                  gap: 1,
                  borderRadius: 1,
                  borderLeft: `3px solid ${domainColor}`,
                  textDecoration: "none",
                  color: "inherit",
                  cursor: "pointer",
                  transition: "transform 120ms, box-shadow 120ms, border-color 120ms",
                  "&:hover": {
                    boxShadow: 3,
                    transform: "translateY(-1px)",
                    borderColor: domainColor,
                  },
                  "&:focus-visible": {
                    outline: `2px solid ${domainColor}`,
                    outlineOffset: 2,
                  },
                }}
              >
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <Box
                    sx={{
                      width: 36,
                      height: 36,
                      borderRadius: 1,
                      bgcolor: withAlpha(domainColor, "1a"),
                      color: domainColor,
                      display: "grid",
                      placeItems: "center",
                      flexShrink: 0,
                    }}
                  >
                    <MaterialSymbol icon={view.icon} size={22} color="inherit" />
                  </Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 800, flex: 1, minWidth: 0 }}>
                    {t(view.titleKey)}
                  </Typography>
                  <MaterialSymbol icon="arrow_forward" size={18} color="disabled" />
                </Box>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    flex: 1,
                    display: "-webkit-box",
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                  }}
                >
                  {t(view.bodyKey)}
                </Typography>
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, flexWrap: "wrap" }}>
                  <Chip
                    size="small"
                    icon={
                      <Box sx={{ display: "flex", color: dColor }}>
                        <MaterialSymbol icon={depthIcon(view.depth)} size={13} color="inherit" />
                      </Box>
                    }
                    label={t(`viewLibrary.depth.${view.depth ?? "overview"}`)}
                    variant="outlined"
                    sx={{
                      borderColor: withAlpha(dColor, "55"),
                      color: dColor,
                      fontWeight: 700,
                    }}
                    // The card itself is the click target — swallow chip clicks
                    // so they don't feel like a separate action.
                    onClick={(e) => e.preventDefault()}
                  />
                  {view.module && (
                    <Chip
                      size="small"
                      label={view.module.toUpperCase()}
                      variant="outlined"
                      onClick={(e) => e.preventDefault()}
                      sx={{ fontWeight: 700 }}
                    />
                  )}
                  <Box sx={{ flex: 1 }} />
                  <Chip
                    size="small"
                    label={t(`viewLibrary.domain.${view.domain}.title`)}
                    variant="outlined"
                    onClick={(e) => {
                      e.preventDefault();
                      setSelectedDomain(view.domain);
                    }}
                    sx={{
                      borderColor: withAlpha(domainColor, "55"),
                      color: domainColor,
                      fontWeight: 700,
                    }}
                  />
                </Box>
              </Paper>
            );
          })}
        </Box>
      )}

    </Box>
  );
}

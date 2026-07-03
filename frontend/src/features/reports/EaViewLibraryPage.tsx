import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { useAuthContext } from "@/hooks/AuthContext";
import { useBpmEnabled } from "@/hooks/useBpmEnabled";
import { useGrcEnabled } from "@/hooks/useGrcEnabled";
import { usePpmEnabled } from "@/hooks/usePpmEnabled";

type DomainKey = "enterprise" | "business" | "application" | "data" | "technology" | "governance";

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

const DOMAINS: Array<{ key: DomainKey; icon: string; color: string }> = [
  { key: "enterprise", icon: "account_balance", color: "#5d4037" },
  { key: "business", icon: "domain", color: "#00695c" },
  { key: "application", icon: "apps", color: "#1565c0" },
  { key: "data", icon: "database", color: "#6a1b9a" },
  { key: "technology", icon: "memory", color: "#455a64" },
  { key: "governance", icon: "gavel", color: "#8d6e00" },
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
    path: "/reports/application-layer",
    permission: "inventory.view",
    depth: "overview",
  },
  {
    key: "application-summary",
    domain: "application",
    titleKey: "viewLibrary.view.applicationSummary.title",
    bodyKey: "viewLibrary.view.applicationSummary.body",
    icon: "article",
    path: "/reports/application-summary",
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

export default function EaViewLibraryPage() {
  const { t } = useTranslation(["reports", "nav"]);
  const navigate = useNavigate();
  const { user } = useAuthContext();
  const { bpmEnabled } = useBpmEnabled();
  const { grcEnabled } = useGrcEnabled();
  const { ppmEnabled } = usePpmEnabled();
  const [selectedDomain, setSelectedDomain] = useState<DomainKey>("business");

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
  const selectedViews = visibleViews.filter((view) => view.domain === selectedDomain);

  return (
    <Box sx={{ maxWidth: 1320, mx: "auto" }}>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 800, letterSpacing: 0 }}>
          {t("viewLibrary.title")}
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 0.75, maxWidth: 900 }}>
          {t("viewLibrary.subtitle")}
        </Typography>
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", lg: "repeat(3, 1fr)" },
          gap: 1.5,
          mb: 3,
        }}
      >
        {DOMAINS.map((domain) => {
          const count = visibleViews.filter((view) => view.domain === domain.key).length;
          const active = domain.key === selectedDomain;
          return (
            <Paper
              key={domain.key}
              component="button"
              type="button"
              onClick={() => setSelectedDomain(domain.key)}
              variant="outlined"
              sx={{
                p: 2,
                textAlign: "left",
                borderColor: active ? domain.color : "divider",
                borderWidth: active ? 2 : 1,
                bgcolor: active ? "rgba(25, 118, 210, 0.04)" : "background.paper",
                cursor: "pointer",
                minHeight: 126,
                borderRadius: 1,
                "&:hover": { borderColor: domain.color, boxShadow: 2 },
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <Box
                  sx={{
                    width: 42,
                    height: 42,
                    borderRadius: 1,
                    bgcolor: domain.color,
                    color: "#fff",
                    display: "grid",
                    placeItems: "center",
                    flexShrink: 0,
                  }}
                >
                  <MaterialSymbol icon={domain.icon} size={24} color="inherit" />
                </Box>
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="h6" sx={{ fontWeight: 750 }}>
                    {t(`viewLibrary.domain.${domain.key}.title`)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t("viewLibrary.viewsCount", { count })}
                  </Typography>
                </Box>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
                {t(`viewLibrary.domain.${domain.key}.body`)}
              </Typography>
            </Paper>
          );
        })}
      </Box>

      <Paper variant="outlined" sx={{ p: 2, borderRadius: 1 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2, flexWrap: "wrap" }}>
          <Typography variant="h5" sx={{ fontWeight: 750, flex: 1 }}>
            {t(`viewLibrary.domain.${selectedDomain}.title`)}
          </Typography>
          <Chip
            size="small"
            icon={<MaterialSymbol icon="touch_app" size={16} />}
            label={t("viewLibrary.drillHint")}
            variant="outlined"
          />
        </Box>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)", xl: "repeat(3, 1fr)" },
            gap: 1.5,
          }}
        >
          {selectedViews.map((view) => (
            <Paper
              key={view.key}
              variant="outlined"
              sx={{
                p: 1.75,
                display: "flex",
                flexDirection: "column",
                gap: 1.25,
                borderRadius: 1,
                minHeight: 208,
                "&:hover": { boxShadow: 2 },
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <MaterialSymbol icon={view.icon} size={24} color="#1565c0" />
                <Typography variant="h6" sx={{ fontWeight: 750, flex: 1 }}>
                  {t(view.titleKey)}
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }}>
                {t(view.bodyKey)}
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                <Chip
                  size="small"
                  icon={<MaterialSymbol icon={depthIcon(view.depth)} size={15} />}
                  label={t(`viewLibrary.depth.${view.depth ?? "overview"}`)}
                  variant="outlined"
                />
                {view.module && (
                  <Chip size="small" label={view.module.toUpperCase()} color="primary" variant="outlined" />
                )}
              </Box>
              <Button
                variant="contained"
                endIcon={<MaterialSymbol icon="arrow_forward" size={18} />}
                onClick={() => navigate(view.path)}
                sx={{ alignSelf: "flex-start", textTransform: "none" }}
              >
                {t("viewLibrary.openView")}
              </Button>
            </Paper>
          ))}
        </Box>
      </Paper>
    </Box>
  );
}

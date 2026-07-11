/**
 * TechnologyLandscapeReport — the NEA Technology-Architecture landscape:
 * ITComponents grouped by data-center containment (DC ⊃ host ⊃ VM ⊃ container
 * engine, from the ITComponent hierarchy) and by network segment. Security
 * components (securityHardware/Software/Service subtypes) can be isolated
 * with a toggle — the WP6.4 security view folded into this report.
 *
 * [FORK FEATURE] — noraPlan.md WP6.3 + WP6.4.
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import FormControlLabel from "@mui/material/FormControlLabel";
import Grid from "@mui/material/Grid";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Switch from "@mui/material/Switch";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import { useMetamodel } from "@/hooks/useMetamodel";
import { useSubtypeLabel } from "@/hooks/useResolveLabel";

interface ComponentEntry {
  id: string;
  name: string;
  subtype: string | null;
  security: boolean;
  network_segment: string | null;
  architecture_state: string;
  depth: number;
}

interface DataCenterEntry extends ComponentEntry {
  components: ComponentEntry[];
}

interface LandscapeData {
  data_centers: DataCenterEntry[];
  unassigned: ComponentEntry[];
  segments: { segment: string; components: ComponentEntry[] }[];
  summary: {
    total: number;
    data_centers: number;
    security_components: number;
    segments: number;
    unsegmented: number;
    by_subtype: Record<string, number>;
  };
}

const SUBTYPE_ICON: Record<string, string> = {
  dataCenter: "apartment",
  physicalHost: "dns",
  virtualServer: "host",
  networkDevice: "router",
  storage: "hard_drive",
  infraTool: "build",
  infraService: "cloud",
  license: "license",
  containerEngine: "deployed_code",
  peripheral: "devices_other",
  securityHardware: "security",
  securitySoftware: "shield_lock",
  securityService: "verified_user",
};

export default function TechnologyLandscapeReport() {
  const { t } = useTranslation(["reports", "common"]);
  const [data, setData] = useState<LandscapeData | null>(null);
  const [error, setError] = useState("");
  const [securityOnly, setSecurityOnly] = useState(false);
  const { types } = useMetamodel();
  const subtypeLabel = useSubtypeLabel();
  const itcType = types.find((ty) => ty.key === "ITComponent");

  useEffect(() => {
    api
      .get<LandscapeData>("/reports/technology-landscape")
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "error"));
  }, []);

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }
  if (!data) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const labelFor = (subtype: string | null) => {
    if (!subtype) return t("technologyLandscape.noSubtype");
    const def = itcType?.subtypes?.find((s) => s.key === subtype);
    return def ? subtypeLabel(def) : subtype;
  };

  const visible = (c: ComponentEntry) => !securityOnly || c.security;

  const renderComponent = (c: ComponentEntry) => (
    <Box
      key={c.id}
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        py: 0.5,
        pl: 2 + c.depth * 3,
        borderBottom: "1px solid",
        borderColor: "divider",
      }}
    >
      <MaterialSymbol
        icon={SUBTYPE_ICON[c.subtype ?? ""] ?? "memory"}
        size={16}
        color={c.security ? "#c62828" : "#78909c"}
      />
      <Link
        component={RouterLink}
        to={`/cards/${c.id}`}
        underline="hover"
        sx={{
          borderBottom: c.architecture_state !== "current" ? "1px dashed" : undefined,
        }}
      >
        {c.name}
      </Link>
      <Typography variant="caption" color="text.secondary">
        {labelFor(c.subtype)}
      </Typography>
      {c.network_segment && (
        <Chip size="small" variant="outlined" label={c.network_segment} sx={{ height: 18 }} />
      )}
    </Box>
  );

  const tiles: { icon: string; color: string; label: string; value: number }[] = [
    {
      icon: "memory",
      color: "#d29270",
      label: t("technologyLandscape.tileTotal"),
      value: data.summary.total,
    },
    {
      icon: "apartment",
      color: "#1976d2",
      label: t("technologyLandscape.tileDataCenters"),
      value: data.summary.data_centers,
    },
    {
      icon: "lan",
      color: "#00897b",
      label: t("technologyLandscape.tileSegments"),
      value: data.summary.segments,
    },
    {
      icon: "shield",
      color: "#c62828",
      label: t("technologyLandscape.tileSecurity"),
      value: data.summary.security_components,
    },
  ];

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
        <Typography variant="h5" fontWeight={700} sx={{ mb: 0.5 }}>
          {t("technologyLandscape.title")}
        </Typography>
        <Box sx={{ flex: 1 }} />
        <FormControlLabel
          control={
            <Switch
              checked={securityOnly}
              onChange={(e) => setSecurityOnly(e.target.checked)}
              size="small"
            />
          }
          label={t("technologyLandscape.securityOnly")}
        />
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("technologyLandscape.subtitle")}
      </Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        {tiles.map((tile) => (
          <Grid item xs={6} md={3} key={tile.label}>
            <Paper sx={{ p: 2, display: "flex", alignItems: "center", gap: 1.5 }}>
              <MaterialSymbol icon={tile.icon} size={26} color={tile.color} />
              <Box>
                <Typography variant="h5" fontWeight={700} lineHeight={1.1}>
                  {tile.value}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {tile.label}
                </Typography>
              </Box>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {/* Data-center containment landscape */}
      <Typography variant="h6" fontWeight={700} sx={{ mb: 1 }}>
        {t("technologyLandscape.dcSection")}
      </Typography>
      {data.data_centers.length === 0 ? (
        <Alert severity="info" sx={{ mb: 3 }}>
          {t("technologyLandscape.dcEmpty")}
        </Alert>
      ) : (
        data.data_centers.map((dc) => {
          const comps = dc.components.filter(visible);
          if (securityOnly && comps.length === 0) return null;
          return (
            <Paper key={dc.id} variant="outlined" sx={{ mb: 2 }}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  px: 2,
                  py: 1,
                  bgcolor: "action.hover",
                }}
              >
                <MaterialSymbol icon="apartment" size={20} color="#1976d2" />
                <Link
                  component={RouterLink}
                  to={`/cards/${dc.id}`}
                  underline="hover"
                  sx={{ fontWeight: 600 }}
                >
                  {dc.name}
                </Link>
                <Chip
                  size="small"
                  variant="outlined"
                  label={`${comps.length} ${t("technologyLandscape.components")}`}
                />
              </Box>
              {comps.map(renderComponent)}
            </Paper>
          );
        })
      )}
      {data.unassigned.filter(visible).length > 0 && (
        <Paper variant="outlined" sx={{ mb: 3 }}>
          <Box sx={{ px: 2, py: 1, bgcolor: "action.hover" }}>
            <Typography fontWeight={600}>{t("technologyLandscape.unassigned")}</Typography>
          </Box>
          {data.unassigned.filter(visible).map(renderComponent)}
        </Paper>
      )}

      {/* Network-segment distribution */}
      <Typography variant="h6" fontWeight={700} sx={{ mb: 1, mt: 3 }}>
        {t("technologyLandscape.segmentSection")}
      </Typography>
      {data.segments.length === 0 ? (
        <Alert severity="info">{t("technologyLandscape.segmentEmpty")}</Alert>
      ) : (
        <Grid container spacing={2}>
          {data.segments.map((seg) => {
            const comps = seg.components.filter(visible);
            if (securityOnly && comps.length === 0) return null;
            return (
              <Grid item xs={12} sm={6} md={4} key={seg.segment}>
                <Paper variant="outlined" sx={{ height: "100%" }}>
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 1,
                      px: 2,
                      py: 1,
                      bgcolor: "action.hover",
                    }}
                  >
                    <MaterialSymbol icon="lan" size={18} color="#00897b" />
                    <Typography fontWeight={600}>{seg.segment}</Typography>
                    <Chip size="small" variant="outlined" label={comps.length} />
                  </Box>
                  <Box sx={{ p: 1, display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                    {comps.map((c) => (
                      <Chip
                        key={c.id}
                        size="small"
                        variant="outlined"
                        color={c.security ? "error" : "default"}
                        icon={
                          <MaterialSymbol
                            icon={SUBTYPE_ICON[c.subtype ?? ""] ?? "memory"}
                            size={14}
                          />
                        }
                        label={c.name}
                        component={RouterLink}
                        to={`/cards/${c.id}`}
                        clickable
                      />
                    ))}
                  </Box>
                </Paper>
              </Grid>
            );
          })}
        </Grid>
      )}
    </Box>
  );
}

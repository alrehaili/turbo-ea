/**
 * Technology Portfolio Report
 * Overview of technology assets and their deployment status.
 * Part of Phase 7: Technology Deployment & Cloud Views.
 */

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import InputAdornment from "@mui/material/InputAdornment";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import ReportShell from "./ReportShell";

interface TechAsset {
  id: string;
  name: string;
  category: string;
  vendor?: string;
  deploymentModel?: string;
  eolStatus?: string;
  criticality: string;
}

export default function TechnologyPortfolioReport() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [assets, setAssets] = useState<TechAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          const [cardResp, vendorRels] = await Promise.all([
            api.get<{ items: any[] }>("/cards?type=ITComponent&page_size=1000"),
            api.get<any[]>("/relations?type=relProviderToITC").catch(() => []),
          ]);
          const cards = Array.isArray(cardResp) ? cardResp : cardResp.items || [];

          // Provider → ITComponent relations give the real vendor per component
          const vendorByComponent = new Map<string, string>();
          for (const rel of vendorRels) {
            if (rel.target_id && rel.source?.name) vendorByComponent.set(rel.target_id, rel.source.name);
          }

          // Cloud subtypes are cloud-deployed by definition; the NORA profile's
          // hostingModel attribute overrides when present.
          const deploymentFor = (c: any): string => {
            const hosting = c.attributes?.hostingModel;
            if (hosting) return hosting;
            if (["saas", "paas", "iaas"].includes(c.subtype)) return "cloud";
            if (["hardware", "software"].includes(c.subtype)) return "on-premises";
            return "unspecified";
          };

          const assets: TechAsset[] = cards.map((c) => ({
            id: c.id,
            name: c.name,
            category: c.subtype || "other",
            vendor: vendorByComponent.get(c.id),
            deploymentModel: deploymentFor(c),
            eolStatus: c.lifecycle?.endOfLife,
            criticality: c.attributes?.resourceClassification || "unclassified",
          }));
          setAssets(assets);
        } catch (err) {
          setError("Failed to load technology assets");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return assets.filter((a) => a.name.toLowerCase().includes(q) || a.vendor?.toLowerCase().includes(q));
  }, [assets, search]);

  const stats = useMemo(() => {
    const total = assets.length;
    const cloud = assets.filter((a) => a.deploymentModel?.toLowerCase().includes("cloud")).length;
    const onprem = assets.filter((a) => a.deploymentModel?.toLowerCase().includes("on-prem")).length;
    const critical = assets.filter((a) => a.criticality?.toLowerCase().includes("critical")).length;
    return { total, cloud, onprem, critical };
  }, [assets]);

  return (
    <ReportShell title={t("techPortfolio.title", "Technology Portfolio")} icon="memory">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("techPortfolio.subtitle", "Inventory of technology assets and their deployment characteristics.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && assets.length === 0 && !error && <Alert severity="info">{t("techPortfolio.empty", "No technology assets found.")}</Alert>}

      {!loading && assets.length > 0 && (
        <>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(4, 1fr)" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {stats.total}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("techPortfolio.metric.total", "Total Assets")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "primary.main" }}>
                {stats.cloud}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("techPortfolio.metric.cloud", "Cloud")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "success.main" }}>
                {stats.onprem}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("techPortfolio.metric.onprem", "On-Prem")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "#f44336" }}>
                {stats.critical}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("techPortfolio.metric.critical", "Critical")}
              </Typography>
            </Paper>
          </Box>

          <TextField
            size="small"
            placeholder={t("techPortfolio.search", "Search technologies…")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <MaterialSymbol icon="search" size={18} color="disabled" />
                  </InputAdornment>
                ),
              },
            }}
            sx={{ mb: 2, maxWidth: 360 }}
          />

          <Paper variant="outlined" sx={{ overflow: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ backgroundColor: "#fafafa" }}>
                  <TableCell sx={{ fontWeight: 700 }}>{t("techPortfolio.col.asset", "Asset")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 120 }}>{t("techPortfolio.col.category", "Category")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 120 }}>{t("techPortfolio.col.vendor", "Vendor")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 130 }}>{t("techPortfolio.col.deployment", "Deployment")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100 }}>{t("techPortfolio.col.criticality", "Criticality")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filtered.map((asset) => (
                  <TableRow key={asset.id} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {asset.name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={asset.category} variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{asset.vendor || "—"}</Typography>
                    </TableCell>
                    <TableCell>
                      {asset.deploymentModel ? (
                        <Chip size="small" label={asset.deploymentModel} />
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          —
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={asset.criticality} variant="outlined" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        </>
      )}
    </ReportShell>
  );
}

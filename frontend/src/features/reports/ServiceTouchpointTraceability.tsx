/**
 * Service Touchpoint Traceability
 * Trace delivery channels and touchpoints for government services.
 * Part of Phase 9: Beneficiary Experience Views.
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
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import ReportShell from "./ReportShell";

interface ServiceTouchpoint {
  service: string;
  channels: number;
  touchpoints: string[];
  coverage: number;
  usage: number;
}

export default function ServiceTouchpointTraceability() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [data, setData] = useState<ServiceTouchpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          // GovService cards (NORA WP1.2) carry deliveryChannel (multi-select)
          // and data_quality; usage is approximated by digital-channel share.
          const resp = await api.get<{ items: any[] }>("/cards?type=GovService&page_size=500");
          const cards = Array.isArray(resp) ? resp : resp.items || [];

          const channelLabels: Record<string, string> = {
            portal: "Portal",
            mobileApp: "Mobile App",
            serviceCenter: "Service Center",
            callCenter: "Call Center",
            kiosk: "Kiosk",
          };
          const digitalChannels = new Set(["portal", "mobileApp"]);

          const services: ServiceTouchpoint[] = cards.map((c) => {
            const raw: string[] = Array.isArray(c.attributes?.deliveryChannel)
              ? c.attributes.deliveryChannel
              : c.attributes?.deliveryChannel
                ? [c.attributes.deliveryChannel]
                : [];
            const digital = raw.filter((ch) => digitalChannels.has(ch)).length;
            return {
              service: c.name,
              channels: raw.length,
              touchpoints: raw.map((ch) => channelLabels[ch] || ch),
              coverage: Math.round(c.data_quality || 0),
              usage: raw.length > 0 ? Math.round((digital / raw.length) * 100) : 0,
            };
          });

          setData(services);
        } catch (err) {
          setError("Failed to load service touchpoint data");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const filtered = useMemo(
    () => data.filter((item) => item.service.toLowerCase().includes(search.toLowerCase())),
    [data, search]
  );

  const stats = useMemo(() => {
    const totalServices = data.length;
    const avgChannels = Math.round(data.reduce((sum, s) => sum + s.channels, 0) / Math.max(data.length, 1));
    const avgCoverage = Math.round(data.reduce((sum, s) => sum + s.coverage, 0) / Math.max(data.length, 1));
    return { totalServices, avgChannels, avgCoverage };
  }, [data]);

  return (
    <ReportShell title={t("serviceTouchpoint.title", "Service Touchpoint Traceability")} icon="connect_without_contact">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("serviceTouchpoint.subtitle", "Government services with their delivery channels and touchpoints.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && data.length === 0 && !error && (
        <Alert severity="info">{t("serviceTouchpoint.empty", "No services found.")}</Alert>
      )}

      {!loading && data.length > 0 && (
        <>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {stats.totalServices}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("serviceTouchpoint.metric.services", "Services")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "primary.main" }}>
                {stats.avgChannels}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("serviceTouchpoint.metric.avgChannels", "Avg Channels")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "success.main" }}>
                {stats.avgCoverage}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("serviceTouchpoint.metric.avgCoverage", "Avg Coverage")}
              </Typography>
            </Paper>
          </Box>

          <TextField
            size="small"
            placeholder={t("serviceTouchpoint.search", "Search services…")}
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
                  <TableCell sx={{ fontWeight: 700 }}>{t("serviceTouchpoint.col.service", "Service")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100, textAlign: "center" }}>{t("serviceTouchpoint.col.channels", "Channels")}</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>{t("serviceTouchpoint.col.touchpoints", "Touchpoints")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100, textAlign: "center" }}>{t("serviceTouchpoint.col.coverage", "Coverage")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100, textAlign: "center" }}>{t("serviceTouchpoint.col.usage", "Usage")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filtered.map((service, idx) => (
                  <TableRow key={idx} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {service.service}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      <Chip size="small" label={service.channels} variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                        {service.touchpoints.map((tp, tpIdx) => (
                          <Chip key={tpIdx} size="small" label={tp} variant="outlined" sx={{ fontSize: "0.7rem" }} />
                        ))}
                      </Box>
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      <Chip
                        size="small"
                        label={`${service.coverage}%`}
                        sx={{ backgroundColor: service.coverage >= 90 ? "#4caf50" : "#ff9800", color: "white" }}
                      />
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      <Typography variant="caption" sx={{ fontWeight: 600, color: service.usage >= 70 ? "#4caf50" : "#ff9800" }}>
                        {service.usage}%
                      </Typography>
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

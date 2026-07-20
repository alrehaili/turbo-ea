/**
 * DataExchangeMapReport — end-to-end data flow for every DataExchange: source
 * applications → exchange → data objects (and their storage) → target
 * applications. GSB routing and NDMO classification surfaced; sensitive
 * off-GSB flows flagged. Complements Service Traceability for the Data domain.
 * [FORK FEATURE] — noraPlan.md WP6.3 / WP4.1.
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";

interface AppRef {
  id: string;
  name: string;
  direction: string | null;
}

interface StorageRef {
  id: string;
  name: string;
}

interface DataObjectRef {
  id: string;
  name: string;
  storage: StorageRef[];
}

interface FlowEntry {
  id: string;
  name: string;
  exchange_method: string | null;
  frequency: string | null;
  via_gsb: boolean;
  classification: string | null;
  external_party: string | null;
  sources: AppRef[];
  targets: AppRef[];
  data_objects: DataObjectRef[];
  flagged: boolean;
}

interface MapData {
  items: FlowEntry[];
  summary: {
    total: number;
    via_gsb: number;
    with_storage: number;
    sensitive_off_gsb: number;
  };
}

const EMPTY: MapData = {
  items: [],
  summary: { total: 0, via_gsb: 0, with_storage: 0, sensitive_off_gsb: 0 },
};

function AppChips({ apps }: { apps: AppRef[] }) {
  if (apps.length === 0) return <>—</>;
  return (
    <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
      {apps.map((a) => (
        <Chip
          key={a.id}
          size="small"
          variant="outlined"
          component={RouterLink}
          to={`/cards/${a.id}`}
          clickable
          label={a.name}
        />
      ))}
    </Box>
  );
}

export default function DataExchangeMapReport() {
  const { t } = useTranslation(["reports", "common"]);
  const [data, setData] = useState<MapData | null>(null);

  useEffect(() => {
    api
      .get<MapData>("/reports/data-exchange-map")
      .then(setData)
      .catch(() => setData(EMPTY));
  }, []);

  if (!data) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 0.5 }}>
        {t("dataExchangeMap.title")}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("dataExchangeMap.subtitle")}
      </Typography>

      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
        <Chip variant="outlined" label={`${t("dataExchangeMap.total")}: ${data.summary.total}`} />
        <Chip
          variant="outlined"
          icon={<MaterialSymbol icon="hub" size={16} />}
          label={`${t("dataExchangeMap.viaGsb")}: ${data.summary.via_gsb}`}
        />
        <Chip
          variant="outlined"
          icon={<MaterialSymbol icon="database" size={16} />}
          label={`${t("dataExchangeMap.withStorage")}: ${data.summary.with_storage}`}
        />
        <Chip
          color={data.summary.sensitive_off_gsb ? "error" : "default"}
          variant="outlined"
          icon={<MaterialSymbol icon="gpp_maybe" size={16} />}
          label={`${t("dataExchangeMap.sensitiveOffGsb")}: ${data.summary.sensitive_off_gsb}`}
        />
      </Box>

      {data.summary.sensitive_off_gsb > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {t("dataExchangeMap.sensitiveHint", { count: data.summary.sensitive_off_gsb })}
        </Alert>
      )}

      {data.items.length === 0 ? (
        <Alert severity="info">{t("dataExchangeMap.empty")}</Alert>
      ) : (
        <Paper variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>{t("dataExchangeMap.colSources")}</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>{t("dataExchangeMap.colExchange")}</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>{t("dataExchangeMap.colDataObjects")}</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>{t("dataExchangeMap.colTargets")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.items.map((f) => (
                <TableRow
                  key={f.id}
                  hover
                  sx={f.flagged ? { bgcolor: "rgba(244, 67, 54, 0.06)" } : undefined}
                >
                  <TableCell sx={{ verticalAlign: "top" }}>
                    <AppChips apps={f.sources} />
                  </TableCell>
                  <TableCell sx={{ verticalAlign: "top" }}>
                    <Link
                      component={RouterLink}
                      to={`/cards/${f.id}`}
                      underline="hover"
                      sx={{ fontWeight: 600, display: "block" }}
                    >
                      {f.name}
                    </Link>
                    <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", mt: 0.5 }}>
                      {f.exchange_method && (
                        <Chip size="small" variant="outlined" label={f.exchange_method} />
                      )}
                      {f.frequency && (
                        <Chip size="small" variant="outlined" label={f.frequency} />
                      )}
                      {f.via_gsb && (
                        <Chip
                          size="small"
                          color="success"
                          variant="outlined"
                          icon={<MaterialSymbol icon="hub" size={14} />}
                          label="GSB"
                        />
                      )}
                      {f.classification && (
                        <Chip
                          size="small"
                          color={f.flagged ? "error" : "default"}
                          variant="outlined"
                          label={f.classification}
                        />
                      )}
                      {f.external_party && (
                        <Chip
                          size="small"
                          variant="outlined"
                          icon={<MaterialSymbol icon="public" size={14} />}
                          label={f.external_party}
                        />
                      )}
                    </Box>
                  </TableCell>
                  <TableCell sx={{ verticalAlign: "top" }}>
                    {f.data_objects.length === 0 ? (
                      "—"
                    ) : (
                      <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
                        {f.data_objects.map((o) => (
                          <Box key={o.id} sx={{ display: "flex", gap: 0.5, alignItems: "center", flexWrap: "wrap" }}>
                            <Chip
                              size="small"
                              variant="outlined"
                              component={RouterLink}
                              to={`/cards/${o.id}`}
                              clickable
                              icon={<MaterialSymbol icon="database" size={14} />}
                              label={o.name}
                            />
                            {o.storage.map((s) => (
                              <Chip
                                key={s.id}
                                size="small"
                                variant="outlined"
                                component={RouterLink}
                                to={`/cards/${s.id}`}
                                clickable
                                icon={<MaterialSymbol icon="memory" size={14} />}
                                label={s.name}
                                sx={{ opacity: 0.8 }}
                              />
                            ))}
                          </Box>
                        ))}
                      </Box>
                    )}
                  </TableCell>
                  <TableCell sx={{ verticalAlign: "top" }}>
                    <AppChips apps={f.targets} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Box>
  );
}

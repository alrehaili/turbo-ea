/**
 * Gap Analysis report — current vs target architecture deltas (NORA Stage 8
 * input). Buckets every architecture-state change (create / replace / modify /
 * retire), shows which transition initiative delivers each change, and flags
 * untraceable changes no initiative owns.
 *
 * [FORK FEATURE] — noraPlan.md WP2.4.
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Link from "@mui/material/Link";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import CardPicker, { type CardOption } from "@/components/CardPicker";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import { useMetamodel } from "@/hooks/useMetamodel";

interface GapInitiative {
  id: string;
  name: string;
  transition_role: string | null;
}

interface GapRow {
  id: string;
  name: string;
  type: string;
  architecture_state: string;
  change_type: string | null;
  initiatives: GapInitiative[];
  replaces?: { id: string; name: string; type: string } | null;
}

interface GapData {
  buckets: Record<"create" | "replace" | "modify" | "retire", GapRow[]>;
  untraceable: GapRow[];
  summary: Record<string, number>;
}

const BUCKETS: Array<{ key: "create" | "replace" | "modify" | "retire"; icon: string; color: string }> = [
  { key: "create", icon: "add_circle", color: "#2e7d32" },
  { key: "replace", icon: "swap_horiz", color: "#1565c0" },
  { key: "modify", icon: "edit", color: "#f9a825" },
  { key: "retire", icon: "do_not_disturb_on", color: "#c62828" },
];

const TRANSITION_ROLES = ["introduces", "modifies", "retires"] as const;

export default function GapAnalysisReport() {
  const { t } = useTranslation(["reports", "common", "cards"]);
  const { relationTypes } = useMetamodel();
  const [data, setData] = useState<GapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [assignFor, setAssignFor] = useState<GapRow | null>(null);
  const [initiative, setInitiative] = useState<CardOption | null>(null);
  const [transitionRole, setTransitionRole] = useState<string>("introduces");
  const [assignError, setAssignError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api.get<GapData>("/reports/gap-analysis"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  /** Find the metamodel relation type linking Initiative ↔ the row's type. */
  const relationFor = (row: GapRow) =>
    relationTypes.find(
      (rt) =>
        (rt.source_type_key === "Initiative" && rt.target_type_key === row.type) ||
        (rt.target_type_key === "Initiative" && rt.source_type_key === row.type),
    );

  const assign = async () => {
    if (!assignFor || !initiative) return;
    const rt = relationFor(assignFor);
    if (!rt) return;
    const initiativeIsSource = rt.source_type_key === "Initiative";
    setAssignError("");
    try {
      await api.post("/relations", {
        type: rt.key,
        source_id: initiativeIsSource ? initiative.id : assignFor.id,
        target_id: initiativeIsSource ? assignFor.id : initiative.id,
        attributes: { transitionRole },
      });
      setAssignFor(null);
      setInitiative(null);
      await load();
    } catch (err) {
      setAssignError(err instanceof Error ? err.message : t("common:errors.generic"));
    }
  };

  if (loading || !data) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const renderRows = (rows: GapRow[]) => (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell sx={{ fontWeight: 700 }}>{t("gapAnalysis.colCard")}</TableCell>
          <TableCell sx={{ fontWeight: 700 }}>{t("gapAnalysis.colType")}</TableCell>
          <TableCell sx={{ fontWeight: 700 }}>{t("gapAnalysis.colReplaces")}</TableCell>
          <TableCell sx={{ fontWeight: 700 }}>{t("gapAnalysis.colInitiatives")}</TableCell>
          <TableCell />
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.id} hover>
            <TableCell>
              <Link component={RouterLink} to={`/cards/${row.id}`} underline="hover">
                {row.name}
              </Link>
            </TableCell>
            <TableCell>{row.type}</TableCell>
            <TableCell>
              {row.replaces ? (
                <Link component={RouterLink} to={`/cards/${row.replaces.id}`} underline="hover">
                  {row.replaces.name}
                </Link>
              ) : (
                "—"
              )}
            </TableCell>
            <TableCell>
              {row.initiatives.length === 0 ? (
                <Chip
                  size="small"
                  color="warning"
                  variant="outlined"
                  icon={<MaterialSymbol icon="link_off" size={14} />}
                  label={t("gapAnalysis.untraceable")}
                />
              ) : (
                <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                  {row.initiatives.map((ini) => (
                    <Chip
                      key={ini.id}
                      size="small"
                      variant="outlined"
                      component={RouterLink}
                      to={`/cards/${ini.id}`}
                      clickable
                      label={
                        ini.transition_role ? `${ini.name} · ${ini.transition_role}` : ini.name
                      }
                    />
                  ))}
                </Box>
              )}
            </TableCell>
            <TableCell align="right">
              <Button
                size="small"
                disabled={!relationFor(row)}
                onClick={() => {
                  setAssignFor(row);
                  setInitiative(null);
                  setTransitionRole(
                    row.change_type === "retire" ? "retires" : "introduces",
                  );
                }}
              >
                {t("gapAnalysis.assignInitiative")}
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 0.5 }}>
        {t("gapAnalysis.title")}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("gapAnalysis.subtitle")}
      </Typography>

      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 3 }}>
        {BUCKETS.map((b) => (
          <Chip
            key={b.key}
            icon={<MaterialSymbol icon={b.icon} size={16} color={b.color} />}
            label={`${t(`gapAnalysis.bucket.${b.key}`)}: ${data.summary[b.key] ?? 0}`}
            variant="outlined"
          />
        ))}
        <Chip
          icon={<MaterialSymbol icon="link_off" size={16} />}
          label={`${t("gapAnalysis.untraceable")}: ${data.summary.untraceable ?? 0}`}
          color={data.summary.untraceable ? "warning" : "default"}
          variant="outlined"
        />
      </Box>

      {data.summary.total_changes === 0 && (
        <Alert severity="info">{t("gapAnalysis.empty")}</Alert>
      )}

      {data.summary.untraceable > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {t("gapAnalysis.untraceableHint", { count: data.summary.untraceable })}
        </Alert>
      )}

      {BUCKETS.filter((b) => data.buckets[b.key].length > 0).map((b) => (
        <Paper key={b.key} variant="outlined" sx={{ mb: 3 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, px: 2, py: 1.5 }}>
            <MaterialSymbol icon={b.icon} size={20} color={b.color} />
            <Typography variant="subtitle1" fontWeight={600}>
              {t(`gapAnalysis.bucket.${b.key}`)}
            </Typography>
          </Box>
          {renderRows(data.buckets[b.key])}
        </Paper>
      ))}

      {/* Assign-to-initiative dialog */}
      <Dialog open={!!assignFor} onClose={() => setAssignFor(null)} fullWidth maxWidth="sm">
        <DialogTitle>{t("gapAnalysis.assignInitiative")}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          {assignError && <Alert severity="error">{assignError}</Alert>}
          <CardPicker
            types="Initiative"
            value={initiative}
            onChange={setInitiative}
            label={t("gapAnalysis.initiative")}
            enabled={!!assignFor}
            autoFocus
          />
          <TextField
            select
            label={t("gapAnalysis.transitionRole")}
            value={transitionRole}
            onChange={(e) => setTransitionRole(e.target.value)}
          >
            {TRANSITION_ROLES.map((r) => (
              <MenuItem key={r} value={r}>
                {t(`gapAnalysis.role.${r}`)}
              </MenuItem>
            ))}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAssignFor(null)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={assign} disabled={!initiative}>
            {t("common:actions.save")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

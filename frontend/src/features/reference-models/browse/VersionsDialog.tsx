/**
 * Reference Model — version history & comparison (RMPlan Phase 5 / §15).
 *
 * Lists the preserved publish snapshots of a model and compares any snapshot
 * against the live model (or another snapshot), showing added / removed /
 * changed items by code. Published models are never silently overwritten —
 * this is the audit view of what each publish approved.
 *
 * [FORK FEATURE] — Reference Models versioning (RMPlan/rmPlan.md).
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import type {
  ReferenceModel,
  ReferenceModelVersion,
  ReferenceModelVersionDiff,
} from "@/types";

interface Props {
  open: boolean;
  model: ReferenceModel | null;
  onClose: () => void;
}

export default function VersionsDialog({ open, model, onClose }: Props) {
  const { t, i18n } = useTranslation(["reports", "common"]);
  const isAr = i18n.language === "ar";
  const [versions, setVersions] = useState<ReferenceModelVersion[] | null>(null);
  const [baseId, setBaseId] = useState("");
  const [against, setAgainst] = useState("current");
  const [diff, setDiff] = useState<ReferenceModelVersionDiff | null>(null);
  const [diffing, setDiffing] = useState(false);

  useEffect(() => {
    if (!open || !model) return;
    setVersions(null);
    setDiff(null);
    api
      .get<{ versions: ReferenceModelVersion[] }>(`/reference-models/${model.id}/versions`)
      .then((res) => {
        setVersions(res.versions);
        if (res.versions[0]) setBaseId(res.versions[0].id);
        setAgainst("current");
      })
      .catch(() => setVersions([]));
  }, [open, model]);

  const runDiff = async () => {
    if (!model || !baseId) return;
    setDiffing(true);
    setDiff(null);
    try {
      const res = await api.get<ReferenceModelVersionDiff>(
        `/reference-models/${model.id}/versions/${baseId}/diff?against=${against}`,
      );
      setDiff(res);
    } finally {
      setDiffing(false);
    }
  };

  const versionLabel = (v: ReferenceModelVersion) =>
    `v${v.version} · ${v.published_at ? new Date(v.published_at).toLocaleDateString(isAr ? "ar" : undefined) : ""}`;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth disableRestoreFocus>
      <DialogTitle>
        {t("rmVersion.title")}
        {model && (
          <Typography variant="body2" color="text.secondary">
            {model.name}
          </Typography>
        )}
      </DialogTitle>
      <DialogContent dividers>
        {!versions && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress />
          </Box>
        )}
        {versions && versions.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            {t("rmVersion.empty")}
          </Typography>
        )}
        {versions && versions.length > 0 && (
          <>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {t("rmVersion.history")}
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75, mb: 2 }}>
              {versions.map((v) => (
                <Paper key={v.id} variant="outlined" sx={{ p: 1, display: "flex", alignItems: "center", gap: 1 }}>
                  <Chip size="small" label={`v${v.version}`} sx={{ direction: "ltr" }} />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography variant="body2" noWrap>
                      {v.change_summary || t("rmVersion.noSummary")}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {v.published_at ? new Date(v.published_at).toLocaleString(isAr ? "ar" : undefined) : ""}
                      {v.published_by_display_name ? ` · ${v.published_by_display_name}` : ""}
                    </Typography>
                  </Box>
                  <Chip size="small" variant="outlined" label={t("rmVersion.items", { count: v.item_count })} />
                </Paper>
              ))}
            </Box>

            <Divider sx={{ my: 1.5 }} />
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {t("rmVersion.compare")}
            </Typography>
            <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap", mb: 2 }}>
              <TextField
                select
                size="small"
                label={t("rmVersion.base")}
                value={baseId}
                onChange={(e) => setBaseId(e.target.value)}
                sx={{ minWidth: 200 }}
              >
                {versions.map((v) => (
                  <MenuItem key={v.id} value={v.id}>
                    {versionLabel(v)}
                  </MenuItem>
                ))}
              </TextField>
              <MaterialSymbol icon={isAr ? "arrow_back" : "arrow_forward"} size={18} />
              <TextField
                select
                size="small"
                label={t("rmVersion.against")}
                value={against}
                onChange={(e) => setAgainst(e.target.value)}
                sx={{ minWidth: 200 }}
              >
                <MenuItem value="current">{t("rmVersion.current")}</MenuItem>
                {versions
                  .filter((v) => v.id !== baseId)
                  .map((v) => (
                    <MenuItem key={v.id} value={v.id}>
                      {versionLabel(v)}
                    </MenuItem>
                  ))}
              </TextField>
              <Button variant="contained" size="small" onClick={runDiff} disabled={diffing || !baseId}>
                {t("rmVersion.runCompare")}
              </Button>
            </Box>

            {diffing && (
              <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
                <CircularProgress size={22} />
              </Box>
            )}
            {diff && <DiffView diff={diff} isAr={isAr} t={t} />}
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("common:actions.close")}</Button>
      </DialogActions>
    </Dialog>
  );
}

function DiffView({
  diff,
  isAr,
  t,
}: {
  diff: ReferenceModelVersionDiff;
  isAr: boolean;
  t: (k: string, o?: Record<string, unknown>) => string;
}) {
  const c = diff.diff.counts;
  const nm = (r: { name: string; name_ar: string | null }) => (isAr && r.name_ar ? r.name_ar : r.name);
  return (
    <Box>
      <Box sx={{ display: "flex", gap: 1, mb: 1.5, flexWrap: "wrap" }}>
        <Chip size="small" color="success" label={t("rmVersion.added", { count: c.added })} />
        <Chip size="small" color="error" label={t("rmVersion.removed", { count: c.removed })} />
        <Chip size="small" color="warning" label={t("rmVersion.changed", { count: c.changed })} />
        <Chip size="small" variant="outlined" label={t("rmVersion.unchanged", { count: c.unchanged })} />
      </Box>
      {c.added + c.removed + c.changed === 0 && (
        <Typography variant="body2" color="text.secondary">
          {t("rmVersion.identical")}
        </Typography>
      )}
      {diff.diff.added.map((r) => (
        <Row key={`a-${r.code}`} icon="add" color="#2e7d32" code={r.code} label={nm(r)} />
      ))}
      {diff.diff.removed.map((r) => (
        <Row key={`r-${r.code}`} icon="remove" color="#d32f2f" code={r.code} label={nm(r)} />
      ))}
      {diff.diff.changed.map((r) => (
        <Row
          key={`c-${r.code}`}
          icon="edit"
          color="#ed6c02"
          code={r.code}
          label={nm(r.after)}
          detail={r.fields.join(", ")}
        />
      ))}
    </Box>
  );
}

function Row({
  icon,
  color,
  code,
  label,
  detail,
}: {
  icon: string;
  color: string;
  code: string;
  label: string;
  detail?: string;
}) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 0.35 }}>
      <MaterialSymbol icon={icon} size={16} color={color} />
      <Chip size="small" variant="outlined" label={code} sx={{ direction: "ltr", fontFamily: "monospace" }} />
      <Typography variant="body2" sx={{ flex: 1, minWidth: 0 }} noWrap>
        {label}
      </Typography>
      {detail && (
        <Typography variant="caption" color="text.secondary">
          {detail}
        </Typography>
      )}
    </Box>
  );
}

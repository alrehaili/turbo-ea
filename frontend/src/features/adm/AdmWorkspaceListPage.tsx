/**
 * ADM Workspace list / dashboard.
 *
 * Route: /ea-delivery/adm
 *
 * Card-per-workspace grid with search + status filter + owner filter.
 * Each card shows SoAW name, workspace status, current active phase, gate
 * state, owner, target date, completion %, and blocked / overdue chips.
 *
 * [FORK FEATURE]
 */

import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Breadcrumbs from "@mui/material/Breadcrumbs";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import InputAdornment from "@mui/material/InputAdornment";
import LinearProgress from "@mui/material/LinearProgress";
import Link from "@mui/material/Link";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "@/components/MaterialSymbol";
import { useAuthContext } from "@/hooks/AuthContext";
import { api } from "@/api/client";
import { PHASE_STATUS_COLORS } from "./admConstants";
import CreateWorkspaceDialog from "./CreateWorkspaceDialog";
import type { AdmWorkspace } from "./types";

const STATUS_OPTIONS = ["all", "active", "draft", "on_hold", "completed", "archived"] as const;

export default function AdmWorkspaceListPage() {
  const { t } = useTranslation(["adm", "nav", "common"]);
  const { user } = useAuthContext();
  const [rows, setRows] = useState<AdmWorkspace[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<(typeof STATUS_OPTIONS)[number]>("all");
  const [createOpen, setCreateOpen] = useState(false);

  const canManage = !!(user?.permissions?.["*"] || user?.permissions?.["adm.manage"]);

  const load = async () => {
    try {
      const data = await api.get<AdmWorkspace[]>("/adm/workspaces");
      setRows(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const filtered = useMemo(() => {
    if (!rows) return [];
    const q = search.trim().toLowerCase();
    return rows.filter((w) => {
      if (status !== "all" && w.status !== status) return false;
      if (q && !w.name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [rows, search, status]);

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
      </Alert>
    );
  }

  if (rows === null) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 10 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 1320, mx: "auto", p: { xs: 1, sm: 2 } }}>
      <Breadcrumbs aria-label={t("breadcrumbs")} separator="›" sx={{ mb: 1 }}>
        <Link component={RouterLink} to="/reports/ea-delivery" underline="hover" color="inherit" variant="body2">
          {t("reports.eaDelivery", { ns: "nav" })}
        </Link>
        <Typography variant="body2" color="text.primary" sx={{ fontWeight: 600 }}>
          {t("nav.workspaces")}
        </Typography>
      </Breadcrumbs>

      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2, flexWrap: "wrap" }}>
        <MaterialSymbol icon="account_tree" size={28} color="#0f7eb5" />
        <Typography variant="h4" sx={{ fontWeight: 800, flex: 1 }}>
          {t("list.title")}
        </Typography>
        {canManage && (
          <Button
            variant="contained"
            startIcon={<MaterialSymbol icon="add" size={18} />}
            onClick={() => setCreateOpen(true)}
          >
            {t("list.newWorkspace")}
          </Button>
        )}
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: 800 }}>
        {t("list.subtitle")}
      </Typography>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "1fr 200px" },
          gap: 1.5,
          mb: 2,
        }}
      >
        <TextField
          size="small"
          placeholder={t("list.search")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <MaterialSymbol icon="search" size={18} />
                </InputAdornment>
              ),
            },
          }}
        />
        <TextField
          select
          size="small"
          label={t("list.filterStatus")}
          value={status}
          onChange={(e) => setStatus(e.target.value as (typeof STATUS_OPTIONS)[number])}
        >
          {STATUS_OPTIONS.map((s) => (
            <MenuItem key={s} value={s}>
              {t(`list.status.${s}`)}
            </MenuItem>
          ))}
        </TextField>
      </Box>

      {filtered.length === 0 ? (
        <Paper variant="outlined" sx={{ p: 4, textAlign: "center", borderRadius: 1 }}>
          <MaterialSymbol icon="inbox" size={32} color="disabled" />
          <Typography sx={{ mt: 1 }}>{t("list.empty")}</Typography>
        </Paper>
      ) : (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)", xl: "repeat(3, 1fr)" },
            gap: 1.5,
          }}
        >
          {filtered.map((w) => (
            <WorkspaceCard key={w.id} workspace={w} />
          ))}
        </Box>
      )}

      <CreateWorkspaceDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(id) => {
          setCreateOpen(false);
          void load();
          window.location.assign(`/ea-delivery/adm/${id}`);
        }}
      />
    </Box>
  );
}

function WorkspaceCard({ workspace }: { workspace: AdmWorkspace }) {
  const { t } = useTranslation("adm");
  const active = workspace.active_phase;
  const accent = active ? PHASE_STATUS_COLORS[active.status] : PHASE_STATUS_COLORS.not_started;
  return (
    <Paper
      variant="outlined"
      component={RouterLink}
      to={`/ea-delivery/adm/${workspace.id}`}
      sx={{
        p: 1.75,
        borderRadius: 1,
        borderLeft: `4px solid ${accent}`,
        textDecoration: "none",
        color: "inherit",
        display: "flex",
        flexDirection: "column",
        gap: 1,
        transition: "box-shadow 120ms, transform 120ms",
        "&:hover": { boxShadow: 3, transform: "translateY(-1px)" },
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <MaterialSymbol icon="account_tree" size={20} color="#0f7eb5" />
        <Typography variant="subtitle1" sx={{ fontWeight: 800, flex: 1, minWidth: 0 }} noWrap>
          {workspace.name}
        </Typography>
        <Chip size="small" label={t(`workspace.status.${workspace.status}`)} />
      </Box>
      <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
        {active && (
          <Chip
            size="small"
            icon={<MaterialSymbol icon="play_arrow" size={12} />}
            label={active.title}
            sx={{ borderColor: `${accent}55`, color: accent, fontWeight: 700 }}
            variant="outlined"
          />
        )}
        {typeof workspace.blocked_count === "number" && workspace.blocked_count > 0 && (
          <Chip
            size="small"
            icon={<MaterialSymbol icon="block" size={12} />}
            label={t("list.blockedCount", { count: workspace.blocked_count })}
            color="error"
            variant="outlined"
          />
        )}
        {typeof workspace.overdue_count === "number" && workspace.overdue_count > 0 && (
          <Chip
            size="small"
            icon={<MaterialSymbol icon="event_busy" size={12} />}
            label={t("list.overdueCount", { count: workspace.overdue_count })}
            color="warning"
            variant="outlined"
          />
        )}
      </Box>
      <Box sx={{ mt: "auto" }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
          <Typography variant="caption" color="text.secondary">
            {t("list.completion")}
          </Typography>
          <Typography variant="caption" sx={{ fontWeight: 800 }}>
            {workspace.completion_pct ?? 0}%
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={workspace.completion_pct ?? 0}
          sx={{
            height: 5,
            borderRadius: 1,
            bgcolor: "action.hover",
            "& .MuiLinearProgress-bar": { bgcolor: accent },
          }}
        />
      </Box>
      {workspace.target_completion && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
          {t("header.target")} {workspace.target_completion}
        </Typography>
      )}
    </Paper>
  );
}

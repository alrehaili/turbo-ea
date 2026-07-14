/**
 * StrategicHouseReport — the NEA "Strategic House" viewpoint (Strategic
 * Alignment, conceptual level): vision as the roof, mission as the band,
 * Pillar cards as columns with their supporting objectives inside (via the
 * Objective → Pillar "supports" relation; legacy pillar-subtype Objectives
 * keep working), unassigned objectives in a base band. Vision/mission are
 * settings (WP6.2's deferred fields), editable in-place by admins.
 *
 * [FORK FEATURE] — noraPlan.md WP6.7.
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
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import CreateCardDialog from "@/components/CreateCardDialog";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import { useAuthContext } from "@/hooks/AuthContext";
import { hasPermission } from "@/components/RequirePermission";
import type { Card } from "@/types";

interface StrategyHouse {
  vision: string;
  mission: string;
}

interface ObjectiveEntry {
  id: string;
  name: string;
}

interface PillarEntry {
  id: string;
  name: string;
  objectives: ObjectiveEntry[];
}

interface CascadeData {
  pillars: PillarEntry[];
  unpillared_objectives: ObjectiveEntry[];
}

const PILLAR_COLOR = "#7b1fa2";

export default function StrategicHouseReport() {
  const { t } = useTranslation(["reports", "common"]);
  const { user } = useAuthContext();
  const canEdit = hasPermission(user?.permissions, "admin.settings");
  const canCreatePillar = hasPermission(user?.permissions, "inventory.create");
  const [createPillarOpen, setCreatePillarOpen] = useState(false);
  const [house, setHouse] = useState<StrategyHouse | null>(null);
  const [cascade, setCascade] = useState<CascadeData | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [editVision, setEditVision] = useState("");
  const [editMission, setEditMission] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [h, c] = await Promise.all([
        api.get<StrategyHouse>("/settings/strategy-house"),
        api.get<CascadeData>("/reports/strategy-cascade"),
      ]);
      setHouse(h);
      setCascade(c);
    } catch (e) {
      setError(e instanceof Error ? e.message : "error");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const saveHouse = async () => {
    setError("");
    try {
      await api.patch("/settings/strategy-house", {
        vision: editVision,
        mission: editMission,
      });
      setEditOpen(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "error");
    }
  };

  if (!house || !cascade) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const pillars = cascade.pillars;
  const unassigned = cascade.unpillared_objectives;

  const objectiveChip = (o: ObjectiveEntry) => (
    <Chip
      key={o.id}
      size="small"
      variant="outlined"
      icon={<MaterialSymbol icon="flag" size={14} />}
      label={o.name}
      component={RouterLink}
      to={`/cards/${o.id}`}
      clickable
      sx={{ maxWidth: "100%" }}
    />
  );

  return (
    <Box sx={{ p: 3, maxWidth: 1100, mx: "auto" }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 0.5 }}>
        <Typography variant="h5" fontWeight={700}>
          {t("strategicHouse.title")}
        </Typography>
        <Box sx={{ flex: 1 }} />
        {canEdit && (
          <Button
            size="small"
            variant="outlined"
            startIcon={<MaterialSymbol icon="edit" size={16} />}
            onClick={() => {
              setEditVision(house.vision);
              setEditMission(house.mission);
              setEditOpen(true);
            }}
          >
            {t("strategicHouse.editVisionMission")}
          </Button>
        )}
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("strategicHouse.subtitle")}
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {/* Roof — vision */}
      <Box
        sx={{
          mx: "auto",
          width: "85%",
          clipPath: "polygon(50% 0, 100% 100%, 0 100%)",
          bgcolor: PILLAR_COLOR,
          color: "#fff",
          pt: 6,
          pb: 2,
          px: 8,
          textAlign: "center",
        }}
      >
        <Typography variant="overline" sx={{ opacity: 0.85 }}>
          {t("strategicHouse.vision")}
        </Typography>
        <Typography variant="subtitle1" fontWeight={700} sx={{ lineHeight: 1.3 }}>
          {house.vision || t("strategicHouse.visionEmpty")}
        </Typography>
      </Box>

      {/* Band — mission */}
      <Paper
        elevation={0}
        sx={{
          mx: "auto",
          width: "85%",
          bgcolor: "action.hover",
          p: 2,
          textAlign: "center",
          borderRadius: 0,
        }}
      >
        <Typography variant="overline" color="text.secondary">
          {t("strategicHouse.mission")}
        </Typography>
        <Typography variant="body1" fontWeight={600}>
          {house.mission || t("strategicHouse.missionEmpty")}
        </Typography>
      </Paper>

      {/* Pillars */}
      <Box
        sx={{
          mx: "auto",
          width: "85%",
          display: "grid",
          gridTemplateColumns: pillars.length
            ? `repeat(${Math.min(pillars.length, 5)}, 1fr)`
            : "1fr",
          gap: 1.5,
          py: 1.5,
        }}
      >
        {pillars.length === 0 ? (
          <Alert
            severity="info"
            action={
              canCreatePillar ? (
                <Button
                  color="inherit"
                  size="small"
                  startIcon={<MaterialSymbol icon="add" size={18} />}
                  onClick={() => setCreatePillarOpen(true)}
                >
                  {t("strategyCascade.addPillar")}
                </Button>
              ) : undefined
            }
          >
            {t("strategicHouse.pillarsEmpty")}
          </Alert>
        ) : (
          pillars.map((p) => (
            <Paper
              key={p.id}
              variant="outlined"
              sx={{
                borderTop: `4px solid ${PILLAR_COLOR}`,
                p: 1.5,
                display: "flex",
                flexDirection: "column",
                gap: 1,
                minHeight: 160,
              }}
            >
              <Typography
                variant="subtitle2"
                fontWeight={700}
                component={RouterLink}
                to={`/cards/${p.id}`}
                sx={{ color: "inherit", textDecoration: "none", "&:hover": { color: PILLAR_COLOR } }}
              >
                {p.name}
              </Typography>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
                {p.objectives.map(objectiveChip)}
              </Box>
            </Paper>
          ))
        )}
      </Box>

      {/* Base — objectives not under a pillar */}
      {unassigned.length > 0 && (
        <Paper
          elevation={0}
          sx={{ mx: "auto", width: "85%", bgcolor: "action.hover", p: 2 }}
        >
          <Typography variant="overline" color="text.secondary" display="block" sx={{ mb: 1 }}>
            {t("strategicHouse.otherObjectives")}
          </Typography>
          <Box sx={{ display: "flex", gap: 0.75, flexWrap: "wrap" }}>
            {unassigned.map(objectiveChip)}
          </Box>
        </Paper>
      )}

      {/* Edit vision/mission */}
      <Dialog open={editOpen} onClose={() => setEditOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{t("strategicHouse.editVisionMission")}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            autoFocus
            label={t("strategicHouse.vision")}
            multiline
            minRows={2}
            value={editVision}
            onChange={(e) => setEditVision(e.target.value)}
          />
          <TextField
            label={t("strategicHouse.mission")}
            multiline
            minRows={2}
            value={editMission}
            onChange={(e) => setEditMission(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={saveHouse}>
            {t("common:actions.save")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* WP100.1: empty-state "Add pillar" — pre-set to the Pillar type.
          CreateCardDialog navigates to the new card on success. */}
      {canCreatePillar && (
        <CreateCardDialog
          open={createPillarOpen}
          onClose={() => setCreatePillarOpen(false)}
          onCreate={async (d) => {
            const card = await api.post<Card>("/cards", d);
            return card.id;
          }}
          initialType="Pillar"
        />
      )}
    </Box>
  );
}

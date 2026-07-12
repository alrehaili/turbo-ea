import { useState, useCallback } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Alert from "@mui/material/Alert";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "@/components/MaterialSymbol";
import CardPicker, { type CardOption } from "@/components/CardPicker";
import { useTypeLabel } from "@/hooks/useResolveLabel";
import { api } from "@/api/client";
import type { Card } from "@/types";

interface SuccessorFieldSectionProps {
  card: Card;
  canEdit: boolean;
  onUpdate: (updates: Partial<Card>) => void;
}

function SuccessorFieldSection({ card, canEdit, onUpdate }: SuccessorFieldSectionProps) {
  const { t } = useTranslation(["cards", "common"]);
  const resolveTypeLabel = useTypeLabel();
  const typeLabel = resolveTypeLabel({ key: card.type } as any) || card.type;

  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<CardOption | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Only show for target-state cards
  if (card.architecture_state !== "target") {
    return null;
  }

  // Map change_type to label
  const getSuccessorLabel = () => {
    switch (card.change_type) {
      case "retire":
        return t("detail.succeeds.retiredBy");
      case "consolidate":
        return t("detail.succeeds.mergedInto");
      case "replace":
        return t("detail.succeeds.replacedBy");
      case "modify":
        return t("detail.succeeds.modifiedAs");
      default:
        return t("detail.succeeds.succeeds");
    }
  };

  const handleOpen = () => {
    setSelected(card.successor_id ? { id: card.successor_id, name: "", type: card.type } : null);
    setError("");
    setOpen(true);
  };

  const handleSave = useCallback(async () => {
    if (!selected) return;
    setLoading(true);
    setError("");
    try {
      await api.patch(`/cards/${card.id}`, {
        successor_id: selected.id,
      });
      onUpdate({ successor_id: selected.id });
      setOpen(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("detail.succeeds.error"));
    } finally {
      setLoading(false);
    }
  }, [selected, card.id, onUpdate, t]);

  const handleClear = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      await api.patch(`/cards/${card.id}`, {
        successor_id: null,
      });
      onUpdate({ successor_id: null });
      setOpen(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t("detail.succeeds.error"));
    } finally {
      setLoading(false);
    }
  }, [card.id, onUpdate, t]);

  return (
    <>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Typography variant="body2" fontWeight={600}>
          {getSuccessorLabel()}
        </Typography>
        {card.successor_id && (
          <Box
            sx={{
              px: 1,
              py: 0.5,
              bgcolor: "action.hover",
              borderRadius: 1,
              display: "flex",
              alignItems: "center",
              gap: 1,
            }}
          >
            <Typography variant="body2">{card.successor_id}</Typography>
            {canEdit && (
              <IconButton
                size="small"
                onClick={() => setSelected(null)}
                title={t("common:actions.clear")}
              >
                <MaterialSymbol icon="close" size={14} />
              </IconButton>
            )}
          </Box>
        )}
        {!card.successor_id && (
          <Typography variant="body2" color="text.secondary">
            {t("detail.succeeds.notSet")}
          </Typography>
        )}
        {canEdit && (
          <Button
            size="small"
            variant="outlined"
            startIcon={<MaterialSymbol icon="edit" size={14} />}
            onClick={handleOpen}
          >
            {t("detail.succeeds.edit")}
          </Button>
        )}
      </Box>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        maxWidth="sm"
        fullWidth
        disableRestoreFocus
      >
        <DialogTitle>{getSuccessorLabel()}</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" onClose={() => setError("")} sx={{ mb: 1, mt: 1 }}>
              {error}
            </Alert>
          )}
          <CardPicker
            types={card.type}
            value={selected}
            onChange={setSelected}
            excludeIds={[card.id]}
            enabled={open}
            fullWidth
            sx={{ mt: 1 }}
            label={t("detail.succeeds.search", { type: typeLabel })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>{t("common:actions.cancel")}</Button>
          {card.successor_id && (
            <Button
              onClick={handleClear}
              disabled={loading}
              color="error"
            >
              {t("common:actions.clear")}
            </Button>
          )}
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={!selected || loading}
          >
            {t("common:actions.save")}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default SuccessorFieldSection;

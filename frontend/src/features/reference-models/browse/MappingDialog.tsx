/**
 * Reference Model mapping dialog (RMPlan Phase 2).
 *
 * Maps an inventory card to a reference-model item (or edits an existing
 * mapping's type / status / rationale / confidence). Card selection uses the
 * shared CardPicker scoped to the model's domain card type. Create mode picks
 * a card; edit mode locks the card and only tunes metadata.
 *
 * [FORK FEATURE] — Reference Models mapping (RMPlan/rmPlan.md).
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import CardPicker, { type CardOption } from "@/components/CardPicker";
import { api, ApiError } from "@/api/client";
import type {
  ReferenceModelMappedCard,
  ReferenceModelMappingStatus,
  ReferenceModelMappingType,
} from "@/types";

const MAPPING_TYPES: ReferenceModelMappingType[] = [
  "primary",
  "secondary",
  "supporting",
  "candidate",
  "historical",
];
const MAPPING_STATUSES: ReferenceModelMappingStatus[] = ["proposed", "confirmed", "rejected"];

interface Props {
  open: boolean;
  itemId: string;
  cardType: string;
  /** Card ids already mapped to this item (hidden from the picker). */
  excludeCardIds: string[];
  /** When set, edit that explicit mapping instead of creating one. */
  editing?: ReferenceModelMappedCard | null;
  onClose: () => void;
  onSaved: () => void;
}

export default function MappingDialog({
  open,
  itemId,
  cardType,
  excludeCardIds,
  editing,
  onClose,
  onSaved,
}: Props) {
  const { t } = useTranslation(["reports", "common"]);
  const isEdit = !!editing?.mapping_id;

  const [card, setCard] = useState<CardOption | null>(null);
  const [mappingType, setMappingType] = useState<ReferenceModelMappingType>("primary");
  const [mappingStatus, setMappingStatus] = useState<ReferenceModelMappingStatus>("confirmed");
  const [rationale, setRationale] = useState("");
  const [confidence, setConfidence] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setError(null);
    setSaving(false);
    if (editing) {
      setCard({ id: editing.id, name: editing.name, type: editing.type });
      setMappingType(editing.mapping_type);
      setMappingStatus(editing.mapping_status ?? "confirmed");
      setRationale(editing.rationale ?? "");
      setConfidence(editing.confidence != null ? String(editing.confidence) : "");
    } else {
      setCard(null);
      setMappingType("primary");
      setMappingStatus("confirmed");
      setRationale("");
      setConfidence("");
    }
  }, [open, editing]);

  const save = async () => {
    if (!isEdit && !card) return;
    setSaving(true);
    setError(null);
    const body: Record<string, unknown> = {
      mapping_type: mappingType,
      mapping_status: mappingStatus,
      rationale: rationale.trim() || null,
      confidence: confidence.trim() === "" ? null : Number(confidence),
    };
    try {
      if (isEdit) {
        await api.patch(`/reference-models/mappings/${editing!.mapping_id}`, body);
      } else {
        await api.post(`/reference-models/items/${itemId}/mappings`, {
          ...body,
          card_id: card!.id,
        });
      }
      onSaved();
      onClose();
    } catch (e) {
      setError(
        e instanceof ApiError && typeof e.detail === "string"
          ? e.detail
          : t("common:errors.generic"),
      );
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth disableRestoreFocus>
      <DialogTitle>{isEdit ? t("rmMap.editTitle") : t("rmMap.addTitle")}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}
          {isEdit ? (
            <Typography variant="body2">
              {t("rmMap.card")}: <strong>{editing!.name}</strong>
            </Typography>
          ) : (
            <CardPicker
              types={cardType}
              value={card}
              onChange={setCard}
              excludeIds={excludeCardIds}
              enabled={open}
              label={t("rmMap.card")}
              autoFocus
            />
          )}
          <TextField
            select
            label={t("rmMap.mappingType")}
            value={mappingType}
            onChange={(e) => setMappingType(e.target.value as ReferenceModelMappingType)}
            size="small"
          >
            {MAPPING_TYPES.map((mt) => (
              <MenuItem key={mt} value={mt}>
                {t(`rmMap.type.${mt}`)}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label={t("rmMap.mappingStatus")}
            value={mappingStatus}
            onChange={(e) => setMappingStatus(e.target.value as ReferenceModelMappingStatus)}
            size="small"
          >
            {MAPPING_STATUSES.map((ms) => (
              <MenuItem key={ms} value={ms}>
                {t(`rmMap.status.${ms}`)}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label={t("rmMap.confidence")}
            value={confidence}
            onChange={(e) => setConfidence(e.target.value.replace(/[^0-9]/g, "").slice(0, 3))}
            size="small"
            inputProps={{ inputMode: "numeric" }}
            helperText={t("rmMap.confidenceHint")}
          />
          <TextField
            label={t("rmMap.rationale")}
            value={rationale}
            onChange={(e) => setRationale(e.target.value)}
            size="small"
            multiline
            minRows={2}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("common:cancel")}</Button>
        <Button variant="contained" onClick={save} disabled={saving || (!isEdit && !card)}>
          {t("common:save")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

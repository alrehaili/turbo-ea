/**
 * Reference Model cross-model relationship dialog (RMPlan §10).
 *
 * Links one reference-model item to another (typically in a *different* model)
 * with a typed relationship — e.g. an ARM application component that
 * `realizes` a BRM capability. The target is chosen by first picking a
 * published domain, then an item within it (reusing `GET /active?domain=`).
 *
 * [FORK FEATURE] — Reference Models relationships (RMPlan/rmPlan.md §10).
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import { api, ApiError } from "@/api/client";
import type {
  ReferenceModelDomain,
  ReferenceModelItem,
  ReferenceModelRelationshipType,
} from "@/types";
import { RM_DOMAIN_META, RM_DOMAIN_ORDER } from "./domainMeta";

const RELATIONSHIP_TYPES: ReferenceModelRelationshipType[] = [
  "supports",
  "consumes",
  "realizes",
  "depends_on",
  "aligns_with",
];

interface Props {
  open: boolean;
  sourceItemId: string;
  /** Item ids to hide from the target picker (the source + already-linked). */
  excludeTargetIds: string[];
  onClose: () => void;
  onSaved: () => void;
}

export default function RelationshipDialog({
  open,
  sourceItemId,
  excludeTargetIds,
  onClose,
  onSaved,
}: Props) {
  const { t } = useTranslation(["reports", "common"]);
  const [publishedDomains, setPublishedDomains] = useState<ReferenceModelDomain[]>([]);
  const [domain, setDomain] = useState<ReferenceModelDomain | "">("");
  const [items, setItems] = useState<ReferenceModelItem[]>([]);
  const [loadingItems, setLoadingItems] = useState(false);
  const [target, setTarget] = useState<ReferenceModelItem | null>(null);
  const [relType, setRelType] = useState<ReferenceModelRelationshipType>("supports");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset on open + load which domains have a published model.
  useEffect(() => {
    if (!open) return;
    setError(null);
    setSaving(false);
    setDomain("");
    setItems([]);
    setTarget(null);
    setRelType("supports");
    setDescription("");
    api
      .get<Record<string, boolean>>("/reference-models/active-summary")
      .then((res) =>
        setPublishedDomains(RM_DOMAIN_ORDER.filter((d) => res[d])),
      )
      .catch(() => setPublishedDomains([]));
  }, [open]);

  // Load the chosen domain's item list.
  useEffect(() => {
    if (!open || !domain) return;
    let cancelled = false;
    setLoadingItems(true);
    setTarget(null);
    api
      .get<{ items: ReferenceModelItem[] }>(`/reference-models/active?domain=${domain}`)
      .then((res) => {
        if (!cancelled) setItems(res.items);
      })
      .catch(() => {
        if (!cancelled) setItems([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingItems(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, domain]);

  const exclude = new Set(excludeTargetIds);
  const options = items.filter((i) => !exclude.has(i.id));

  const save = async () => {
    if (!target) return;
    setSaving(true);
    setError(null);
    try {
      await api.post(`/reference-models/items/${sourceItemId}/relationships`, {
        target_item_id: target.id,
        relationship_type: relType,
        description: description.trim() || null,
      });
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
      <DialogTitle>{t("rmRel.addTitle")}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField
            select
            label={t("rmRel.relType")}
            value={relType}
            onChange={(e) => setRelType(e.target.value as ReferenceModelRelationshipType)}
            size="small"
          >
            {RELATIONSHIP_TYPES.map((rt) => (
              <MenuItem key={rt} value={rt}>
                {t(`rmRel.type.${rt}`)}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label={t("rmRel.targetModel")}
            value={domain}
            onChange={(e) => setDomain(e.target.value as ReferenceModelDomain)}
            size="small"
          >
            {publishedDomains.map((d) => (
              <MenuItem key={d} value={d}>
                {RM_DOMAIN_META[d].code}
              </MenuItem>
            ))}
          </TextField>
          <Autocomplete
            options={options}
            value={target}
            onChange={(_e, v) => setTarget(v)}
            getOptionLabel={(o) => `${o.code} — ${o.name}`}
            isOptionEqualToValue={(a, b) => a.id === b.id}
            disabled={!domain}
            loading={loadingItems}
            size="small"
            renderInput={(params) => (
              <TextField {...params} label={t("rmRel.targetItem")} />
            )}
          />
          <TextField
            label={t("rmRel.description")}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            size="small"
            multiline
            minRows={2}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("common:cancel")}</Button>
        <Button variant="contained" onClick={save} disabled={saving || !target}>
          {t("common:save")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

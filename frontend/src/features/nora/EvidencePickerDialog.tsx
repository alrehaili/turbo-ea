/**
 * EvidencePickerDialog — structured evidence linking for NORA program
 * deliverables (WP3.1). Replaces the free-text-only "add evidence" dialog:
 * the user picks an evidence *kind* (link / card / diagram / SoAW / ADR /
 * saved report) and then the specific entity, and the dialog produces a
 * well-formed evidence item ({kind, ref, label}) with a real in-app path — so
 * evidence links can't drift or 404 the way hand-typed URLs do.
 * [FORK FEATURE] — noraPlan.md WP3.1.
 */
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Autocomplete from "@mui/material/Autocomplete";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import CardPicker, { type CardOption } from "@/components/CardPicker";
import { api } from "@/api/client";
import type { ArchitectureDecision, DiagramSummary, SavedReport, SoAW } from "@/types";

export interface EvidenceValue {
  kind: string;
  ref: string;
  label: string | null;
}

type Kind = "link" | "card" | "diagram" | "soaw" | "adr" | "report";

const KINDS: Kind[] = ["link", "card", "diagram", "soaw", "adr", "report"];

interface Props {
  open: boolean;
  onClose: () => void;
  onAdd: (item: EvidenceValue) => void;
}

interface Picked {
  id: string;
  label: string;
  path: string;
}

export default function EvidencePickerDialog({ open, onClose, onAdd }: Props) {
  const { t } = useTranslation(["nav", "common"]);
  const [kind, setKind] = useState<Kind>("link");

  // Free-text link fields.
  const [linkRef, setLinkRef] = useState("");
  const [linkLabel, setLinkLabel] = useState("");

  // Card picker value.
  const [card, setCard] = useState<CardOption | null>(null);

  // Lists for the entity pickers, loaded lazily per kind.
  const [diagrams, setDiagrams] = useState<DiagramSummary[] | null>(null);
  const [soaws, setSoaws] = useState<SoAW[] | null>(null);
  const [adrs, setAdrs] = useState<ArchitectureDecision[] | null>(null);
  const [reports, setReports] = useState<SavedReport[] | null>(null);
  const [picked, setPicked] = useState<Picked | null>(null);

  // Reset transient state whenever the dialog opens.
  useEffect(() => {
    if (open) {
      setKind("link");
      setLinkRef("");
      setLinkLabel("");
      setCard(null);
      setPicked(null);
    }
  }, [open]);

  // Lazy-load the list for the selected kind.
  useEffect(() => {
    if (!open) return;
    if (kind === "diagram" && diagrams === null) {
      api.get<DiagramSummary[]>("/diagrams").then(setDiagrams).catch(() => setDiagrams([]));
    } else if (kind === "soaw" && soaws === null) {
      api.get<SoAW[]>("/soaw").then(setSoaws).catch(() => setSoaws([]));
    } else if (kind === "adr" && adrs === null) {
      api.get<ArchitectureDecision[]>("/adr").then(setAdrs).catch(() => setAdrs([]));
    } else if (kind === "report" && reports === null) {
      api
        .get<SavedReport[]>("/saved-reports?filter=all")
        .then(setReports)
        .catch(() => setReports([]));
    }
    setPicked(null);
  }, [kind, open, diagrams, soaws, adrs, reports]);

  const options: Picked[] = useMemo(() => {
    if (kind === "diagram") {
      return (diagrams ?? []).map((d) => ({
        id: d.id,
        label: d.name,
        path: `/diagrams/${d.id}`,
      }));
    }
    if (kind === "soaw") {
      return (soaws ?? []).map((s) => ({
        id: s.id,
        label: s.name,
        path: `/ea-delivery/soaw/${s.id}`,
      }));
    }
    if (kind === "adr") {
      return (adrs ?? []).map((a) => ({
        id: a.id,
        label: `${a.reference_number} · ${a.title}`,
        path: `/ea-delivery/adr/${a.id}`,
      }));
    }
    if (kind === "report") {
      return (reports ?? []).map((r) => ({
        id: r.id,
        label: r.name,
        path: `/reports/saved`,
      }));
    }
    return [];
  }, [kind, diagrams, soaws, adrs, reports]);

  const canSave =
    kind === "link"
      ? linkRef.trim().length > 0
      : kind === "card"
        ? card !== null
        : picked !== null;

  const handleSave = () => {
    let item: EvidenceValue | null = null;
    if (kind === "link") {
      item = { kind: "link", ref: linkRef.trim(), label: linkLabel.trim() || null };
    } else if (kind === "card" && card) {
      item = { kind: "card", ref: `/cards/${card.id}`, label: card.name };
    } else if (picked) {
      item = { kind, ref: picked.path, label: picked.label };
    }
    if (item) {
      onAdd(item);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{t("noraProgram.evidencePicker.title", "Add evidence")}</DialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
        <TextField
          select
          label={t("noraProgram.evidencePicker.kind", "Evidence type")}
          value={kind}
          onChange={(e) => setKind(e.target.value as Kind)}
        >
          {KINDS.map((k) => (
            <MenuItem key={k} value={k}>
              {t(`noraProgram.evidencePicker.kinds.${k}`, k)}
            </MenuItem>
          ))}
        </TextField>

        {kind === "link" && (
          <>
            <TextField
              autoFocus
              label={t("noraProgram.evidenceLabel", "Label")}
              value={linkLabel}
              onChange={(e) => setLinkLabel(e.target.value)}
            />
            <TextField
              label={t("noraProgram.evidenceRef", "Reference")}
              placeholder="/reports/gap-analysis · /cards/… · https://…"
              value={linkRef}
              onChange={(e) => setLinkRef(e.target.value)}
            />
          </>
        )}

        {kind === "card" && (
          <CardPicker value={card} onChange={setCard} enabled={open} />
        )}

        {kind !== "link" && kind !== "card" && (
          <Autocomplete
            options={options}
            getOptionLabel={(o) => o.label}
            isOptionEqualToValue={(a, b) => a.id === b.id}
            value={picked}
            onChange={(_, v) => setPicked(v)}
            renderInput={(params) => (
              <TextField
                {...params}
                label={t("noraProgram.evidencePicker.pick", "Select")}
              />
            )}
          />
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("common:actions.cancel")}</Button>
        <Button variant="contained" onClick={handleSave} disabled={!canSave}>
          {t("common:actions.save")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

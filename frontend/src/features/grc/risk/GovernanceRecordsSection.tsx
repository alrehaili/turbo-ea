import { useState } from "react";
import { useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import IconButton from "@mui/material/IconButton";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useAbortableEffect } from "@/hooks/useLatestRequest";
import type { GovernanceInstrument, RiskGovernanceLink } from "@/types";

interface Props {
  riskId: string;
  /** `risks.manage` and the risk is not closed. */
  canManage: boolean;
}

interface RecordOption {
  id: string;
  label: string;
}

const INSTRUMENT_ICON: Record<GovernanceInstrument, string> = {
  adr: "gavel",
  arb: "groups",
  exception: "rule",
};

/**
 * The governance records a risk is explicitly linked to (D-42): ADRs, ARB
 * reviews and technology-standard exceptions. Only such a link makes a risk
 * architecture-related. The server lists only records the reader may see and
 * enforces `risks.manage` plus the record's own visibility on every change;
 * links are added and removed one at a time, so hidden ones are never touched.
 */
export default function GovernanceRecordsSection({ riskId, canManage }: Props) {
  const { t } = useTranslation("grc");
  const navigate = useNavigate();
  const k = (key: string) => `risks.governance.${key}`;
  const [refetchKey, setRefetchKey] = useState(0);
  const { data, error: loadError } = useApiQuery<{ links: RiskGovernanceLink[] }>(
    `/risks/${riskId}/governance-links`,
    { refetchKey },
  );
  const [instrument, setInstrument] = useState<GovernanceInstrument>("adr");
  const [options, setOptions] = useState<RecordOption[]>([]);
  const [error, setError] = useState<string | null>(null);

  // The records of the chosen kind the user may see, loaded for the picker.
  useAbortableEffect(
    async ({ signal, isCurrent }) => {
      if (!canManage) return;
      try {
        let next: RecordOption[] = [];
        if (instrument === "adr") {
          const rows = await api.get<{ id: string; reference_number: string; title: string }[]>(
            "/adr",
            { signal },
          );
          next = rows.map((r) => ({ id: r.id, label: `${r.reference_number} — ${r.title}` }));
        } else if (instrument === "arb") {
          const rows = await api.get<{ id: string; title: string }[]>("/arb", { signal });
          next = rows.map((r) => ({ id: r.id, label: r.title }));
        } else {
          const [rows, standards] = await Promise.all([
            api.get<{ id: string; standard_id: string; card: { name: string } | null; status: string }[]>(
              "/tech-standards/exceptions",
              { signal },
            ),
            api.get<{ id: string; name: string }[]>("/tech-standards", { signal }),
          ]);
          const names = new Map(standards.map((s) => [s.id, s.name]));
          next = rows.map((r) => ({
            id: r.id,
            label: `${names.get(r.standard_id) ?? "—"} · ${r.card?.name ?? "—"} · ${r.status}`,
          }));
        }
        if (isCurrent()) setOptions(next);
      } catch {
        if (isCurrent()) setOptions([]);
      }
    },
    [instrument, canManage],
  );

  const change = async (call: () => Promise<unknown>) => {
    setError(null);
    try {
      await call();
      setRefetchKey((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : t(k("failed")));
    }
  };

  const links = data?.links ?? [];
  const linked = new Set(links.map((l) => `${l.instrument}:${l.record_id}`));

  return (
    <Box data-testid="risk-governance-records">
      <Typography variant="body2" fontWeight={600} color="text.secondary" sx={{ mb: 0.5 }}>
        {t(k("title"))}
      </Typography>
      <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 1 }}>
        {t(k("hint"))}
      </Typography>
      {(loadError || error) && (
        <Alert severity="error" sx={{ mb: 1 }}>
          {error ?? t(k("loadFailed"))}
        </Alert>
      )}
      {links.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {t(k("none"))}
        </Typography>
      ) : (
        <Stack spacing={0.5} sx={{ mb: 1 }}>
          {links.map((l) => (
            <Box key={`${l.instrument}:${l.record_id}`} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <MaterialSymbol icon={INSTRUMENT_ICON[l.instrument]} size={18} />
              <Chip size="small" variant="outlined" label={t(k(`instrument.${l.instrument}`))} />
              <Typography
                variant="body2"
                dir="auto"
                sx={{ cursor: "pointer", flex: 1, minWidth: 0 }}
                noWrap
                onClick={() => navigate(l.path)}
              >
                {l.label}
              </Typography>
              <Chip size="small" label={l.status} />
              {l.approved && <Chip size="small" color="success" label={t(k("approved"))} />}
              {canManage && (
                <Tooltip title={t(k("unlink"))}>
                  <IconButton
                    size="small"
                    aria-label={t(k("unlink"))}
                    onClick={() =>
                      change(() =>
                        api.delete(`/risks/${riskId}/governance-links/${l.instrument}/${l.record_id}`),
                      )
                    }
                  >
                    <MaterialSymbol icon="link_off" size={18} />
                  </IconButton>
                </Tooltip>
              )}
            </Box>
          ))}
        </Stack>
      )}
      {canManage && (
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", maxWidth: 640 }}>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>{t(k("recordType"))}</InputLabel>
            <Select
              label={t(k("recordType"))}
              value={instrument}
              onChange={(e) => setInstrument(e.target.value as GovernanceInstrument)}
            >
              {(["adr", "arb", "exception"] as const).map((i) => (
                <MenuItem key={i} value={i}>
                  {t(k(`instrument.${i}`))}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Autocomplete
            size="small"
            sx={{ flex: 1, minWidth: 240 }}
            options={options.filter((o) => !linked.has(`${instrument}:${o.id}`))}
            getOptionLabel={(o) => o.label}
            value={null}
            onChange={(_, v) => {
              if (v) {
                change(() =>
                  api.post(`/risks/${riskId}/governance-links`, { instrument, record_id: v.id }),
                );
              }
            }}
            renderInput={(p) => <TextField {...p} label={t(k("link"))} />}
          />
        </Box>
      )}
    </Box>
  );
}

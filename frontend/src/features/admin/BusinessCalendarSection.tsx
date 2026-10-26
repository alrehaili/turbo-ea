import { useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "@/api/client";
import MaterialSymbol from "@/components/MaterialSymbol";
import { useAuthContext } from "@/hooks/AuthContext";
import { useAbortableEffect } from "@/hooks/useLatestRequest";
import { usePermissions } from "@/hooks/usePermissions";

/** ISO weekday numbers, listed Sunday first (the Saudi week). */
const WEEKDAYS = [7, 1, 2, 3, 4, 5, 6] as const;

interface Holiday {
  date: string;
  name: string;
}

interface CalendarYear {
  fiscal_year: number;
  starts: string;
  ends: string;
  working_weekdays: number[];
  holidays: Holiday[];
  confirmed: boolean;
  confirmed_at: string | null;
}

interface CalendarList {
  fiscal_year_start: number;
  default_working_weekdays: number[];
  years: CalendarYear[];
}

/**
 * The business calendar (D-28, D-38): per fiscal year, the working week and the
 * official holidays, and its confirmation. Only a confirmed year counts for the
 * working-day figures on the Executive dashboard; changing a confirmed year
 * withdraws its confirmation. Shown to holders of `admin.business_calendar`.
 */
export default function BusinessCalendarSection() {
  const { t } = useTranslation(["admin", "common"]);
  const k = (key: string) => `settings.businessCalendar.${key}`;
  const { user } = useAuthContext();
  const { can } = usePermissions(user);
  const allowed = can("admin.business_calendar");

  const [list, setList] = useState<CalendarList | null>(null);
  const [fy, setFy] = useState<number>(new Date().getFullYear());
  const [week, setWeek] = useState<number[]>([]);
  const [holidays, setHolidays] = useState<Holiday[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useAbortableEffect(
    async ({ signal, isCurrent }) => {
      if (!allowed) return;
      try {
        const r = await api.get<CalendarList>("/business-calendar", { signal });
        if (isCurrent()) setList(r);
      } catch {
        if (isCurrent()) setList({ fiscal_year_start: 1, default_working_weekdays: [7, 1, 2, 3, 4], years: [] });
      }
    },
    [allowed, reload],
  );

  const current = list?.years.find((y) => y.fiscal_year === fy) ?? null;

  // Load the selected year into the form whenever the year or the data changes.
  const [loadedKey, setLoadedKey] = useState("");
  const key = `${fy}:${current ? JSON.stringify(current) : "new"}:${list ? "ready" : "loading"}`;
  if (list && key !== loadedKey) {
    setLoadedKey(key);
    setWeek(current ? current.working_weekdays : list.default_working_weekdays);
    setHolidays(current ? current.holidays : []);
  }

  if (!allowed) return null;

  const years = Array.from(
    new Set([...(list?.years.map((y) => y.fiscal_year) ?? []), fy, new Date().getFullYear()]),
  ).sort((a, b) => a - b);

  const run = async (call: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await call();
      setReload((n) => n + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common:errors.generic"));
    } finally {
      setBusy(false);
    }
  };

  const save = () =>
    run(() =>
      api.put(`/business-calendar/${fy}`, {
        working_weekdays: week,
        holidays: holidays.filter((h) => h.date || h.name.trim()),
      }),
    );

  const toggleDay = (day: number) =>
    setWeek((w) => (w.includes(day) ? w.filter((d) => d !== day) : [...w, day]));

  return (
    <Paper sx={{ p: 3, mb: 3 }} data-testid="business-calendar">
      <Box sx={{ display: "flex", alignItems: "center", mb: 2, gap: 1 }}>
        <MaterialSymbol icon="event_available" size={22} color="#555" />
        <Typography variant="h6" fontWeight={600}>
          {t(k("title"))}
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t(k("description"))}
      </Typography>

      <Box sx={{ display: "flex", gap: 2, alignItems: "center", flexWrap: "wrap", mb: 2 }}>
        <TextField
          select
          size="small"
          label={t(k("fiscalYear"))}
          value={fy}
          onChange={(e) => setFy(Number(e.target.value))}
          sx={{ minWidth: 160 }}
        >
          {[...years, Math.max(...years) + 1].map((y) => (
            <MenuItem key={y} value={y}>
              FY{y}
            </MenuItem>
          ))}
        </TextField>
        {current ? (
          <Chip
            size="small"
            color={current.confirmed ? "success" : "warning"}
            label={t(k(current.confirmed ? "confirmed" : "unconfirmed"))}
            data-testid="calendar-status"
          />
        ) : (
          <Chip size="small" label={t(k("notMaintained"))} data-testid="calendar-status" />
        )}
        {current && (
          <Typography variant="caption" color="text.secondary">
            {t(k("range"), { starts: current.starts, ends: current.ends })}
          </Typography>
        )}
      </Box>

      <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
        {t(k("workingWeek"))}
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", mb: 2 }}>
        {WEEKDAYS.map((d) => (
          <FormControlLabel
            key={d}
            control={<Checkbox size="small" checked={week.includes(d)} onChange={() => toggleDay(d)} />}
            label={t(k(`weekday.${d}`))}
          />
        ))}
      </Box>

      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        {t(k("holidays"))}
      </Typography>
      {holidays.map((h, i) => (
        <Box key={i} sx={{ display: "flex", gap: 1, alignItems: "center", mb: 1 }}>
          <TextField
            size="small"
            type="date"
            label={t(k("holidayDate"))}
            value={h.date}
            onChange={(e) =>
              setHolidays((hs) => hs.map((x, j) => (j === i ? { ...x, date: e.target.value } : x)))
            }
          />
          <TextField
            size="small"
            label={t(k("holidayName"))}
            value={h.name}
            onChange={(e) =>
              setHolidays((hs) => hs.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))
            }
            inputProps={{ maxLength: 200 }}
            sx={{ flex: 1 }}
          />
          <IconButton
            size="small"
            aria-label={t(k("removeHoliday"))}
            onClick={() => setHolidays((hs) => hs.filter((_, j) => j !== i))}
          >
            <MaterialSymbol icon="delete" size={18} />
          </IconButton>
        </Box>
      ))}
      <Button
        size="small"
        startIcon={<MaterialSymbol icon="add" size={18} />}
        onClick={() => setHolidays((hs) => [...hs, { date: "", name: "" }])}
        sx={{ mb: 2 }}
      >
        {t(k("addHoliday"))}
      </Button>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {current?.confirmed && (
        <Alert severity="info" sx={{ mb: 2 }}>
          {t(k("editWithdrawsConfirmation"))}
        </Alert>
      )}
      <Box sx={{ display: "flex", gap: 1 }}>
        <Button variant="contained" disabled={busy || week.length === 0} onClick={save}>
          {t(k("save"))}
        </Button>
        {current && !current.confirmed && (
          <Button
            variant="outlined"
            color="success"
            disabled={busy}
            onClick={() => run(() => api.post(`/business-calendar/${fy}/confirm`, {}))}
          >
            {t(k("confirm"))}
          </Button>
        )}
        {current?.confirmed && (
          <Button
            variant="outlined"
            color="inherit"
            disabled={busy}
            onClick={() => run(() => api.post(`/business-calendar/${fy}/unconfirm`, {}))}
          >
            {t(k("unconfirm"))}
          </Button>
        )}
      </Box>
    </Paper>
  );
}

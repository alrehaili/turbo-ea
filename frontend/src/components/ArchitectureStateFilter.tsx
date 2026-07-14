import { useCallback, useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import FormControlLabel from "@mui/material/FormControlLabel";
import Checkbox from "@mui/material/Checkbox";
import Typography from "@mui/material/Typography";
import Tooltip from "@mui/material/Tooltip";

const ARCHITECTURE_STATES = [
  { key: "current", label: "common:architectureState.current", color: "#2196f3" },
  { key: "transition", label: "common:architectureState.transition", color: "#ffc107" },
  { key: "target", label: "common:architectureState.target", color: "#4caf50" },
];

interface ArchitectureStateFilterProps {
  onStateChange: (states: string[]) => void;
  storageKey?: string;
}

export default function ArchitectureStateFilter({
  onStateChange,
  storageKey = "report_architecture_states",
}: ArchitectureStateFilterProps) {
  const { t } = useTranslation("common");
  const [selectedStates, setSelectedStates] = useState<string[]>(["current", "transition", "target"]);

  // Load from sessionStorage on mount
  useEffect(() => {
    const stored = sessionStorage.getItem(storageKey);
    if (stored) {
      try {
        const states = JSON.parse(stored);
        setSelectedStates(states);
        onStateChange(states);
      } catch {
        // Invalid JSON, use defaults
        sessionStorage.setItem(storageKey, JSON.stringify(["current", "transition", "target"]));
      }
    }
  }, [storageKey]);

  const handleToggle = useCallback(
    (state: string) => {
      const newStates = selectedStates.includes(state)
        ? selectedStates.filter((s) => s !== state)
        : [...selectedStates, state];

      setSelectedStates(newStates);
      sessionStorage.setItem(storageKey, JSON.stringify(newStates));
      onStateChange(newStates);
    },
    [selectedStates, storageKey, onStateChange]
  );

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
      <Typography variant="body2" sx={{ fontWeight: 500 }}>
        {t("labels.show")}:
      </Typography>
      <Box sx={{ display: "flex", gap: 1 }}>
        {ARCHITECTURE_STATES.map((state) => (
          <Tooltip key={state.key} title={t(state.label)}>
            <FormControlLabel
              control={
                <Checkbox
                  size="small"
                  checked={selectedStates.includes(state.key)}
                  onChange={() => handleToggle(state.key)}
                  sx={{
                    color: state.color,
                    "&.Mui-checked": {
                      color: state.color,
                    },
                  }}
                />
              }
              label={
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 0.5,
                    fontSize: "0.875rem",
                  }}
                >
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      bgcolor: state.color,
                    }}
                  />
                  {t(state.label)}
                </Box>
              }
              sx={{ m: 0 }}
            />
          </Tooltip>
        ))}
      </Box>
    </Box>
  );
}

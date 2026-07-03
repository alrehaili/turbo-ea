/**
 * ApprovalStepsStrip — compact stepper showing a card's multi-step review
 * chain (NORA stage gates). Rendered under the card-detail header while the
 * card is IN_REVIEW (and after, until reset).
 *
 * [FORK FEATURE] — noraPlan.md WP2.2.
 */
import { useCallback, useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import { api } from "@/api/client";
import MaterialSymbol from "./MaterialSymbol";
import { STATUS_COLORS } from "@/theme/tokens";

export interface ApprovalStepInfo {
  id: string;
  step_no: number;
  required_role_key: string;
  status: "pending" | "approved" | "rejected";
  actor_display_name: string | null;
  comment: string | null;
  acted_at: string | null;
}

interface StepsResponse {
  governance_enabled: boolean;
  chain: string[];
  steps: ApprovalStepInfo[];
}

const STEP_ICON: Record<string, { icon: string; color: string }> = {
  pending: { icon: "radio_button_unchecked", color: STATUS_COLORS.neutral },
  approved: { icon: "check_circle", color: STATUS_COLORS.success },
  rejected: { icon: "cancel", color: STATUS_COLORS.error },
};

export default function ApprovalStepsStrip({
  cardId,
  refreshKey,
}: {
  cardId: string;
  refreshKey?: unknown;
}) {
  const { t } = useTranslation("cards");
  const [steps, setSteps] = useState<ApprovalStepInfo[] | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await api.get<StepsResponse>(`/cards/${cardId}/approval-steps`);
      setSteps(res.steps);
    } catch {
      setSteps(null);
    }
  }, [cardId]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  if (!steps || steps.length === 0) return null;

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap", mt: 1 }}>
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
        {t("detail.reviewChain")}
      </Typography>
      {steps.map((step) => {
        const cfg = STEP_ICON[step.status] ?? STEP_ICON.pending;
        const tooltip = [
          step.actor_display_name,
          step.acted_at ? new Date(step.acted_at).toLocaleString() : null,
          step.comment,
        ]
          .filter(Boolean)
          .join(" — ");
        return (
          <Tooltip key={step.id} title={tooltip} disableHoverListener={!tooltip}>
            <Chip
              size="small"
              variant="outlined"
              icon={<MaterialSymbol icon={cfg.icon} size={16} color={cfg.color} />}
              label={`${step.step_no + 1}. ${step.required_role_key}`}
              sx={{ borderColor: cfg.color }}
            />
          </Tooltip>
        );
      })}
    </Box>
  );
}

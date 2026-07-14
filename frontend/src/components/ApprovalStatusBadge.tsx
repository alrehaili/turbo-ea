import { useState } from "react";
import Chip from "@mui/material/Chip";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "./MaterialSymbol";
import { STATUS_COLORS } from "@/theme/tokens";

export type ApprovalAction = "submit" | "approve" | "reject" | "reset";

interface Props {
  status: string;
  size?: "small" | "medium";
  canChange?: boolean;
  onAction?: (action: ApprovalAction) => void;
  /** Multi-step review mode (NORA stage gates — [FORK] WP2.2): drafts are
   * submitted for review instead of approved directly; approve/reject decide
   * the current chain step. */
  governanceEnabled?: boolean;
}

const STATUS_CONFIG: Record<
  string,
  { color: "default" | "success" | "warning" | "error" | "info"; icon: string }
> = {
  DRAFT: { color: "default", icon: "edit_note" },
  IN_REVIEW: { color: "info", icon: "hourglass_top" },
  APPROVED: { color: "success", icon: "verified" },
  BROKEN: { color: "warning", icon: "warning" },
  REJECTED: { color: "error", icon: "cancel" },
};

export default function ApprovalStatusBadge({
  status,
  size = "small",
  canChange,
  onAction,
  governanceEnabled,
}: Props) {
  const { t } = useTranslation("common");
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const cfg = STATUS_CONFIG[status];
  if (!cfg) return null;

  const interactive = canChange && onAction;

  const item = (
    action: ApprovalAction,
    icon: string,
    color: string,
    label: string,
    disabled: boolean,
  ) => (
    <MenuItem
      key={action}
      onClick={() => {
        onAction?.(action);
        setAnchorEl(null);
      }}
      disabled={disabled}
    >
      <MaterialSymbol icon={icon} size={18} color={color} />
      <Typography sx={{ ml: 1 }}>{label}</Typography>
    </MenuItem>
  );

  const menuItems = governanceEnabled
    ? [
        item(
          "submit",
          "send",
          STATUS_COLORS.info ?? STATUS_COLORS.neutral,
          t("actions.submitForReview"),
          status === "IN_REVIEW" || status === "APPROVED",
        ),
        item(
          "approve",
          "verified",
          STATUS_COLORS.success,
          t("actions.approveStep"),
          status !== "IN_REVIEW",
        ),
        item("reject", "cancel", STATUS_COLORS.error, t("actions.reject"), status !== "IN_REVIEW"),
        item(
          "reset",
          "restart_alt",
          STATUS_COLORS.neutral,
          t("actions.resetToDraft"),
          status === "DRAFT",
        ),
      ]
    : [
        item(
          "approve",
          "verified",
          STATUS_COLORS.success,
          t("actions.approve"),
          status === "APPROVED",
        ),
        item("reject", "cancel", STATUS_COLORS.error, t("actions.reject"), status === "REJECTED"),
        item(
          "reset",
          "restart_alt",
          STATUS_COLORS.neutral,
          t("actions.resetToDraft"),
          status === "DRAFT",
        ),
      ];

  return (
    <>
      <Chip
        size={size}
        label={t(`status.${status.toLowerCase()}`)}
        color={cfg.color}
        variant="outlined"
        icon={<MaterialSymbol icon={cfg.icon} size={16} />}
        deleteIcon={
          interactive ? (
            <MaterialSymbol icon="arrow_drop_down" size={18} />
          ) : undefined
        }
        onDelete={interactive ? (e) => setAnchorEl(e.currentTarget.closest(".MuiChip-root")) : undefined}
        onClick={interactive ? (e) => setAnchorEl(e.currentTarget) : undefined}
        sx={interactive ? { cursor: "pointer" } : undefined}
      />
      {interactive && (
        <Menu anchorEl={anchorEl} open={!!anchorEl} onClose={() => setAnchorEl(null)}>
          {menuItems}
        </Menu>
      )}
    </>
  );
}

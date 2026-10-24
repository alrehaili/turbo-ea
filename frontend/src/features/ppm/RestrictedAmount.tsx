import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import type { TypographyProps } from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "@/components/MaterialSymbol";
import { STATUS_COLORS } from "@/theme/tokens";

/**
 * Stands in for a money figure the caller may not see (the API returns
 * `null` without `costs.view` or a stakeholder role on the initiative). It is
 * never rendered as zero: a withheld amount and a real 0 must look different.
 */
export default function RestrictedAmount({
  variant = "body2",
}: {
  variant?: TypographyProps["variant"];
}) {
  const { t } = useTranslation("ppm");
  return (
    <Tooltip title={t("costsRestrictedHint")}>
      <Box
        component="span"
        data-testid="restricted-amount"
        sx={{ display: "inline-flex", alignItems: "center", gap: 0.5 }}
      >
        <MaterialSymbol icon="lock" size={14} color={STATUS_COLORS.neutral} />
        <Typography component="span" variant={variant} color="text.secondary">
          {t("costsRestricted")}
        </Typography>
      </Box>
    </Tooltip>
  );
}

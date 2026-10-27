import { useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { useApiQuery } from "@/hooks/useApiQuery";
import type { LinkedRisk } from "@/types";

interface Props {
  kind: "adr" | "arb";
  recordId: string;
}

/**
 * Read-only Linked risks on an ADR or an ARB review (D-42.9): the risks
 * explicitly linked to this record. Needs `risks.view`; without it (or when the
 * record is hidden) the request is refused and nothing is shown. Links are
 * managed from the risk.
 */
export default function LinkedRisksList({ kind, recordId }: Props) {
  const { t } = useTranslation("grc");
  const navigate = useNavigate();
  const { data, error } = useApiQuery<{ risks: LinkedRisk[] }>(`/${kind}/${recordId}/risks`);
  if (error || !data) return null;
  return (
    <Box data-testid="linked-risks">
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
        <MaterialSymbol icon="warning" size={20} />
        <Typography variant="subtitle2" fontWeight={700}>
          {t("risks.governance.linkedRisks", { count: data.risks.length })}
        </Typography>
      </Box>
      {data.risks.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          {t("risks.governance.noLinkedRisks")}
        </Typography>
      ) : (
        data.risks.map((r) => (
          <Box key={r.id} sx={{ display: "flex", alignItems: "center", gap: 1, py: 0.25, flexWrap: "wrap" }}>
            <Chip
              size="small"
              variant="outlined"
              label={r.reference}
              onClick={() => navigate(r.path)}
              sx={{ fontFamily: "monospace", cursor: "pointer" }}
            />
            <Typography variant="body2" dir="auto" sx={{ flex: 1, minWidth: 0 }}>
              {r.title}
            </Typography>
            <Chip size="small" label={r.level} />
            <Chip size="small" variant="outlined" label={r.status} />
            {r.escalated && <Chip size="small" color="error" label={t("risks.governance.escalated")} />}
          </Box>
        ))
      )}
    </Box>
  );
}

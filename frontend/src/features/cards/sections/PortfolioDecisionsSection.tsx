import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import { useCurrency } from "@/hooks/useCurrency";
import { SEVERITY_COLORS, STATUS_COLORS } from "@/theme/tokens";

/**
 * Portfolio Decisions section on the card detail page.
 *
 * Surfaces every ``AssessmentDecision`` recorded against this card (across
 * every rationalization assessment / board it appears in) so a stakeholder
 * visiting the Application card sees the board's verdict — including the
 * rationale — without having to remember which assessment it's in.
 *
 * Renders nothing when the card has no decisions, which is the common case
 * for cards that aren't applications or haven't been reviewed yet.
 */

type TimeDecision = "undecided" | "tolerate" | "invest" | "migrate" | "eliminate";

interface CardBrief {
  id: string;
  name: string;
  type: string;
}

interface Decision {
  id: string;
  card: CardBrief | null;
  time_decision: TimeDecision;
  successor: CardBrief | null;
  initiative: CardBrief | null;
  annual_cost: number | null;
  planned_savings: number | null;
  rationale: string | null;
  risk_note: string | null;
  notes: string | null;
  progress: number;
  assessment: {
    id: string;
    name: string;
    status: string;
  };
}

const DECISION_ACCENT: Record<TimeDecision, string> = {
  undecided: STATUS_COLORS.neutral,
  tolerate: STATUS_COLORS.info,
  invest: STATUS_COLORS.success,
  migrate: SEVERITY_COLORS.medium,
  eliminate: STATUS_COLORS.error,
};

const DECISION_ICON: Record<TimeDecision, string> = {
  undecided: "help",
  tolerate: "check_circle",
  invest: "trending_up",
  migrate: "swap_horiz",
  eliminate: "block",
};

interface Props {
  cardId: string;
}

export default function PortfolioDecisionsSection({ cardId }: Props) {
  const { t } = useTranslation(["cards", "reports", "common"]);
  const { fmtShort } = useCurrency();
  const [decisions, setDecisions] = useState<Decision[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<Decision[]>(`/rationalization/cards/${cardId}/decisions`)
      .then((rows) => {
        if (!cancelled) setDecisions(rows);
      })
      .catch(() => {
        // 403 (no permission), 404, or backend down — hide the section silently.
        if (!cancelled) setDecisions([]);
      });
    return () => {
      cancelled = true;
    };
  }, [cardId]);

  if (decisions === null || decisions.length === 0) return null;

  return (
    <Accordion defaultExpanded disableGutters sx={{ "&:before": { display: "none" } }}>
      <AccordionSummary
        expandIcon={<MaterialSymbol icon="expand_more" size={20} />}
        sx={{ minHeight: 48 }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <MaterialSymbol icon="how_to_vote" size={20} color="#0f7eb5" />
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            {t("portfolioDecisions.title", { ns: "cards" })}
          </Typography>
          <Chip size="small" label={decisions.length} sx={{ ml: 1 }} />
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          {decisions.map((d) => (
            <Paper
              key={d.id}
              variant="outlined"
              sx={{
                p: 1.75,
                borderRadius: 1,
                borderLeft: `3px solid ${DECISION_ACCENT[d.time_decision]}`,
              }}
            >
              {/* Header: verdict + successor + assessment link */}
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  mb: d.rationale ? 1.25 : 1,
                  flexWrap: "wrap",
                }}
              >
                <Chip
                  size="small"
                  icon={
                    <Box sx={{ display: "flex", color: "#fff" }}>
                      <MaterialSymbol
                        icon={DECISION_ICON[d.time_decision]}
                        size={14}
                        color="inherit"
                      />
                    </Box>
                  }
                  label={t(`rationalization.decision.${d.time_decision}`, { ns: "reports" })}
                  sx={{
                    bgcolor: DECISION_ACCENT[d.time_decision],
                    color: "#fff",
                    fontWeight: 700,
                    "& .MuiChip-icon": { color: "#fff" },
                  }}
                />
                {d.successor && (
                  <>
                    <MaterialSymbol icon="arrow_forward" size={16} color="disabled" />
                    <Chip
                      size="small"
                      icon={<MaterialSymbol icon="apps" size={14} />}
                      label={d.successor.name}
                      component={RouterLink}
                      to={`/cards/${d.successor.id}`}
                      clickable
                      variant="outlined"
                    />
                  </>
                )}
                <Box sx={{ flex: 1 }} />
                <Link
                  component={RouterLink}
                  to={`/rationalization?assessment=${d.assessment.id}`}
                  underline="hover"
                  variant="caption"
                  sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
                >
                  {d.assessment.name}
                  <MaterialSymbol icon="open_in_new" size={12} />
                </Link>
              </Box>

              {/* Rationale — the "why" front and center */}
              {d.rationale ? (
                <Box sx={{ mb: (d.risk_note || d.notes) ? 1.25 : 0 }}>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ fontWeight: 700, letterSpacing: 0.5, display: "block", mb: 0.25 }}
                  >
                    {t("portfolioDecisions.rationale", { ns: "cards" })}
                  </Typography>
                  <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                    {d.rationale}
                  </Typography>
                </Box>
              ) : (
                <Typography
                  variant="caption"
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 0.5,
                    color: "warning.main",
                    mb: 1,
                  }}
                >
                  <MaterialSymbol icon="report" size={14} color="inherit" />
                  {t("portfolioDecisions.rationaleMissing", { ns: "cards" })}
                </Typography>
              )}

              {/* Risk & execution notes */}
              {(d.risk_note || d.notes) && (
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: {
                      xs: "1fr",
                      sm: d.risk_note && d.notes ? "1fr 1fr" : "1fr",
                    },
                    gap: 1.5,
                    mb: 1.25,
                  }}
                >
                  {d.risk_note && (
                    <Box>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ fontWeight: 700, letterSpacing: 0.5, display: "block", mb: 0.25 }}
                      >
                        {t("portfolioDecisions.riskNote", { ns: "cards" })}
                      </Typography>
                      <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                        {d.risk_note}
                      </Typography>
                    </Box>
                  )}
                  {d.notes && (
                    <Box>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ fontWeight: 700, letterSpacing: 0.5, display: "block", mb: 0.25 }}
                      >
                        {t("portfolioDecisions.notes", { ns: "cards" })}
                      </Typography>
                      <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                        {d.notes}
                      </Typography>
                    </Box>
                  )}
                </Box>
              )}

              {/* Numbers + progress footer */}
              <Box sx={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
                {d.annual_cost != null && (
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      {t("rationalization.colAnnualCost", { ns: "reports" })}
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 700 }}>
                      {fmtShort(d.annual_cost)}
                    </Typography>
                  </Box>
                )}
                {d.planned_savings != null && d.planned_savings > 0 && (
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      {t("rationalization.colSavings", { ns: "reports" })}
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 700, color: STATUS_COLORS.success }}>
                      {fmtShort(d.planned_savings)}
                    </Typography>
                  </Box>
                )}
                <Box sx={{ flex: 1, minWidth: 140 }}>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      mb: 0.25,
                    }}
                  >
                    <Typography variant="caption" color="text.secondary">
                      {t("rationalization.colProgress", { ns: "reports" })}
                    </Typography>
                    <Typography variant="caption" sx={{ fontWeight: 700 }}>
                      {d.progress}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={Math.max(0, Math.min(100, d.progress))}
                    sx={{
                      height: 5,
                      borderRadius: 1,
                      bgcolor: "action.hover",
                      "& .MuiLinearProgress-bar": {
                        bgcolor: DECISION_ACCENT[d.time_decision],
                      },
                    }}
                  />
                </Box>
              </Box>
            </Paper>
          ))}
        </Box>
      </AccordionDetails>
    </Accordion>
  );
}

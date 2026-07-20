/**
 * Reference Models landing page (RMPlan Phase 1, page 1).
 *
 * One entry page listing the published reference model of every NEA domain
 * with its key metrics — item count, mapped inventory, coverage — and the
 * Open / Manage actions. Domains without a published model show an empty
 * card pointing managers at the management console.
 *
 * [FORK FEATURE] — Reference Models browse (RMPlan/rmPlan.md).
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { hasPermission } from "@/components/RequirePermission";
import { api } from "@/api/client";
import { useAuthContext } from "@/hooks/AuthContext";
import type { ReferenceModelOverviewEntry } from "@/types";
import { RM_DOMAIN_META, RM_DOMAIN_ORDER } from "./domainMeta";

const STATUS_COLOR: Record<string, "default" | "success" | "warning"> = {
  draft: "default",
  published: "success",
  archived: "warning",
};

export default function ReferenceModelsLanding() {
  const { t, i18n } = useTranslation(["reports", "nav", "common"]);
  const navigate = useNavigate();
  const { user } = useAuthContext();
  const canManage = hasPermission(user?.permissions, "reference_models.manage");
  const isAr = i18n.language === "ar";

  const [entries, setEntries] = useState<ReferenceModelOverviewEntry[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .get<{ models: ReferenceModelOverviewEntry[] }>("/reference-models/overview")
      .then((res) => {
        if (!cancelled) setEntries(res.models);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const byDomain = new Map((entries ?? []).map((e) => [e.domain, e]));

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 0.5 }}>
        <Typography variant="h5" fontWeight={700}>
          {t("rmBrowse.title")}
        </Typography>
        {canManage && (
          <Button
            variant="outlined"
            size="small"
            startIcon={<MaterialSymbol icon="settings" size={18} />}
            onClick={() => navigate("/reference-models/manage")}
          >
            {t("rmBrowse.manage")}
          </Button>
        )}
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("rmBrowse.subtitle")}
      </Typography>

      {error && <Alert severity="error">{t("common:errors.generic")}</Alert>}
      {!entries && !error && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      )}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "1fr 1fr 1fr" },
          gap: 2,
        }}
      >
        {entries &&
          RM_DOMAIN_ORDER.map((domain) => {
            const meta = RM_DOMAIN_META[domain];
            const entry = byDomain.get(domain);
            const model = entry?.model ?? null;
            const itemCount = model?.item_count ?? 0;
            const covered = entry?.covered_items ?? 0;
            const coverage = itemCount > 0 ? Math.round((covered / itemCount) * 100) : 0;
            const name = model ? (isAr && model.name_ar ? model.name_ar : model.name) : null;
            return (
              <Paper
                key={domain}
                variant="outlined"
                sx={{
                  p: 2,
                  display: "flex",
                  flexDirection: "column",
                  gap: 1.5,
                  borderTop: `3px solid ${meta.color}`,
                }}
              >
                <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                  <Avatar sx={{ bgcolor: meta.color, width: 40, height: 40 }}>
                    <MaterialSymbol icon={meta.icon} size={22} />
                  </Avatar>
                  <Box sx={{ minWidth: 0 }}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Typography component="span" dir="ltr" sx={{ fontWeight: 700 }}>
                        {meta.code}
                      </Typography>
                      {model && (
                        <Chip
                          size="small"
                          label={t(`rmLibrary.status.${model.status}`)}
                          color={STATUS_COLOR[model.status] ?? "default"}
                        />
                      )}
                    </Box>
                    <Typography variant="body2" color="text.secondary" noWrap>
                      {t(`nav:noraProgram.domain.${domain}`)}
                    </Typography>
                  </Box>
                </Box>

                {model ? (
                  <>
                    <Typography variant="subtitle2" sx={{ minHeight: 40 }}>
                      {name}
                      <Typography component="span" variant="caption" color="text.secondary" dir="ltr" sx={{ mx: 0.75 }}>
                        v{model.version}
                      </Typography>
                    </Typography>
                    <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                      <Metric label={t("rmBrowse.items")} value={itemCount} />
                      <Metric label={t("rmBrowse.mappedCards")} value={entry?.mapped_cards ?? 0} />
                      <Metric label={t("rmBrowse.coverage")} value={`${coverage}%`} />
                      <Metric label={t("rmBrowse.uncoded")} value={entry?.uncoded_cards ?? 0} />
                    </Box>
                    <Box sx={{ display: "flex", gap: 1, mt: "auto" }}>
                      <Button
                        size="small"
                        variant="contained"
                        onClick={() => navigate(`/reference-models/${domain}`)}
                      >
                        {t("rmBrowse.openModel")}
                      </Button>
                    </Box>
                  </>
                ) : (
                  <>
                    <Typography variant="body2" color="text.secondary" sx={{ minHeight: 40 }}>
                      {t("rmBrowse.noPublished")}
                    </Typography>
                    {canManage && (
                      <Box sx={{ mt: "auto" }}>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => navigate("/reference-models/manage")}
                        >
                          {t("rmBrowse.manage")}
                        </Button>
                      </Box>
                    )}
                  </>
                )}
              </Paper>
            );
          })}
      </Box>
    </Box>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <Box>
      <Typography variant="h6" component="div" sx={{ lineHeight: 1.2 }}>
        {value}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
    </Box>
  );
}

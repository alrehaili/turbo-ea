import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import MuiCard from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import { api } from "@/api/client";
import MaterialSymbol from "@/components/MaterialSymbol";
import { hasPermission } from "@/components/RequirePermission";
import StandardsAdmin from "@/features/admin/StandardsAdmin";
import { useAuthContext } from "@/hooks/AuthContext";
import { surface } from "@/theme/tokens";
import type { EAPrinciple, Standard } from "@/types";
import CatalogMeta from "./CatalogMeta";

export default function StandardsPanel() {
  const { user } = useAuthContext();
  // Admins get the full create/edit/delete UI (same component as
  // Admin › Metamodel › Standards); everyone else gets a read-only view.
  if (hasPermission(user?.permissions, "admin.metamodel")) {
    return <StandardsAdmin />;
  }
  return <ReadOnlyStandards />;
}

function ReadOnlyStandards() {
  const { t } = useTranslation("grc");
  const [loading, setLoading] = useState(true);
  const [standards, setStandards] = useState<Standard[]>([]);
  const [principles, setPrinciples] = useState<EAPrinciple[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [stds, prins] = await Promise.all([
          api.get<Standard[]>("/metamodel/standards"),
          api.get<EAPrinciple[]>("/metamodel/principles"),
        ]);
        if (!cancelled) {
          setStandards(
            stds.filter((s) => s.is_active).sort((a, b) => a.sort_order - b.sort_order),
          );
          setPrinciples(prins);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const principleTitle = (id: string) => principles.find((p) => p.id === id)?.title ?? id;

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (standards.length === 0) {
    return (
      <Box
        sx={{
          py: 6,
          textAlign: "center",
          border: "1px dashed",
          borderColor: "divider",
          borderRadius: 2,
        }}
      >
        <MaterialSymbol icon="rule" size={40} color="#bbb" />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {t("governance.standards.empty")}
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
      <Typography variant="h6" fontWeight={600}>
        {t("governance.standards.title")}
      </Typography>
      {standards.map((s, idx) => (
        <MuiCard key={s.id} variant="outlined">
          <CardContent sx={{ py: 2, "&:last-child": { pb: 2 } }}>
            <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1.5 }}>
              <Typography
                variant="caption"
                sx={{
                  bgcolor: "primary.main",
                  color: surface.light.paper,
                  borderRadius: "50%",
                  width: 24,
                  height: 24,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                  flexShrink: 0,
                  mt: 0.25,
                }}
              >
                {idx + 1}
              </Typography>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 0.25 }}>
                  {s.title}
                </Typography>
                {s.description && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                    {s.description}
                  </Typography>
                )}
                <CatalogMeta domain={s.domain} adoption={s.adoption} sourceIds={s.source_ids} />
                {s.principle_ids.length > 0 && (
                  <Box
                    sx={{ display: "flex", alignItems: "center", gap: 0.75, mt: 0.5, flexWrap: "wrap" }}
                  >
                    <Typography variant="caption" color="text.secondary" fontWeight={600}>
                      {t("governance.standards.linkedPrinciples")}:
                    </Typography>
                    {s.principle_ids.map((pid) => (
                      <Chip
                        key={pid}
                        size="small"
                        icon={<MaterialSymbol icon="bookmark_star" size={14} />}
                        label={principleTitle(pid)}
                        sx={{ height: 22, fontSize: 11 }}
                      />
                    ))}
                  </Box>
                )}
                {(s.rationale || s.implications) && (
                  <Box sx={{ display: "flex", gap: 3, mt: 0.5, flexWrap: "wrap" }}>
                    {s.rationale && (
                      <Box sx={{ flex: 1, minWidth: 200 }}>
                        <Typography variant="caption" color="text.secondary" fontWeight={600}>
                          {t("governance.standards.rationale")}:
                        </Typography>
                        <Box component="ul" sx={{ m: 0, pl: 2, listStyleType: "'•  '" }}>
                          {s.rationale
                            .split("\n")
                            .filter(Boolean)
                            .map((line, i) => (
                              <Typography
                                key={i}
                                component="li"
                                variant="caption"
                                color="text.secondary"
                                sx={{ py: 0.1 }}
                              >
                                {line}
                              </Typography>
                            ))}
                        </Box>
                      </Box>
                    )}
                    {s.implications && (
                      <Box sx={{ flex: 1, minWidth: 200 }}>
                        <Typography variant="caption" color="text.secondary" fontWeight={600}>
                          {t("governance.standards.implications")}:
                        </Typography>
                        <Box component="ul" sx={{ m: 0, pl: 2, listStyleType: "'•  '" }}>
                          {s.implications
                            .split("\n")
                            .filter(Boolean)
                            .map((line, i) => (
                              <Typography
                                key={i}
                                component="li"
                                variant="caption"
                                color="text.secondary"
                                sx={{ py: 0.1 }}
                              >
                                {line}
                              </Typography>
                            ))}
                        </Box>
                      </Box>
                    )}
                  </Box>
                )}
              </Box>
            </Box>
          </CardContent>
        </MuiCard>
      ))}
    </Box>
  );
}

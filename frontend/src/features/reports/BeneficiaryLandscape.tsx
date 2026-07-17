/**
 * Beneficiary Landscape
 * Organization × beneficiary groups mapping for segmentation strategy.
 * Part of Phase 9: Beneficiary Experience Views.
 */

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import { api } from "@/api/client";
import ReportShell from "./ReportShell";

interface PersonaMapping {
  name: string;
  subtype: string;
  org: string;
}

export default function BeneficiaryLandscape() {
  const { t } = useTranslation(["reports"]);
  const [personas, setPersonas] = useState<PersonaMapping[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          const [response, orgRels] = await Promise.all([
            api.get<{ items: any[] }>("/cards?type=Persona&page_size=500"),
            api.get<any[]>("/relations?type=relPersonaToOrg").catch(() => []),
          ]);
          const cards = Array.isArray(response) ? response : response.items || [];

          // Persona → Organization membership (relPersonaToOrg: persona is source)
          const orgByPersona = new Map<string, string>();
          for (const rel of orgRels) {
            if (rel.source_id && rel.target?.name) orgByPersona.set(rel.source_id, rel.target.name);
          }

          const personaData: PersonaMapping[] = cards.map((c) => ({
            name: c.name,
            subtype: c.subtype || "general",
            org: orgByPersona.get(c.id) || "Unassigned",
          }));

          setPersonas(personaData);
        } catch (err) {
          setError("Failed to load landscape");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const mockData = useMemo(() => {
    const orgs = Array.from(new Set(personas.map((p) => p.org))).sort();
    const beneficiaryTypes = Array.from(new Set(personas.map((p) => p.subtype))).sort();

    return {
      orgs,
      beneficiaries: beneficiaryTypes,
      matrix: orgs.map((org) => {
        const inOrg = personas.filter((p) => p.org === org);
        return {
          name: org,
          total: inOrg.length,
          segments: beneficiaryTypes.map((seg) => ({
            name: seg,
            count: inOrg.filter((p) => p.subtype === seg).length,
          })),
        };
      }),
    };
  }, [personas]);

  return (
    <ReportShell title={t("beneficiaryLandscape.title", "Beneficiary Landscape")} icon="public">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("beneficiaryLandscape.subtitle", "Organization units × beneficiary groups and engagement metrics.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && (
        <Paper variant="outlined" sx={{ overflow: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ backgroundColor: "#fafafa" }}>
                <TableCell sx={{ fontWeight: 700, minWidth: 150 }}>{t("beneficiaryLandscape.col.org", "Organization")}</TableCell>
                <TableCell sx={{ fontWeight: 700, width: 120 }}>{t("beneficiaryLandscape.col.total", "Total")}</TableCell>
                {mockData.beneficiaries.map((seg) => (
                  <TableCell key={seg} sx={{ fontWeight: 700, width: 140, textAlign: "center" }}>
                    <Typography variant="caption">{seg}</Typography>
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {mockData.matrix.map((org, idx) => (
                <TableRow key={idx} hover>
                  <TableCell sx={{ fontWeight: 600 }}>{org.name}</TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {org.total}
                    </Typography>
                  </TableCell>
                  {org.segments.map((seg, segIdx) => (
                    <TableCell key={segIdx} sx={{ textAlign: "center" }}>
                      <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 0.5 }}>
                        {seg.count > 0 ? (
                          <Chip size="small" label={seg.count} variant="outlined" sx={{ fontSize: "0.7rem" }} />
                        ) : (
                          <Typography variant="caption" color="text.disabled">—</Typography>
                        )}
                      </Box>
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}
    </ReportShell>
  );
}

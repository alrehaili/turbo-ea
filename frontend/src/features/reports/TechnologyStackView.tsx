/**
 * Technology Stack View
 * Hierarchical view of technology stacks and their components.
 * Part of Phase 7: Technology Deployment & Cloud Views.
 */

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import ReportShell from "./ReportShell";

interface StackLayer {
  id: string;
  name: string;
  layer: string;
  category: string;
  vendor?: string;
  componentCount: number;
  expanded: boolean;
}

export default function TechnologyStackView() {
  const { t } = useTranslation(["reports"]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stacks, setStacks] = useState<StackLayer[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          const [compResp, catRels, vendorRels] = await Promise.all([
            api.get<{ items: any[] }>("/cards?type=ITComponent&page_size=1000"),
            api.get<any[]>("/relations?type=relITCToTechCat").catch(() => []),
            api.get<any[]>("/relations?type=relProviderToITC").catch(() => []),
          ]);
          const components = Array.isArray(compResp) ? compResp : compResp.items || [];

          // TechCategory relation = the stack layer; Provider relation = vendor
          const categoryByComponent = new Map<string, string>();
          for (const rel of catRels) {
            if (rel.source_id && rel.target?.name) categoryByComponent.set(rel.source_id, rel.target.name);
          }
          const vendorByComponent = new Map<string, string>();
          for (const rel of vendorRels) {
            if (rel.target_id && rel.source?.name) vendorByComponent.set(rel.target_id, rel.source.name);
          }

          const subtypeLayer: Record<string, string> = {
            software: "Software",
            hardware: "Hardware & Infrastructure",
            saas: "Cloud Services (SaaS)",
            paas: "Cloud Services (PaaS)",
            iaas: "Cloud Services (IaaS)",
            service: "Managed Services",
            aiModel: "AI Models",
          };

          const stacks = components.map((c) => ({
            id: c.id,
            name: c.name,
            layer: subtypeLayer[c.subtype] || "Other",
            category: categoryByComponent.get(c.id) || "Uncategorised",
            vendor: vendorByComponent.get(c.id),
            componentCount: 1,
            expanded: false,
          }));
          setStacks(stacks.sort((a, b) => a.layer.localeCompare(b.layer)));
        } catch (err) {
          setError("Failed to load technology stack data");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const toggleExpand = (id: string) => {
    const newExpanded = new Set(expanded);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpanded(newExpanded);
  };

  const layerGroups = useMemo(() => {
    const groups = new Map<string, StackLayer[]>();
    stacks.forEach((s) => {
      if (!groups.has(s.layer)) {
        groups.set(s.layer, []);
      }
      groups.get(s.layer)!.push(s);
    });
    return Array.from(groups.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [stacks]);

  return (
    <ReportShell title={t("techStack.title", "Technology Stack")} icon="architecture">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("techStack.subtitle", "View technology components organized by architectural layer.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && stacks.length === 0 && !error && <Alert severity="info">{t("techStack.empty", "No technology components found.")}</Alert>}

      {!loading && stacks.length > 0 && (
        <Paper variant="outlined" sx={{ overflow: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ backgroundColor: "#fafafa" }}>
                <TableCell sx={{ fontWeight: 700, width: 40 }} />
                <TableCell sx={{ fontWeight: 700 }}>{t("techStack.col.layer", "Layer")}</TableCell>
                <TableCell sx={{ fontWeight: 700, width: 150 }}>{t("techStack.col.category", "Category")}</TableCell>
                <TableCell sx={{ fontWeight: 700, width: 120 }}>{t("techStack.col.vendor", "Vendor")}</TableCell>
                <TableCell sx={{ fontWeight: 700, width: 80, textAlign: "right" }}>{t("techStack.col.components", "Count")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {layerGroups.map(([layer, components]) => (
                <Box component="tbody" key={layer}>
                  <TableRow hover sx={{ backgroundColor: "#f5f5f5" }}>
                    <TableCell sx={{ textAlign: "center" }}>
                      <IconButton
                        size="small"
                        onClick={() => toggleExpand(layer)}
                        sx={{ color: "text.secondary" }}
                      >
                        <MaterialSymbol icon={expanded.has(layer) ? "expand_less" : "expand_more"} size={18} />
                      </IconButton>
                    </TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>
                      <Chip label={layer} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell />
                    <TableCell />
                    <TableCell sx={{ textAlign: "right", fontWeight: 700 }}>
                      {components.length}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell colSpan={5} sx={{ p: 0 }}>
                      <Collapse in={expanded.has(layer)} timeout="auto" unmountOnExit>
                        <Table size="small" sx={{ backgroundColor: "#fafafa" }}>
                          <TableBody>
                            {components.map((comp) => (
                              <TableRow key={comp.id} hover>
                                <TableCell sx={{ pl: 4 }} />
                                <TableCell>
                                  <Typography variant="body2">{comp.name}</Typography>
                                </TableCell>
                                <TableCell>
                                  <Chip size="small" label={comp.category} variant="outlined" />
                                </TableCell>
                                <TableCell>
                                  <Typography variant="caption">{comp.vendor || "—"}</Typography>
                                </TableCell>
                                <TableCell />
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </Collapse>
                    </TableCell>
                  </TableRow>
                </Box>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}
    </ReportShell>
  );
}

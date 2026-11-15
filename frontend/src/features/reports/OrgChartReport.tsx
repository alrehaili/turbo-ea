/**
 * OrgChartReport — the NORA BA "Organization Chart" artifact: the organization
 * hierarchy rendered as an indented tree. [FORK FEATURE] — noraPlan.md WP3.4.
 * Draws Organizational Units under NORA, Organization cards otherwise
 * (`pickOrgChartType`).
 */
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useOptionLabel, useSubtypeLabel } from "@/hooks/useResolveLabel";
import { useMetamodel } from "@/hooks/useMetamodel";
import type { Card } from "@/types";
import { orgNodeIcon, orgNodeKind, pickOrgChartType } from "./orgChart";

interface TreeNode {
  card: Card;
  children: TreeNode[];
}

// Color mapping for org hierarchy levels (business layer colors)
const ORG_LEVEL_COLORS: Record<number, string> = {
  0: "#2889ff", // Root (Sector) — primary blue
  1: "#1565c0", // Level 1 — darker blue
  2: "#0d47a1", // Level 2 — even darker
  3: "#1a237e", // Level 3+ — navy
};

function buildTree(cards: Card[]): TreeNode[] {
  const nodes = new Map<string, TreeNode>(cards.map((c) => [c.id, { card: c, children: [] }]));
  const roots: TreeNode[] = [];
  for (const node of nodes.values()) {
    const parent = node.card.parent_id ? nodes.get(node.card.parent_id) : undefined;
    if (parent) parent.children.push(node);
    else roots.push(node);
  }
  const sortRec = (list: TreeNode[]) => {
    list.sort((a, b) => a.card.name.localeCompare(b.card.name));
    list.forEach((n) => sortRec(n.children));
  };
  sortRec(roots);
  return roots;
}

export default function OrgChartReport() {
  const { t } = useTranslation(["reports", "common"]);
  const { types, loading: typesLoading } = useMetamodel();
  const subtypeLabel = useSubtypeLabel();
  const optionLabel = useOptionLabel();
  const orgType = pickOrgChartType(types);
  const { data, loading, error } = useApiQuery<{ items: Card[] }>(
    orgType ? `/cards?type=${encodeURIComponent(orgType.key)}&page_size=10000` : null,
  );
  const cards = error ? [] : data?.items;
  const unitTypeOptions =
    orgType?.fields_schema
      ?.flatMap((section) => section.fields)
      .find((field) => field.key === "unitType")?.options ?? [];

  if (typesLoading || loading || (orgType && !cards)) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const renderNode = (node: TreeNode, level: number) => {
    const subtypeDef = orgType?.subtypes?.find((s) => s.key === node.card.subtype);
    const unitTypeDef = subtypeDef
      ? undefined
      : unitTypeOptions.find((o) => o.key === node.card.attributes?.unitType);
    const icon = orgNodeIcon(orgNodeKind(node.card));
    // Use hierarchical color or fallback to grey for deep levels
    const color = ORG_LEVEL_COLORS[level] || "#546e7a";

    return (
      <Box key={node.card.id}>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            py: 0.75,
            pl: 2 + level * 3,
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <MaterialSymbol icon={icon} size={18} color={color} />
          <Link
            component={RouterLink}
            to={`/cards/${node.card.id}`}
            underline="hover"
            sx={{ fontWeight: level === 0 ? 600 : 400 }}
          >
            {node.card.name}
          </Link>
          {(subtypeDef || unitTypeDef) && (
            <Typography variant="caption" color="text.secondary">
              {subtypeDef ? subtypeLabel(subtypeDef) : optionLabel(unitTypeDef)}
            </Typography>
          )}
        </Box>
        {node.children.map((child) => renderNode(child, level + 1))}
      </Box>
    );
  };

  const roots = buildTree(cards ?? []);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 0.5 }}>
        {t("orgChart.title")}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("orgChart.subtitle")}
      </Typography>
      {roots.length === 0 ? (
        <Alert severity="info">{t("orgChart.empty")}</Alert>
      ) : (
        <Paper variant="outlined">{roots.map((r) => renderNode(r, 0))}</Paper>
      )}
    </Box>
  );
}

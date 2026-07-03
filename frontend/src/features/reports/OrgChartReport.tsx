/**
 * OrgChartReport — the NORA BA "Organization Chart" artifact: the Organization
 * hierarchy rendered as an indented tree. [FORK FEATURE] — noraPlan.md WP3.4.
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import { useSubtypeLabel } from "@/hooks/useResolveLabel";
import { useMetamodel } from "@/hooks/useMetamodel";
import type { Card } from "@/types";

interface TreeNode {
  card: Card;
  children: TreeNode[];
}

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
  const [cards, setCards] = useState<Card[] | null>(null);
  const { types } = useMetamodel();
  const subtypeLabel = useSubtypeLabel();
  const orgType = types.find((ty) => ty.key === "Organization");

  useEffect(() => {
    api
      .get<{ items: Card[] }>("/cards?type=Organization&page_size=10000")
      .then((res) => setCards(res.items))
      .catch(() => setCards([]));
  }, []);

  if (!cards) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const renderNode = (node: TreeNode, level: number) => {
    const subtypeDef = orgType?.subtypes?.find((s) => s.key === node.card.subtype);
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
          <MaterialSymbol
            icon="corporate_fare"
            size={18}
            color={level === 0 ? "#2889ff" : "#78909c"}
          />
          <Link
            component={RouterLink}
            to={`/cards/${node.card.id}`}
            underline="hover"
            sx={{ fontWeight: level === 0 ? 600 : 400 }}
          >
            {node.card.name}
          </Link>
          {subtypeDef && (
            <Typography variant="caption" color="text.secondary">
              {subtypeLabel(subtypeDef)}
            </Typography>
          )}
        </Box>
        {node.children.map((child) => renderNode(child, level + 1))}
      </Box>
    );
  };

  const roots = buildTree(cards);

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

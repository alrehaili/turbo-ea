/**
 * ValueChainReport — the NEA "Business Value Chain" viewpoint (Business,
 * conceptual level): the top-tier Business Capabilities as a chevron ribbon,
 * grouped by capability type when the NORA profile's `capabilityType` field
 * is filled (core capabilities form the chain; supporting/strategic ones sit
 * in bands below), with each chevron's child capabilities listed beneath it.
 *
 * [FORK FEATURE] — noraPlan.md WP6.7.
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { api } from "@/api/client";
import type { Card } from "@/types";

const CHAIN_COLOR = "#003399";

function chevron(clipFirst: boolean, clipLast: boolean): string {
  // First chevron has a flat start; last has a flat end; middles have both.
  const notchIn = clipFirst ? "0 50%" : "6% 50%";
  const tipOut = clipLast ? "100% 0, 100% 100%" : "94% 0, 100% 50%, 94% 100%";
  return `polygon(0 0, ${tipOut}, 0 100%, ${notchIn})`;
}

export default function ValueChainReport() {
  const { t } = useTranslation(["reports"]);
  const [caps, setCaps] = useState<Card[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<{ items: Card[] }>("/cards?type=BusinessCapability&page_size=2000")
      .then((res) => setCaps(res.items))
      .catch((e) => setError(e instanceof Error ? e.message : "error"));
  }, []);

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }
  if (!caps) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const topLevel = caps
    .filter((c) => !c.parent_id)
    .sort((a, b) => a.name.localeCompare(b.name));
  const childrenOf = (id: string) =>
    caps.filter((c) => c.parent_id === id).sort((a, b) => a.name.localeCompare(b.name));

  const typeOf = (c: Card) => (c.attributes ?? {})["capabilityType"] as string | undefined;
  // Core capabilities form the chain; anything untyped rides with them so the
  // report degrades gracefully before the profile fields are filled.
  const chain = topLevel.filter((c) => !typeOf(c) || typeOf(c) === "core");
  const strategic = topLevel.filter((c) => typeOf(c) === "strategic");
  const supporting = topLevel.filter((c) => typeOf(c) === "supporting");

  const band = (title: string, items: Card[], color: string) =>
    items.length === 0 ? null : (
      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Typography variant="overline" color="text.secondary" display="block" sx={{ mb: 1 }}>
          {title}
        </Typography>
        <Box sx={{ display: "flex", gap: 0.75, flexWrap: "wrap" }}>
          {items.map((c) => (
            <Chip
              key={c.id}
              size="small"
              variant="outlined"
              label={c.name}
              component={RouterLink}
              to={`/cards/${c.id}`}
              clickable
              sx={{ borderColor: color }}
            />
          ))}
        </Box>
      </Paper>
    );

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 0.5 }}>
        {t("valueChain.title")}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("valueChain.subtitle")}
      </Typography>

      {chain.length === 0 ? (
        <Alert severity="info">{t("valueChain.empty")}</Alert>
      ) : (
        <>
          {/* The chevron ribbon */}
          <Box sx={{ display: "flex", gap: 0.5, mb: 1, overflowX: "auto", pb: 1 }}>
            {chain.map((c, i) => (
              <Box
                key={c.id}
                component={RouterLink}
                to={`/cards/${c.id}`}
                sx={{
                  flex: "1 0 0",
                  minWidth: 130,
                  clipPath: chevron(i === 0, i === chain.length - 1),
                  bgcolor: CHAIN_COLOR,
                  color: "#fff",
                  px: 3,
                  py: 2,
                  textAlign: "center",
                  textDecoration: "none",
                  "&:hover": { filter: "brightness(1.2)" },
                }}
              >
                <Typography variant="subtitle2" fontWeight={700} sx={{ lineHeight: 1.2 }}>
                  {c.name}
                </Typography>
                <Typography variant="caption" sx={{ opacity: 0.8 }}>
                  {childrenOf(c.id).length} {t("valueChain.subCapabilities")}
                </Typography>
              </Box>
            ))}
          </Box>

          {/* Sub-capabilities under each chain segment */}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: `repeat(${chain.length}, 1fr)`,
              gap: 0.5,
              mb: 3,
            }}
          >
            {chain.map((c) => (
              <Box key={c.id} sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
                {childrenOf(c.id).map((child) => (
                  <Chip
                    key={child.id}
                    size="small"
                    variant="outlined"
                    label={child.name}
                    component={RouterLink}
                    to={`/cards/${child.id}`}
                    clickable
                  />
                ))}
              </Box>
            ))}
          </Box>
        </>
      )}

      {band(t("valueChain.strategic"), strategic, "#c7527d")}
      {band(t("valueChain.supporting"), supporting, "#607d8b")}
    </Box>
  );
}

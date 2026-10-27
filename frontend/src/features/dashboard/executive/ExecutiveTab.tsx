import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";
import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import ExecutiveBenefits from "./ExecutiveBenefits";
import ExecutiveDecisions from "./ExecutiveDecisions";
import ExecutiveDetailsPage from "./ExecutiveDetailsPage";
import ExecutiveGovernance from "./ExecutiveGovernance";
import ExecutiveOverview from "./ExecutiveOverview";
import ExecutiveStrategy from "./ExecutiveStrategy";

/**
 * The Executive tab: a secondary navigation over the executive pages
 * (UI_UX_SPECIFICATION §1). Phase 2 ships the CEO overview and the decisions
 * page; the Phase 1 delivery, money and repository figures stay one page away
 * as *Details*. Pages of later phases are not listed until they exist. The page
 * lives in the URL (`?tab=executive&page=…`) so a link opens it directly.
 */
export const EXECUTIVE_PAGES = [
  "overview",
  "strategy",
  "governance",
  "benefits",
  "decisions",
  "details",
] as const;
export type ExecutivePage = (typeof EXECUTIVE_PAGES)[number];

export default function ExecutiveTab() {
  const { t } = useTranslation("common");
  const [searchParams, setSearchParams] = useSearchParams();
  const raw = searchParams.get("page");
  const page: ExecutivePage = (EXECUTIVE_PAGES as readonly string[]).includes(raw ?? "")
    ? (raw as ExecutivePage)
    : "overview";

  const select = (next: ExecutivePage) => {
    const params = new URLSearchParams(searchParams);
    params.set("tab", "executive");
    params.set("page", next);
    setSearchParams(params, { replace: true });
  };

  return (
    <Box>
      <Tabs
        value={page}
        onChange={(_, v: ExecutivePage) => select(v)}
        variant="scrollable"
        allowScrollButtonsMobile
        aria-label={t("dashboard.executive.pages.label")}
        sx={{ mb: 2, borderBottom: 1, borderColor: "divider", minHeight: 40 }}
      >
        {EXECUTIVE_PAGES.map((key) => (
          <Tab
            key={key}
            value={key}
            label={t(`dashboard.executive.pages.${key}`)}
            sx={{ textTransform: "none", minHeight: 40 }}
          />
        ))}
      </Tabs>
      {page === "overview" && <ExecutiveOverview />}
      {page === "strategy" && <ExecutiveStrategy />}
      {page === "governance" && <ExecutiveGovernance />}
      {page === "benefits" && <ExecutiveBenefits />}
      {page === "decisions" && <ExecutiveDecisions />}
      {page === "details" && <ExecutiveDetailsPage />}
    </Box>
  );
}

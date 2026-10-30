import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import "@/i18n";
import ComplianceHeatmap from "./ComplianceHeatmap";

const regulations = [{ key: "gdpr", label: "GDPR" }];

describe("ComplianceHeatmap score availability", () => {
  it("does not invent a perfect score for an unassessed regulation", () => {
    render(<ComplianceHeatmap regulations={regulations} matrix={{}} scores={{}} />);
    expect(screen.getByText("Not scanned")).toBeInTheDocument();
    expect(screen.queryByText("100%")).not.toBeInTheDocument();
  });
  it("does not invent a score when counts are present without a score", () => {
    render(<ComplianceHeatmap regulations={regulations} matrix={{ gdpr: { compliant: 1 } }} scores={{}} />);
    expect(screen.queryByText("100%")).not.toBeInTheDocument();
    expect(screen.getAllByText("—")).toHaveLength(5);
  });
  it("preserves an assessed zero score", () => {
    render(<ComplianceHeatmap regulations={regulations} matrix={{ gdpr: { non_compliant: 1 } }} scores={{ gdpr: 0 }} />);
    expect(screen.getByText("0%")).toBeInTheDocument();
  });
});

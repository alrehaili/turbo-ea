import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import i18n from "@/i18n";
import { makeCardType } from "@/test/fixtures/metamodel";
import { withMetamodel } from "@/test/hooks";
import ComplianceFilterSidebar, { defaultComplianceFilters } from "./ComplianceFilterSidebar";

vi.mock("@/hooks/useMetamodel", () => import("@/test/hooks").then((m) => m.useMetamodelModule()));

function renderSidebar() {
  const onFiltersChange = vi.fn();
  render(<ComplianceFilterSidebar
    filters={defaultComplianceFilters()}
    onFiltersChange={onFiltersChange}
    collapsed={false}
    onToggleCollapsed={vi.fn()}
    visibleColumns={new Set()}
    onVisibleColumnsChange={vi.fn()}
    frozenColumns={new Set()}
    onToggleFrozen={vi.fn()}
    columnOrderItems={[]}
    columnOrder={[]}
    onColumnOrderChange={vi.fn()}
  />);
  return onFiltersChange;
}

afterEach(async () => { await act(async () => { await i18n.changeLanguage("en"); }); });

describe("ComplianceFilterSidebar card type labels", () => {
  it("uses admin-defined labels and keeps filter values as keys", () => {
    withMetamodel([makeCardType({ key: "ITComponent", label: "Technology Asset", translations: {} })]);
    const onChange = renderSidebar();
    fireEvent.click(screen.getByText("Technology Asset"));
    expect(onChange.mock.calls[0][0].cardTypes.has("ITComponent")).toBe(false);
    expect(screen.queryByText("ITComponent")).not.toBeInTheDocument();
  });

  it("updates the metamodel label when the language changes", async () => {
    withMetamodel([makeCardType({ key: "ITComponent", label: "Technology Asset", translations: { label: { de: "Technologieanlage" } } })]);
    renderSidebar();
    expect(screen.getByText("Technology Asset")).toBeInTheDocument();
    await act(async () => { await i18n.changeLanguage("de"); });
    expect(screen.getByText("Technologieanlage")).toBeInTheDocument();
  });

  it("uses translated display labels while a type is absent from the metamodel", () => {
    withMetamodel([]);
    renderSidebar();
    expect(screen.getByText("IT Component")).toBeInTheDocument();
    expect(screen.queryByText("ITComponent")).not.toBeInTheDocument();
  });
});

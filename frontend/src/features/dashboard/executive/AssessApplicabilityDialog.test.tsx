import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const post = vi.fn();
vi.mock("@/api/client", () => ({
  api: { post: (...a: unknown[]) => post(...a) },
}));

import AssessApplicabilityDialog from "./AssessApplicabilityDialog";

beforeEach(() => {
  post.mockReset().mockResolvedValue({});
});

describe("AssessApplicabilityDialog", () => {
  it("records an exemption with its criteria and justification", async () => {
    const onSaved = vi.fn();
    render(
      <AssessApplicabilityDialog
        initiative={{ id: "i1", name: "ERP renewal" }}
        onClose={vi.fn()}
        onSaved={onSaved}
      />,
    );
    const save = screen.getByRole("button", { name: "Record assessment" });
    // Every field is required before saving.
    expect(save).toBeDisabled();
    fireEvent.click(screen.getByLabelText("Does not require EA governance review (exempt)"));
    fireEvent.change(screen.getByLabelText("Criteria applied"), { target: { value: "v1 §2" } });
    fireEvent.change(screen.getByLabelText("Justification"), { target: { value: "Minor change" } });
    fireEvent.click(save);
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/cards/i1/ea-applicability", {
        decision: "not_required",
        criteria_reference: "v1 §2",
        justification: "Minor change",
      }),
    );
    expect(onSaved).toHaveBeenCalled();
  });

  it("shows the server's refusal", async () => {
    post.mockRejectedValue(new Error("Not enough permissions"));
    render(
      <AssessApplicabilityDialog initiative={{ id: "i1", name: "ERP" }} onClose={vi.fn()} onSaved={vi.fn()} />,
    );
    fireEvent.change(screen.getByLabelText("Criteria applied"), { target: { value: "v1" } });
    fireEvent.change(screen.getByLabelText("Justification"), { target: { value: "Core" } });
    fireEvent.click(screen.getByRole("button", { name: "Record assessment" }));
    expect(await screen.findByText("Not enough permissions")).toBeInTheDocument();
  });
});

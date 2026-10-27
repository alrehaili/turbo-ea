import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { DecisionImplementationState } from "@/types";

const get = vi.fn();
const post = vi.fn();
const put = vi.fn();
const patch = vi.fn();
const del = vi.fn();
vi.mock("@/api/client", () => ({
  api: {
    get: (...a: unknown[]) => get(...a),
    post: (...a: unknown[]) => post(...a),
    put: (...a: unknown[]) => put(...a),
    patch: (...a: unknown[]) => patch(...a),
    delete: (...a: unknown[]) => del(...a),
  },
  isAbortError: () => false,
}));

import DecisionImplementationPanel from "./DecisionImplementationPanel";

function state(over: Partial<DecisionImplementationState> = {}): DecisionImplementationState {
  return {
    decision: { kind: "adr", id: "d1", status: "signed", approved: true },
    state: "in_progress",
    overdue: false,
    implementation: {
      status: "open",
      due_date: "2027-03-31",
      original_due_date: "2027-01-31",
      due_date_basis: "with_decision",
      revised: true,
      submitted_by: null,
      submitted_at: null,
      submission_note: null,
      verified_by: null,
      verified_at: null,
      attestation: null,
      text_withheld: false,
    },
    actions: [
      {
        id: "a1",
        description: "Cut over billing",
        status: "open",
        assigned_to: { id: "u-owner", display_name: "Olivia Owner" },
        due_date: "2027-01-15",
        completed_by: null,
        completed_at: null,
        completion_note: null,
        evidence: [],
        evidence_count: 0,
        can_complete: true,
      },
    ],
    history: { recorded: false, transitions: [] },
    permissions: { manage: true, verify: false, submit: true },
    ...over,
  };
}

function serve(payload: DecisionImplementationState) {
  get.mockImplementation((path: string) => {
    if (path.endsWith("/implementation")) return Promise.resolve(payload);
    return Promise.resolve([]);
  });
}

beforeEach(() => {
  get.mockReset();
  post.mockReset().mockResolvedValue({});
  put.mockReset().mockResolvedValue({});
  patch.mockReset().mockResolvedValue({});
  del.mockReset().mockResolvedValue(undefined);
});

describe("DecisionImplementationPanel", () => {
  it("shows the deadline in force beside the original approved one, and the actions", async () => {
    serve(state());
    render(<DecisionImplementationPanel kind="adr" decisionId="d1" linkedCardIds={[]} />);
    expect(await screen.findByText("Cut over billing")).toBeInTheDocument();
    expect(screen.getByText("In progress")).toBeInTheDocument();
    expect(screen.getByText(/Originally approved:/)).toBeInTheDocument();
    expect(screen.getByText(/Owner: Olivia Owner/)).toBeInTheDocument();
  });

  it("completes an action with a note and a system reference as evidence", async () => {
    serve(state());
    render(<DecisionImplementationPanel kind="arb" decisionId="d1" linkedCardIds={[]} />);
    fireEvent.click(await screen.findByRole("button", { name: "Complete" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("What was done"), {
      target: { value: "Switched traffic" },
    });
    fireEvent.change(within(dialog).getByLabelText("System reference"), {
      target: { value: "CHG-1001" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/arb/d1/actions/a1/complete", {
        note: "Switched traffic",
        evidence: [{ kind: "reference", text: "CHG-1001" }],
      }),
    );
  });

  it("offers submission only once every action is complete", async () => {
    const done = state();
    done.actions[0] = { ...done.actions[0], status: "done", evidence_count: 1 };
    serve(done);
    render(<DecisionImplementationPanel kind="adr" decisionId="d1" linkedCardIds={[]} />);
    expect(await screen.findByRole("button", { name: "Submit for verification" })).toBeInTheDocument();
  });

  it("does not offer submission while an action is open", async () => {
    serve(state());
    render(<DecisionImplementationPanel kind="adr" decisionId="d1" linkedCardIds={[]} />);
    await screen.findByText("Cut over billing");
    expect(screen.queryByRole("button", { name: "Submit for verification" })).toBeNull();
  });

  it("lets an independent verifier verify with an attestation", async () => {
    serve(
      state({
        state: "awaiting_verification",
        implementation: { ...state().implementation, status: "submitted" },
        permissions: { manage: false, verify: true, submit: false },
      }),
    );
    render(<DecisionImplementationPanel kind="adr" decisionId="d1" linkedCardIds={[]} />);
    fireEvent.click(await screen.findByRole("button", { name: "Verify" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("What you examined"), {
      target: { value: "CHG-1001" },
    });
    fireEvent.change(within(dialog).getByLabelText("Why it shows the decision implemented"), {
      target: { value: "Deployed" },
    });
    fireEvent.click(within(dialog).getByLabelText("I confirm this attestation"));
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/adr/d1/implementation/verify", {
        outcome: "verified",
        attestation: { examined: "CHG-1001", demonstrates: "Deployed", confirmed: true },
      }),
    );
  });

  it("revises the deadline with a reason", async () => {
    serve(state());
    render(<DecisionImplementationPanel kind="arb" decisionId="d1" linkedCardIds={[]} />);
    fireEvent.click(await screen.findByRole("button", { name: "Revise" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Reason"), { target: { value: "Vendor delay" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(put).toHaveBeenCalledWith("/arb/d1/implementation/due-date", {
        due_date: "2027-03-31",
        reason: "Vendor delay",
      }),
    );
  });

  it("explains that actions wait for the signature on an unsigned ADR", async () => {
    serve(
      state({
        decision: { kind: "adr", id: "d1", status: "draft", approved: false },
        state: "no_plan",
        actions: [],
      }),
    );
    render(<DecisionImplementationPanel kind="adr" decisionId="d1" linkedCardIds={[]} />);
    expect(await screen.findByText(/Actions can be added once the decision is signed/)).toBeInTheDocument();
    expect(screen.getByText(/Proposed implementation deadline/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add action" })).toBeNull();
  });

  it("shows who verified once implemented, and freezes the actions", async () => {
    serve(
      state({
        state: "implemented",
        implementation: {
          ...state().implementation,
          status: "verified",
          verified_by: { id: "v", display_name: "Vera Verifier" },
          verified_at: "2027-01-20T10:00:00Z",
          attestation: { examined: "CHG-1001", demonstrates: "Deployed", confirmed: true },
        },
      }),
    );
    render(<DecisionImplementationPanel kind="adr" decisionId="d1" linkedCardIds={[]} />);
    expect(await screen.findByText(/verified by Vera Verifier/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Complete" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Add action" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Delete action" })).toBeNull();
    // Rewording is cosmetic and stays possible; owner and due date do not.
    fireEvent.click(screen.getByRole("button", { name: "Edit action" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByLabelText("Due date")).toBeDisabled();
    fireEvent.change(within(dialog).getByLabelText("Action"), { target: { value: "Cut over billing (EU)" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(patch).toHaveBeenCalledWith("/adr/d1/actions/a1", {
        description: "Cut over billing (EU)",
        assigned_to: "u-owner",
        due_date: "2027-01-15",
      }),
    );
  });
});

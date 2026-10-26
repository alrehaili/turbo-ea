import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const post = vi.fn();
const del = vi.fn();
const get = vi.fn();
vi.mock("@/api/client", () => ({
  api: {
    get: (...a: unknown[]) => get(...a),
    post: (...a: unknown[]) => post(...a),
    delete: (...a: unknown[]) => del(...a),
  },
}));

import ExceptionLifecycleActions, { type LifecycleException } from "./ExceptionLifecycleActions";

const ME = "u-me";

function renderActions(
  exception: LifecycleException,
  permissions: string[],
  onChanged = vi.fn(),
) {
  const can = (p: string) => permissions.includes(p);
  render(<ExceptionLifecycleActions exception={exception} userId={ME} can={can} onChanged={onChanged} />);
  return onChanged;
}

const MANAGE = "tech_standards.manage";
const APPROVE = "tech_standards.approve_exception";
const DELETE = "tech_standards.delete_exception";

beforeEach(() => {
  post.mockReset().mockResolvedValue({});
  del.mockReset().mockResolvedValue(undefined);
  get.mockReset().mockResolvedValue([]);
});

describe("ExceptionLifecycleActions", () => {
  it("offers approve and reject on a request to an approver", async () => {
    const onChanged = renderActions({ id: "e1", status: "requested" }, [APPROVE]);
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(post).toHaveBeenCalledWith("/tech-standards/exceptions/e1/decision?action=approve", {});
    expect(screen.queryByRole("button", { name: "Submit remediation" })).toBeNull();
  });

  it("submits remediation evidence on an approved or expired waiver", async () => {
    for (const status of ["approved", "expired"]) {
      post.mockClear();
      const { unmount } = render(
        <ExceptionLifecycleActions
          exception={{ id: "e2", status }}
          userId={ME}
          can={(p) => p === MANAGE}
          onChanged={vi.fn()}
        />,
      );
      fireEvent.click(screen.getByRole("button", { name: "Submit remediation" }));
      const confirm = screen.getByRole("button", { name: "Submit for verification" });
      expect(confirm).toBeDisabled(); // evidence is required
      fireEvent.change(screen.getByLabelText("Evidence"), { target: { value: "  Moved to REST  " } });
      fireEvent.click(confirm);
      await waitFor(() =>
        expect(post).toHaveBeenCalledWith("/tech-standards/exceptions/e2/remediation", {
          evidence: "Moved to REST",
        }),
      );
      unmount();
    }
  });

  it("cites the card's existing documents and files as remediation evidence", async () => {
    get.mockImplementation((path: string) =>
      Promise.resolve(
        path.endsWith("/documents")
          ? [{ id: "d1", name: "Cutover report" }]
          : [{ id: "f1", name: "config-export.json" }],
      ),
    );
    render(
      <ExceptionLifecycleActions
        exception={{ id: "e2b", status: "approved", card: { id: "c1" } }}
        userId={ME}
        can={(p) => p === MANAGE}
        onChanged={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Submit remediation" }));
    fireEvent.click(await screen.findByLabelText(/Cutover report/));
    expect(get).toHaveBeenCalledWith("/cards/c1/documents", expect.anything());
    expect(get).toHaveBeenCalledWith("/cards/c1/file-attachments", expect.anything());
    expect(screen.getByLabelText(/config-export\.json · File/)).not.toBeChecked();
    fireEvent.change(screen.getByLabelText("Evidence"), { target: { value: "Moved to REST" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit for verification" }));
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/tech-standards/exceptions/e2b/remediation", {
        evidence: "Moved to REST",
        evidence_refs: [{ kind: "document", id: "d1" }],
      }),
    );
  });

  it("says when the card has nothing to cite and loads nothing without a card", async () => {
    renderActions({ id: "e2c", status: "approved" }, [MANAGE]);
    fireEvent.click(screen.getByRole("button", { name: "Submit remediation" }));
    expect(screen.getByText(/has no documents or files yet/)).toBeInTheDocument();
    expect(get).not.toHaveBeenCalled();
  });

  it("lets an independent approver verify, but not the submitter or the requester", async () => {
    const onChanged = renderActions(
      { id: "e3", status: "remediation_submitted", created_by: "u-req", remediation_submitted_by: "u-sub" },
      [APPROVE],
    );
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));
    // The dialog explains that the violation itself must be gone (I-32); the
    // note is optional here, since the server decides whether it is needed.
    expect(screen.getByText(/not only evidence submitted/)).toBeInTheDocument();
    const confirm = screen.getAllByRole("button", { name: "Verify" }).at(-1)!;
    expect(confirm).toBeEnabled();
    fireEvent.click(confirm);
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(post).toHaveBeenCalledWith("/tech-standards/exceptions/e3/remediation/verify", {
      outcome: "verified",
    });
  });

  it("sends the verifier's attestation: what was examined, why, and the confirmation", async () => {
    renderActions(
      { id: "e3b", status: "remediation_submitted", created_by: "u-req", remediation_submitted_by: "u-sub" },
      [APPROVE],
    );
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));
    fireEvent.change(screen.getByLabelText("What you examined"), { target: { value: " Config export " } });
    fireEvent.change(screen.getByLabelText("Why it shows the violation is resolved"), {
      target: { value: " No MQ endpoint left " },
    });
    fireEvent.click(screen.getByLabelText(/I confirm that I examined this evidence myself/));
    fireEvent.click(screen.getAllByRole("button", { name: "Verify" }).at(-1)!);
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/tech-standards/exceptions/e3b/remediation/verify", {
        outcome: "verified",
        attestation: { examined: "Config export", demonstrates: "No MQ endpoint left", confirmed: true },
      }),
    );
  });

  it("shows a refused verification in the dialog", async () => {
    post.mockRejectedValueOnce(new Error("The standards check still finds this card using the standard"));
    renderActions(
      { id: "e3c", status: "remediation_submitted", created_by: "u-req", remediation_submitted_by: "u-sub" },
      [APPROVE],
    );
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));
    fireEvent.click(screen.getAllByRole("button", { name: "Verify" }).at(-1)!);
    expect(await screen.findByText(/still finds this card/)).toBeInTheDocument();
  });

  it("lets a manager withdraw an exception awaiting verification or past its expiry", () => {
    for (const status of ["remediation_submitted", "expired"]) {
      const { unmount } = render(
        <ExceptionLifecycleActions
          exception={{ id: "e12", status, created_by: "u-other" }}
          userId={ME}
          can={(p) => p === MANAGE}
          onChanged={vi.fn()}
        />,
      );
      expect(screen.getByRole("button", { name: "Withdraw" })).toBeInTheDocument();
      unmount();
    }
  });

  it("offers no withdrawal once rejected", () => {
    renderActions({ id: "e13", status: "rejected", created_by: ME }, [MANAGE]);
    expect(screen.queryByRole("button", { name: "Withdraw" })).toBeNull();
  });

  it("disables verification for the remediation submitter", () => {
    renderActions(
      { id: "e4", status: "remediation_submitted", created_by: "u-req", remediation_submitted_by: ME },
      [APPROVE],
    );
    expect(screen.getByRole("button", { name: "Verify" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Return" })).toBeDisabled();
  });

  it("disables verification for the requester", () => {
    renderActions(
      { id: "e5", status: "remediation_submitted", created_by: ME, remediation_submitted_by: "u-sub" },
      [APPROVE],
    );
    expect(screen.getByRole("button", { name: "Verify" })).toBeDisabled();
  });

  it("returns a remediation with a note", async () => {
    renderActions(
      { id: "e6", status: "remediation_submitted", created_by: "u-req", remediation_submitted_by: "u-sub" },
      [APPROVE],
    );
    fireEvent.click(screen.getByRole("button", { name: "Return" }));
    fireEvent.change(screen.getByLabelText("Why it is returned"), { target: { value: "Still on SOAP" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Return" }).at(-1)!);
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/tech-standards/exceptions/e6/remediation/verify", {
        outcome: "returned",
        note: "Still on SOAP",
      }),
    );
  });

  it("lets the requester withdraw without the manage permission, with a reason", async () => {
    renderActions({ id: "e7", status: "requested", created_by: ME }, []);
    fireEvent.click(screen.getByRole("button", { name: "Withdraw" }));
    fireEvent.change(screen.getByLabelText("Reason"), { target: { value: "Project cancelled" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Withdraw" }).at(-1)!);
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/tech-standards/exceptions/e7/withdraw", {
        reason: "Project cancelled",
      }),
    );
  });

  it("offers no withdrawal to someone who is neither the requester nor a manager", () => {
    renderActions({ id: "e8", status: "approved", created_by: "u-other" }, []);
    expect(screen.queryByRole("button", { name: "Withdraw" })).toBeNull();
  });

  it("offers no action on a closed exception except an authorised delete", () => {
    renderActions({ id: "e9", status: "remediated", created_by: ME }, [MANAGE, APPROVE]);
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("deletes permanently only with the delete permission and a reason", async () => {
    renderActions({ id: "e10", status: "rejected" }, [DELETE]);
    fireEvent.click(screen.getByRole("button", { name: /Delete permanently/ }));
    fireEvent.change(screen.getByLabelText("Why this record was created in error"), {
      target: { value: "Wrong card & standard" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Delete permanently" }));
    await waitFor(() =>
      expect(del).toHaveBeenCalledWith(
        "/tech-standards/exceptions/e10?reason=Wrong%20card%20%26%20standard",
      ),
    );
  });

  it("shows the server's refusal in the dialog", async () => {
    post.mockRejectedValueOnce(new Error("A withdrawal needs a reason"));
    renderActions({ id: "e11", status: "approved" }, [MANAGE]);
    fireEvent.click(screen.getByRole("button", { name: "Withdraw" }));
    fireEvent.change(screen.getByLabelText("Reason"), { target: { value: "x" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Withdraw" }).at(-1)!);
    expect(await screen.findByText("A withdrawal needs a reason")).toBeInTheDocument();
  });
});

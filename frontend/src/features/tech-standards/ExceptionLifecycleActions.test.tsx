import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const post = vi.fn();
const del = vi.fn();
vi.mock("@/api/client", () => ({
  api: { post: (...a: unknown[]) => post(...a), delete: (...a: unknown[]) => del(...a) },
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

  it("lets an independent approver verify, but not the submitter or the requester", async () => {
    const onChanged = renderActions(
      { id: "e3", status: "remediation_submitted", created_by: "u-req", remediation_submitted_by: "u-sub" },
      [APPROVE],
    );
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(post).toHaveBeenCalledWith("/tech-standards/exceptions/e3/remediation/verify", {
      outcome: "verified",
    });
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

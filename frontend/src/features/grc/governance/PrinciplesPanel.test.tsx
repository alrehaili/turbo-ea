/**
 * PrinciplesPanel — GRC Governance → Principles. [FORK] An `admin.metamodel`
 * holder gets the full CRUD admin component; everyone else the read-only list:
 * active principles only, in sort order, each numbered and carrying its
 * reference.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";

vi.mock("@/api/client", () => import("@/test/apiMock").then((m) => m.apiClientModule()));

// The admin CRUD component is rendered for privileged users; stub it so the
// gating tests assert only the decision, not the admin component internals.
vi.mock("@/features/admin/PrinciplesAdmin", () => ({
  default: () => <div data-testid="principles-admin">admin crud</div>,
}));

import "@/i18n";
import { AuthProvider } from "@/hooks/AuthContext";
import { mockApi } from "@/test/apiMock";
import type { EAPrinciple, User } from "@/types";
import PrinciplesPanel from "./PrinciplesPanel";

function makeUser(permissions: Record<string, boolean> | undefined): User {
  return {
    id: "u1",
    email: "u@example.com",
    display_name: "U",
    role: "member",
    is_active: true,
    permissions,
  };
}

const READER = makeUser({ "grc.view": true });

function wrap(user: User) {
  return render(
    <MemoryRouter>
      <AuthProvider user={user} refreshUser={async () => {}}>
        <PrinciplesPanel />
      </AuthProvider>
    </MemoryRouter>,
  );
}

const PATH = "/metamodel/principles";

const PRINCIPLES: EAPrinciple[] = [
  { id: "b", reference_number: "P-002", title: "Cloud first", is_active: true, sort_order: 20 },
  {
    id: "a",
    reference_number: "P-001",
    title: "Reuse first",
    description: "Prefer reuse",
    rationale: "Cheaper\n\nFaster",
    implications: "Check the catalogue",
    is_active: true,
    sort_order: 10,
  },
  { id: "c", reference_number: "P-003", title: "Retired", is_active: false, sort_order: 0 },
  { id: "d", reference_number: null, title: "Unnumbered", is_active: true, sort_order: 30 },
];

function card(title: string): HTMLElement {
  const el = screen.getByText(title).closest(".MuiCard-root");
  if (!(el instanceof HTMLElement)) throw new Error(`no card for ${title}`);
  return el;
}

beforeEach(() => {
  mockApi.reset();
});

describe("PrinciplesPanel", () => {
  it("lists the active principles in sort order with their number and reference", async () => {
    mockApi.on("get", PATH, PRINCIPLES);
    wrap(READER);

    await screen.findByText("Reuse first");
    const titles = screen.getAllByRole("heading").map((h) => h.textContent);
    // The panel heading, then one title per active principle in sort order,
    // each followed by its reference.
    expect(titles).toEqual([
      "Architecture Principles",
      "Reuse firstP-001",
      "Cloud firstP-002",
      "Unnumbered",
    ]);
    expect(screen.queryByText("Retired")).not.toBeInTheDocument();

    const reuse = card("Reuse first");
    expect(within(reuse).getByText("1")).toBeInTheDocument();
    expect(within(reuse).getByText("P-001")).toBeInTheDocument();
    expect(within(reuse).getByText("Prefer reuse")).toBeInTheDocument();
    expect(within(reuse).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "Cheaper",
      "Faster",
      "Check the catalogue",
    ]);

    const cloud = card("Cloud first");
    expect(within(cloud).getByText("2")).toBeInTheDocument();
    expect(within(cloud).getByText("P-002")).toBeInTheDocument();

    const unnumbered = card("Unnumbered");
    expect(within(unnumbered).getByText("3")).toBeInTheDocument();
    expect(within(unnumbered).queryByText(/^P-/)).not.toBeInTheDocument();
  });

  it("shows the empty state when no principle is active", async () => {
    mockApi.on("get", PATH, [PRINCIPLES[2]]);
    wrap(READER);
    expect(await screen.findByText(/No active principles yet/)).toBeInTheDocument();
  });
});

describe("PrinciplesPanel gating", () => {
  it("renders the full CRUD admin UI for users with admin.metamodel", () => {
    wrap(makeUser({ "admin.metamodel": true }));
    expect(screen.getByTestId("principles-admin")).toBeInTheDocument();
  });

  it("renders the full CRUD admin UI for wildcard users", () => {
    wrap(makeUser({ "*": true }));
    expect(screen.getByTestId("principles-admin")).toBeInTheDocument();
  });

  it("renders the read-only view (no CRUD) without admin.metamodel", async () => {
    mockApi.on("get", PATH, []);
    wrap(READER);
    expect(await screen.findByText(/No active principles yet/)).toBeInTheDocument();
    expect(screen.queryByTestId("principles-admin")).not.toBeInTheDocument();
  });
});

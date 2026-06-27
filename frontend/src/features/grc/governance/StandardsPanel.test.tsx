import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "@/hooks/AuthContext";
import type { User } from "@/types";

// The admin CRUD component is rendered for privileged users; stub it so the
// test asserts only the gating decision, not the admin component internals.
vi.mock("@/features/admin/StandardsAdmin", () => ({
  default: () => <div data-testid="standards-admin">admin crud</div>,
}));

// The read-only branch fetches standards + principles on mount — keep it
// network-free.
vi.mock("@/api/client", () => ({
  api: { get: vi.fn().mockResolvedValue([]) },
}));

import StandardsPanel from "./StandardsPanel";

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

function wrap(user: User) {
  return render(
    <MemoryRouter>
      <AuthProvider user={user} refreshUser={async () => {}}>
        <StandardsPanel />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("StandardsPanel gating", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders the full CRUD admin UI for users with admin.metamodel", () => {
    wrap(makeUser({ "admin.metamodel": true }));
    expect(screen.getByTestId("standards-admin")).toBeInTheDocument();
  });

  it("renders the full CRUD admin UI for wildcard users", () => {
    wrap(makeUser({ "*": true }));
    expect(screen.getByTestId("standards-admin")).toBeInTheDocument();
  });

  it("renders the read-only view (no CRUD) without admin.metamodel", () => {
    wrap(makeUser({ "grc.view": true }));
    expect(screen.queryByTestId("standards-admin")).not.toBeInTheDocument();
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "@/hooks/AuthContext";
import type { User } from "@/types";

// The admin CRUD component is rendered for privileged users; stub it so the
// test asserts only the gating decision, not the admin component internals.
vi.mock("@/features/admin/PrinciplesAdmin", () => ({
  default: () => <div data-testid="principles-admin">admin crud</div>,
}));

// The read-only branch fetches principles on mount — keep it network-free.
vi.mock("@/api/client", () => ({
  api: { get: vi.fn().mockResolvedValue([]) },
}));

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

function wrap(user: User) {
  return render(
    <MemoryRouter>
      <AuthProvider user={user} refreshUser={async () => {}}>
        <PrinciplesPanel />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("PrinciplesPanel gating", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders the full CRUD admin UI for users with admin.metamodel", () => {
    wrap(makeUser({ "admin.metamodel": true }));
    expect(screen.getByTestId("principles-admin")).toBeInTheDocument();
  });

  it("renders the full CRUD admin UI for wildcard users", () => {
    wrap(makeUser({ "*": true }));
    expect(screen.getByTestId("principles-admin")).toBeInTheDocument();
  });

  it("renders the read-only view (no CRUD) without admin.metamodel", () => {
    wrap(makeUser({ "grc.view": true }));
    expect(screen.queryByTestId("principles-admin")).not.toBeInTheDocument();
  });
});

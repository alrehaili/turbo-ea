/**
 * [FORK] The grouped top bar as a user meets it: seven entries, the layer
 * rows with their summary action, the Reports filter box, and extension
 * routes that asked for the GRC group landing inside Governance.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";

vi.mock("@/api/client", () => import("@/test/apiMock").then((m) => m.apiClientModule()));
vi.mock("@/hooks/useMetamodel", () => import("@/test/hooks").then((m) => m.useMetamodelModule()));
vi.mock("@/hooks/useBpmEnabled", () => import("@/test/hooks").then((m) => m.useBpmEnabledModule()));
vi.mock("@/hooks/useGrcEnabled", () => import("@/test/hooks").then((m) => m.useGrcEnabledModule()));
vi.mock("@/hooks/usePpmEnabled", () => import("@/test/hooks").then((m) => m.usePpmEnabledModule()));
vi.mock("@/hooks/useTurboLensReady", () =>
  import("@/test/hooks").then((m) => m.useTurboLensReadyModule()),
);
vi.mock("@/hooks/useThemeMode", () => import("@/test/hooks").then((m) => m.useThemeModeModule()));
vi.mock("@/hooks/useEventStream", () => import("@/test/hooks").then((m) => m.useEventStreamModule()));

const profile = vi.hoisted(() => ({ current: "nora" as "nora" | "togaf" }));
vi.mock("@/hooks/useFrameworkProfile", () => ({
  useFrameworkProfile: () => ({ profile: profile.current, invalidateProfile: () => {} }),
}));
vi.mock("@/hooks/useActiveReferenceModels", () => ({
  useActiveReferenceModels: () => ({ summary: {} }),
}));
vi.mock("@/hooks/useSponsorButtonEnabled", () => ({
  useSponsorButtonEnabled: () => ({ sponsorButtonEnabled: false, loaded: true }),
}));
vi.mock("@/hooks/useEnabledLocales", () => ({
  useEnabledLocales: () => ({ enabledLocales: ["en"] }),
}));
vi.mock("@/hooks/useAppTitle", () => ({ useAppTitle: () => "Turbo EA" }));
vi.mock("@/hooks/useNavbarStyle", () => ({
  useNavbarStyle: () => ({ bg: "#1a1a2e", fg: "#ffffff" }),
}));
vi.mock("@/components/NotificationBell", () => ({
  default: () => <div data-testid="notification-bell" />,
}));

import AppLayout from "./AppLayout";
import { AuthProvider } from "@/hooks/AuthContext";
import { mockApi } from "@/test/apiMock";
import { hookState } from "@/test/hooks";
import { setViewportWidth } from "@/test/matchMedia";
import {
  registerExtension,
  resetExtensionHost,
  UI_SDK_VERSION,
  type ExtensionRouteContribution,
} from "@/lib/extensionHost";
import type { User } from "@/types";

type LayoutUser = Parameters<typeof AppLayout>[0]["user"];

const adminUser: LayoutUser = {
  id: "u1",
  display_name: "Admin User",
  email: "admin@turboea.local",
  role: "admin",
  permissions: { "*": true },
};

function userWithPerms(...perms: string[]): LayoutUser {
  return {
    id: "u5",
    display_name: "Scoped User",
    email: "scoped@turboea.local",
    role: "member",
    permissions: Object.fromEntries(perms.map((p) => [p, true])),
  };
}

function Where() {
  return <div data-testid="location">{useLocation().pathname}</div>;
}

function Layout({ user = adminUser }: { user?: LayoutUser }) {
  return (
    <MemoryRouter initialEntries={["/"]}>
      <AuthProvider user={user as unknown as User} refreshUser={async () => {}}>
        <AppLayout user={user} onLogout={() => {}}>
          <Where />
        </AppLayout>
      </AuthProvider>
    </MemoryRouter>
  );
}

/** The bar's entries in order, by their visible label. */
function barLabels(): string[] {
  const nav = screen.getByRole("link", { name: /Dashboard/ }).parentElement as HTMLElement;
  return Array.from(nav.children).map((el) =>
    (el.textContent ?? "").replace(/^[a-z_0-9]+/, "").replace(/expand_more$/, ""),
  );
}

const menuLabels = () =>
  screen.getAllByRole("menuitem").map((el) => (el.textContent ?? "").replace(/^[a-z_0-9]+/, ""));

function registerRoutes(...routes: ExtensionRouteContribution[]) {
  registerExtension("test-ext", { key: "test-ext", sdkVersion: UI_SDK_VERSION, routes });
}

beforeEach(() => {
  hookState.reset();
  mockApi.reset();
  resetExtensionHost();
  profile.current = "nora";
  setViewportWidth(1440);
  mockApi.on("get", "/notifications/badge-counts", { open_todos: 0, pending_surveys: 0 });
  mockApi.on("get", "/extensions/status", []);
});

afterEach(() => resetExtensionHost());

describe("AppLayout — grouped bar", () => {
  it("shows seven entries on a laptop-width screen, with no hamburger", () => {
    render(<Layout />);
    expect(barLabels()).toEqual([
      "Dashboard",
      "Inventory",
      "Architecture",
      "Reports",
      "Governance",
      "Projects",
      "Todos",
    ]);
    expect(screen.queryByRole("button", { name: /^menu$/ })).not.toBeInTheDocument();
  });

  it("switches to the drawer below 1280px", () => {
    setViewportWidth(1200);
    render(<Layout />);
    expect(screen.getByRole("button", { name: /^menu$/ })).toBeInTheDocument();
  });

  it("drops a group whose every page the role cannot open", () => {
    render(<Layout user={userWithPerms("inventory.view")} />);
    expect(barLabels()).toEqual(["Dashboard", "Inventory", "Architecture", "Todos"]);
  });

  it("offers each layer's summary as a second action on the layer's row", async () => {
    const user = userEvent.setup();
    render(<Layout />);
    await user.click(screen.getByRole("button", { name: /Architecture/ }));
    expect(menuLabels()).toEqual(
      expect.arrayContaining(["Business Layer", "View Library", "Diagrams", "Business Processes"]),
    );
    expect(menuLabels()).not.toContain("Business Summary");

    await user.click(screen.getByRole("link", { name: "Business Summary" }));
    expect(screen.getByTestId("location")).toHaveTextContent("/layers/business-summary");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("drops the summary action, not the row, for a role that cannot open it", async () => {
    const user = userEvent.setup();
    // Security layer needs risks.view; its summary needs inventory.view.
    render(<Layout user={userWithPerms("risks.view")} />);
    await user.click(screen.getByRole("button", { name: /Architecture/ }));
    // View Library is ungated, so it is the only other entry.
    expect(menuLabels()).toEqual(["Security Layer", "View Library"]);
    expect(screen.queryByRole("link", { name: "Security Summary" })).not.toBeInTheDocument();
  });

  it("drops the NORA pages outside the NORA profile", async () => {
    profile.current = "togaf";
    const user = userEvent.setup();
    render(<Layout />);
    await user.click(screen.getByRole("button", { name: /Governance/ }));
    expect(menuLabels()).not.toContain("NORA Program");
    expect(menuLabels()).not.toContain("EA Maturity");
    expect(menuLabels()).toContain("Risk & Compliance");
  });

  it("drops a page whose module is off from inside its group", async () => {
    hookState.bpm = { ...hookState.bpm, bpmEnabled: false };
    hookState.grc = { ...hookState.grc, grcEnabled: false };
    const user = userEvent.setup();
    render(<Layout />);
    await user.click(screen.getByRole("button", { name: /Architecture/ }));
    expect(menuLabels()).not.toContain("Business Processes");
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: /Governance/ }));
    expect(menuLabels()).not.toContain("Risk & Compliance");
  });
});

describe("AppLayout — Reports dropdown", () => {
  it("lists Saved Reports first and filters as you type", async () => {
    const user = userEvent.setup();
    render(<Layout />);
    await user.click(screen.getByRole("button", { name: /Reports/ }));
    expect(menuLabels()[0]).toBe("Saved Reports");

    const box = screen.getByRole("textbox", { name: "Filter…" });
    expect(box).toHaveFocus();
    await user.type(box, "gap");
    expect(menuLabels()).toEqual(["Gap Analysis", "Gap Summary", "Initiative Gaps"]);

    await user.clear(box);
    await user.type(box, "zzz");
    expect(screen.queryAllByRole("menuitem")).toHaveLength(0);
    expect(screen.getByText("No matches")).toBeInTheDocument();
  });

  it("starts each opening with an empty filter", async () => {
    const user = userEvent.setup();
    render(<Layout />);
    await user.click(screen.getByRole("button", { name: /Reports/ }));
    await user.type(screen.getByRole("textbox", { name: "Filter…" }), "gap");
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: /Reports/ }));
    expect(screen.getByRole("textbox", { name: "Filter…" })).toHaveValue("");
  });

  it("has no filter box on a short dropdown", async () => {
    const user = userEvent.setup();
    render(<Layout />);
    await user.click(screen.getByRole("button", { name: /Governance/ }));
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });
});

describe("AppLayout — GRC extension routes inside Governance", () => {
  const route: ExtensionRouteContribution = {
    id: "audit",
    path: "/ext/test-ext/audit",
    label: "Audit Trail",
    icon: "star",
    component: () => null,
    navGroup: "grc",
  };

  it("sits right after the GRC entry", async () => {
    registerRoutes(route);
    const user = userEvent.setup();
    render(<Layout />);
    await user.click(screen.getByRole("button", { name: /Governance/ }));
    const labels = menuLabels();
    expect(labels[labels.indexOf("Risk & Compliance") + 1]).toBe("Audit Trail");
    await user.keyboard("{Escape}");
    expect(barLabels()).not.toContain("Audit Trail");
  });

  it("falls back to the bar when GRC is off", () => {
    hookState.grc = { ...hookState.grc, grcEnabled: false };
    registerRoutes(route);
    render(<Layout />);
    expect(barLabels()).toContain("Audit Trail");
  });

  it("falls back to the bar for a role that cannot open GRC", () => {
    registerRoutes(route);
    render(<Layout user={userWithPerms("arb.view")} />);
    expect(barLabels()).toEqual(["Dashboard", "Architecture", "Governance", "Todos", "Audit Trail"]);
  });
});

describe("AppLayout — drawer", () => {
  it("lists the summary under its layer and Saved Reports first", async () => {
    setViewportWidth(900);
    const user = userEvent.setup();
    render(<Layout />);
    await user.click(screen.getByRole("button", { name: /^menu$/ }));
    const drawer = screen.getByRole("presentation");
    await user.click(within(drawer).getByText("Architecture"));
    await user.click(within(drawer).getByText("Business Summary"));
    expect(screen.getByTestId("location")).toHaveTextContent("/layers/business-summary");
  });
});

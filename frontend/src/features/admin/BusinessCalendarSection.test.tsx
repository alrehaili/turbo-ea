import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const get = vi.fn();
const put = vi.fn();
const post = vi.fn();
vi.mock("@/api/client", () => ({
  api: {
    get: (...a: unknown[]) => get(...a),
    put: (...a: unknown[]) => put(...a),
    post: (...a: unknown[]) => post(...a),
  },
}));

let allowed = true;
vi.mock("@/hooks/AuthContext", () => ({
  useOptionalAuthUser: () => null,
  useAuthContext: () => ({ user: { id: "u1", permissions: {} } }),
}));
vi.mock("@/hooks/usePermissions", () => ({
  usePermissions: () => ({ can: (p: string) => allowed && p === "admin.business_calendar" }),
}));

import BusinessCalendarSection from "./BusinessCalendarSection";

const YEAR = new Date().getFullYear();

function listing(confirmed: boolean) {
  return {
    fiscal_year_start: 1,
    default_working_weekdays: [7, 1, 2, 3, 4],
    years: [
      {
        fiscal_year: YEAR,
        starts: `${YEAR}-01-01`,
        ends: `${YEAR}-12-31`,
        working_weekdays: [7, 1, 2, 3, 4],
        holidays: [{ date: `${YEAR}-09-23`, name: "National Day" }],
        confirmed,
        confirmed_at: null,
      },
    ],
  };
}

beforeEach(() => {
  allowed = true;
  get.mockReset().mockResolvedValue(listing(false));
  put.mockReset().mockResolvedValue({});
  post.mockReset().mockResolvedValue({});
});

describe("BusinessCalendarSection", () => {
  it("renders nothing without the calendar permission", () => {
    allowed = false;
    const { container } = render(<BusinessCalendarSection />);
    expect(container).toBeEmptyDOMElement();
    expect(get).not.toHaveBeenCalled();
  });

  it("shows the year's week, holidays and confirmation state", async () => {
    render(<BusinessCalendarSection />);
    expect(await screen.findByDisplayValue("National Day")).toBeInTheDocument();
    expect(screen.getByTestId("calendar-status")).toHaveTextContent("Not confirmed");
    expect(screen.getByLabelText("Sunday")).toBeChecked();
    expect(screen.getByLabelText("Thursday")).toBeChecked();
    expect(screen.getByLabelText("Friday")).not.toBeChecked();
  });

  it("saves the working week and holidays for the selected fiscal year", async () => {
    render(<BusinessCalendarSection />);
    await screen.findByDisplayValue("National Day");
    fireEvent.click(screen.getByRole("button", { name: "Add holiday" }));
    const names = screen.getAllByLabelText("Holiday");
    fireEvent.change(names[1], { target: { value: "Founding Day" } });
    const dates = screen.getAllByLabelText("Date");
    fireEvent.change(dates[1], { target: { value: `${YEAR}-02-22` } });
    fireEvent.click(screen.getByRole("button", { name: "Save calendar" }));
    await waitFor(() =>
      expect(put).toHaveBeenCalledWith(`/business-calendar/${YEAR}`, {
        working_weekdays: [7, 1, 2, 3, 4],
        holidays: [
          { date: `${YEAR}-09-23`, name: "National Day" },
          { date: `${YEAR}-02-22`, name: "Founding Day" },
        ],
      }),
    );
  });

  it("confirms an unconfirmed year and offers to withdraw a confirmed one", async () => {
    render(<BusinessCalendarSection />);
    fireEvent.click(await screen.findByRole("button", { name: "Confirm calendar" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(`/business-calendar/${YEAR}/confirm`, {}));
  });

  it("warns that editing a confirmed year withdraws the confirmation", async () => {
    get.mockResolvedValue(listing(true));
    render(<BusinessCalendarSection />);
    expect(await screen.findByText(/withdraws the confirmation/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Withdraw confirmation" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm calendar" })).toBeNull();
  });
});

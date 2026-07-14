import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

vi.mock("@/api/client", () => ({ api: { get: vi.fn(), patch: vi.fn() } }));

import { GroupTranslationsDialog } from "./CardLayoutEditor";

describe("GroupTranslationsDialog — group header translation authoring", () => {
  it("prefills existing translations and emits the edited per-locale map on save", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(
      <GroupTranslationsDialog
        groupName="Dimension One"
        initial={{ ar: "البعد الأول" }}
        onClose={() => {}}
        onSave={onSave}
      />,
    );

    // Existing Arabic translation is prefilled (fork ships EN/AR only).
    expect(screen.getByDisplayValue("البعد الأول")).toBeInTheDocument();
    // The raw group name is the placeholder / fallback (not a stored value).
    expect(screen.getByLabelText("English")).toHaveValue("");

    // Author an English override and save.
    await user.type(screen.getByLabelText("English"), "Dimension One EN");
    await user.click(screen.getByRole("button", { name: /^Save$/ }));

    expect(onSave).toHaveBeenCalledTimes(1);
    const map = onSave.mock.calls[0][0] as Record<string, string>;
    expect(map.ar).toBe("البعد الأول");
    expect(map.en).toBe("Dimension One EN");
  });
});

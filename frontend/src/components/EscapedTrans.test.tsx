import { render } from "@testing-library/react";
import { useTranslation } from "react-i18next";
import { describe, expect, it } from "vitest";

import EscapedTrans from "./EscapedTrans";

// "Select diagrams to link to <strong>{{name}}</strong>. A diagram can be …"
function Line({ name, components }: { name: string; components?: Parameters<typeof EscapedTrans>[0]["components"] }) {
  const { t } = useTranslation(["delivery"]);
  return (
    <p>
      <EscapedTrans
        t={t}
        i18nKey="linkDialog.description"
        values={{ name }}
        components={components}
      />
    </p>
  );
}

function strong(name: string): HTMLElement {
  const el = render(<Line name={name} />).container.querySelector("strong");
  expect(el).not.toBeNull();
  return el as HTMLElement;
}

describe("EscapedTrans", () => {
  it("renders the translation's own markup as elements, in the caller's namespace", () => {
    const { container } = render(<Line name="Cloud Migration" />);
    expect(container.textContent).toBe(
      "Select diagrams to link to Cloud Migration. A diagram can be linked to multiple initiatives.",
    );
    expect(container.querySelector("strong")).toHaveTextContent(/^Cloud Migration$/);
  });

  it.each([
    // Tags Trans keeps as elements: a bare <Trans values> would render these.
    "x <strong>y</strong>",
    "R&D <i>pilot</i>",
    "a<br/>b",
    // A tag it does not keep, with a handler.
    '<img src="x" onerror="window.__xss=1">',
    // Entities stay as typed, never decoded once more.
    "a &amp; b",
    "1 < 2 > 0",
  ])("shows the value %j exactly as typed, creating no element from it", (name) => {
    const el = strong(name);
    expect(el.textContent).toBe(name);
    expect(el.children).toHaveLength(0);
  });

  it("takes the caller's component map", () => {
    const { container } = render(<Line name="N" components={{ strong: <em /> }} />);
    expect(container.querySelector("strong")).toBeNull();
    expect(container.querySelector("em")).toHaveTextContent(/^N$/);
  });
});

import DOMPurify from "dompurify";
import { describe, expect, it, vi } from "vitest";

import * as linkify from "./linkify";
import { looksLikeHtml, richHtmlToText, sanitizeRichHtml } from "./richHtml";

describe("looksLikeHtml", () => {
  it.each([
    ["<p>x</p>", true],
    ["a</strong>", true],
    ["line<br/>", true],
    ["<B>loud</B>", true],
    ["plain text", false],
    ["2 < 3 and 4 > 1", false],
    ["< p>", false],
    ["<3 you", false],
    ["", false],
    [null, false],
    [undefined, false],
  ])("%j → %s", (text, expected) => {
    expect(looksLikeHtml(text)).toBe(expected);
  });
});

describe("richHtmlToText", () => {
  it("returns a value without markup unchanged, whitespace included", () => {
    expect(richHtmlToText("  a  &amp;\n b ")).toBe("  a  &amp;\n b ");
  });

  it("drops tags, decodes entities and breaks words at block ends", () => {
    expect(
      richHtmlToText(
        "<p><strong>SYNTHETIC</strong> record &amp; test.</p><p>Scope:\n  goals.</p>" +
          "<ul><li>one</li><li>two</li></ul>a<br>b<h2>H</h2><div>d</div><table><tr><td>c1</td><td>c2</td></tr></table>",
      ),
    ).toBe("SYNTHETIC record & test. Scope: goals. one two a b H d c1 c2");
  });

  it("keeps inline elements joined to their word", () => {
    expect(richHtmlToText("<p>re<em>ad</em>able</p>")).toBe("readable");
  });

  it("never runs what it parses", () => {
    const spy = vi.fn();
    (window as unknown as { __pwn: () => void }).__pwn = spy;
    expect(richHtmlToText('<img src=x onerror="__pwn()"><p>safe</p>')).toBe("safe");
    expect(spy).not.toHaveBeenCalled();
  });
});

function anchors(html: string): HTMLAnchorElement[] {
  const div = document.createElement("div");
  div.innerHTML = html;
  return Array.from(div.querySelectorAll("a"));
}

describe("sanitizeRichHtml", () => {
  it("builds its private sanitiser once, so the hook is added once", async () => {
    vi.resetModules();
    const actual = await vi.importActual<typeof import("dompurify")>("dompurify");
    const create = vi.fn((w: Window) => actual.default(w));
    vi.doMock("dompurify", () => ({ default: create }));
    // The module already loaded, not a fresh evaluation: a test that runs
    // linkify's module body would make its constants look test-covered.
    vi.doMock("./linkify", () => linkify);
    try {
      const { sanitizeRichHtml: fresh } = await import("./richHtml");
      fresh("<p>one</p>");
      fresh("<p>two</p>");
      expect(create).toHaveBeenCalledTimes(1);
    } finally {
      vi.doUnmock("dompurify");
      vi.doUnmock("./linkify");
      vi.resetModules();
    }
  });

  it("returns an empty string for nothing", () => {
    expect(sanitizeRichHtml("")).toBe("");
    expect(sanitizeRichHtml(null)).toBe("");
    expect(sanitizeRichHtml(undefined)).toBe("");
  });

  it("makes a stored anchor open in a new tab", () => {
    const [a] = anchors(sanitizeRichHtml('<p><a href="https://x.io">x</a></p>'));
    expect(a.getAttribute("href")).toBe("https://x.io");
    expect(a.getAttribute("target")).toBe("_blank");
    expect(a.getAttribute("rel")).toBe("noopener noreferrer");
  });

  it("overrides a stored target and rel", () => {
    const [a] = anchors(
      sanitizeRichHtml('<a href="https://x.io" target="_self" rel="opener">x</a>'),
    );
    expect(a.getAttribute("target")).toBe("_blank");
    expect(a.getAttribute("rel")).toBe("noopener noreferrer");
  });

  it("keeps a mailto anchor", () => {
    const [a] = anchors(sanitizeRichHtml('<a href="mailto:ops@x.io">mail</a>'));
    expect(a.getAttribute("href")).toBe("mailto:ops@x.io");
    expect(a.getAttribute("target")).toBe("_blank");
  });

  it("strips the href from an anchor with a disallowed scheme or a relative path", () => {
    for (const href of ["javascript:alert(1)", "/cards/1", "ftp://x.io", ""]) {
      const [a] = anchors(sanitizeRichHtml(`<a href="${href}" target="_blank">x</a>`));
      expect(a).toBeDefined();
      expect(a.hasAttribute("href")).toBe(false);
      expect(a.hasAttribute("target")).toBe(false);
    }
  });

  it("trims an href before deciding whether it may stay", () => {
    const [a] = anchors(sanitizeRichHtml('<a href=" https://x.io">x</a>'));
    expect(a.getAttribute("href")?.trim()).toBe("https://x.io");
    expect(a.getAttribute("target")).toBe("_blank");
  });

  it("drops a stored rel along with a disallowed href", () => {
    const [a] = anchors(sanitizeRichHtml('<a href="javascript:alert(1)" rel="opener">x</a>'));
    expect(a.hasAttribute("href")).toBe(false);
    expect(a.hasAttribute("rel")).toBe(false);
  });

  it("leaves elements other than anchors alone", () => {
    const html = '<map name="m"><area href="https://x.io" target="_self" alt="a"></map>';
    expect(sanitizeRichHtml(html)).toBe(html);
  });

  it("links a text node that is nothing but a URL", () => {
    const [a] = anchors(sanitizeRichHtml("<p>https://x.io</p>"));
    expect(a.getAttribute("href")).toBe("https://x.io");
  });

  it("links a bare URL in a text node and hands punctuation back", () => {
    const out = sanitizeRichHtml("<p>see https://x.io/doc. Then</p>");
    const [a] = anchors(out);
    expect(a.getAttribute("href")).toBe("https://x.io/doc");
    expect(a.textContent).toBe("https://x.io/doc");
    expect(a.getAttribute("target")).toBe("_blank");
    expect(out).toContain("</a>. Then");
  });

  it("does not wrap a URL that is already inside an anchor", () => {
    const out = sanitizeRichHtml('<p><a href="https://x.io">https://x.io</a></p>');
    expect(anchors(out)).toHaveLength(1);
  });

  it("links inside nested markup, across several text nodes", () => {
    const out = sanitizeRichHtml(
      "<ul><li>one https://a.io</li><li><strong>two</strong> https://b.io</li></ul>",
    );
    expect(anchors(out).map((a) => a.getAttribute("href"))).toEqual([
      "https://a.io",
      "https://b.io",
    ]);
  });

  it("still strips scripts and event handlers", () => {
    const out = sanitizeRichHtml(
      '<p>x https://a.io<script>alert(1)</script><img src=x onerror="alert(1)"></p>',
    );
    expect(out).not.toContain("<script");
    expect(out).not.toContain("onerror");
    expect(anchors(out)).toHaveLength(1);
  });

  it("is idempotent", () => {
    const once = sanitizeRichHtml("<p>go https://x.io now</p>");
    expect(sanitizeRichHtml(once)).toBe(once);
  });

  it("leaves the global DOMPurify instance without the anchor hook", () => {
    sanitizeRichHtml('<a href="https://x.io">x</a>');
    const [a] = anchors(DOMPurify.sanitize('<a href="https://x.io" target="_blank">x</a>'));
    // Default DOMPurify drops `target`; if the hook had leaked it would be
    // re-added here.
    expect(a.hasAttribute("target")).toBe(false);
  });
});

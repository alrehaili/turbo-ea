/**
 * The one sanitiser for stored rich text — ADR sections, SoAW sections, a
 * portal's card description — and the reason there is exactly one.
 *
 * DOMPurify's default allowlist keeps `href` and `rel` but drops `target`, so
 * a bare `DOMPurify.sanitize(html)` renders every anchor as a same-tab link
 * and quietly discards the `target="_blank"` the editor wrote. This wrapper
 * does three things every stored-HTML surface owes:
 *
 *   1. **Autolink** bare `http(s)://` addresses in text nodes (the same
 *      tokenizer free text uses, `lib/linkify.ts`), skipping text already
 *      inside an `<a>`. Documents written before the editor autolinked, and
 *      URLs pasted as plain text, become links when displayed.
 *   2. **Sanitise last**, so the anchors the autolinker created go through the
 *      same allowlist as the stored ones — one code path, one policy.
 *   3. **Stamp every anchor** `target="_blank" rel="noopener noreferrer"` when
 *      its href is http(s)/mailto, and strip the href otherwise. A stored
 *      `javascript:` or relative href never survives.
 *
 * It runs on a **private** DOMPurify instance: hooks are per instance, and
 * the SVG-thumbnail sanitisers (`ProcessNavigator`, `ProcessFlowTab`) must
 * not inherit an anchor hook. The pre-sanitise walk is safe because a
 * `DOMParser` document is inert — no scripts run, no subresources load.
 */
import createDOMPurify from "dompurify";

import { isLinkableHref, splitLinks } from "./linkify";

type Purifier = ReturnType<typeof createDOMPurify>;

let purifier: Purifier | null = null;

function getPurifier(): Purifier {
  if (purifier) return purifier;
  const p = createDOMPurify(window);
  p.addHook("afterSanitizeAttributes", (node) => {
    if (node.nodeName !== "A") return;
    // Stryker disable next-line StringLiteral: an absent href is unlinkable whatever it defaults to
    const href = node.getAttribute("href") ?? "";
    if (!isLinkableHref(href)) {
      node.removeAttribute("href");
      node.removeAttribute("target");
      node.removeAttribute("rel");
      return;
    }
    node.setAttribute("target", "_blank");
    node.setAttribute("rel", "noopener noreferrer");
  });
  purifier = p;
  return p;
}

/** Wrap bare URLs found in text nodes that are not already inside an anchor. */
function autolinkTextNodes(html: string): string {
  const doc = new DOMParser().parseFromString(html, "text/html");
  const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT);
  // Collect first: replacing a node while the walker is on it skips its
  // successors.
  const targets: Text[] = [];
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const t = n as Text;
    // Stryker disable next-line OptionalChaining: a text node under <body> always has a parent element
    if (t.parentElement?.closest("a")) continue;
    targets.push(t);
  }
  for (const t of targets) {
    // A node with no link rebuilds as one identical text node.
    const frag = doc.createDocumentFragment();
    for (const tok of splitLinks(t.data)) {
      if (tok.type === "text") {
        frag.append(doc.createTextNode(tok.value));
      } else {
        const a = doc.createElement("a");
        a.setAttribute("href", tok.href);
        a.textContent = tok.value;
        frag.append(a);
      }
    }
    t.replaceWith(frag);
  }
  return doc.body.innerHTML;
}

/**
 * Whether a free-text value carries HTML markup (an opening or closing tag).
 * Card detail renders such a description as rich text; a plain-text surface
 * flattens it with {@link richHtmlToText}.
 */
export function looksLikeHtml(text: string | null | undefined): boolean {
  return !!text && /<\/?[a-z][^>]*>/i.test(text);
}

/** Elements whose start and end are word breaks once the markup is gone. */
const BREAKING = "p,div,br,li,tr,td,th,h1,h2,h3,h4,h5,h6,blockquote,pre,hr";

/**
 * The visible text of a value that may hold HTML, for a one-line surface
 * (a grid cell) that cannot lay out paragraphs. Tags are dropped, entities
 * decoded, each block edge becomes a space and runs of whitespace collapse.
 * A value without markup comes back unchanged. Parsing is inert (`DOMParser`):
 * nothing in the value runs or loads.
 */
export function richHtmlToText(text: string): string {
  if (!looksLikeHtml(text)) return text;
  const doc = new DOMParser().parseFromString(text, "text/html");
  for (const el of doc.body.querySelectorAll(BREAKING)) {
    el.before(" ");
    el.after(" ");
  }
  // Stryker disable next-line StringLiteral: <body> always has textContent
  return (doc.body.textContent ?? "").replace(/\s+/g, " ").trim();
}

/**
 * Sanitised HTML for `dangerouslySetInnerHTML`, with every link opening in a
 * new tab and every bare URL linked. Empty input gives `""`.
 */
export function sanitizeRichHtml(html: string | null | undefined): string {
  if (!html) return "";
  return getPurifier().sanitize(autolinkTextNodes(html), { ADD_ATTR: ["target"] });
}

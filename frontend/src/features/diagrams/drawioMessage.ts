/**
 * Whether a `message` event really comes from our embedded DrawIO frame.
 *
 * `window.addEventListener("message", …)` hears every window that holds a
 * reference to this one — a page that opened the app in a popup included — so
 * a listener that acts on the payload alone lets a foreign site drive it. The
 * editor's `exit` message saves whatever XML it carries, which made that a
 * cross-site write. A message is trusted only when it comes from the origin
 * DrawIO is served from **and** from the frame this component rendered: the
 * origin check alone would still admit another same-origin window.
 */
export function isFromDrawioFrame(
  event: MessageEvent,
  frame: HTMLIFrameElement | null,
  drawioUrl: string,
): boolean {
  const frameWindow = frame?.contentWindow;
  if (!frameWindow || event.source !== frameWindow) return false;
  let expectedOrigin: string;
  try {
    expectedOrigin = new URL(drawioUrl, window.location.href).origin;
  } catch {
    return false;
  }
  return event.origin === expectedOrigin;
}

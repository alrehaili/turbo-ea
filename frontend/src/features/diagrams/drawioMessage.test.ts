import { describe, expect, it } from "vitest";
import { isFromDrawioFrame } from "./drawioMessage";

function frameWith(contentWindow: unknown): HTMLIFrameElement {
  return { contentWindow } as unknown as HTMLIFrameElement;
}

function message(origin: string, source: unknown): MessageEvent {
  return { origin, source, data: "{}" } as unknown as MessageEvent;
}

describe("isFromDrawioFrame", () => {
  const frameWindow = { name: "drawio" };
  const frame = frameWith(frameWindow);
  const here = window.location.origin;

  it("accepts a message from our frame on the app's own origin", () => {
    expect(isFromDrawioFrame(message(here, frameWindow), frame, "/drawio/index.html")).toBe(true);
  });

  it("rejects a foreign origin even when the source is our frame", () => {
    const event = message("https://attacker.invalid", frameWindow);
    expect(isFromDrawioFrame(event, frame, "/drawio/index.html")).toBe(false);
  });

  it("rejects another same-origin window", () => {
    const event = message(here, { name: "other" });
    expect(isFromDrawioFrame(event, frame, "/drawio/index.html")).toBe(false);
  });

  it("rejects everything while there is no frame", () => {
    expect(isFromDrawioFrame(message(here, null), null, "/drawio/index.html")).toBe(false);
    expect(isFromDrawioFrame(message(here, null), frameWith(null), "/drawio/index.html")).toBe(
      false,
    );
  });

  it("expects the origin DrawIO is actually served from", () => {
    const url = "https://draw.example/index.html";
    expect(isFromDrawioFrame(message("https://draw.example", frameWindow), frame, url)).toBe(true);
    expect(isFromDrawioFrame(message(here, frameWindow), frame, url)).toBe(false);
  });

  it("rejects when the DrawIO address cannot be parsed", () => {
    expect(isFromDrawioFrame(message(here, frameWindow), frame, "http://[bad")).toBe(false);
  });
});

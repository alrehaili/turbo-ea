import i18n, { loadLanguage } from "./i18n"; // Initialize i18next before React renders
// Self-hosted Arabic-capable font (Cairo) — bundled by Vite so Arabic text
// renders correctly even when the device has no Arabic font and Google
// Fonts is unreachable. Latin text keeps using Inter (loaded in index.html);
// Cairo sits after it in the font stack and supplies the Arabic glyphs.
import "@fontsource/cairo/400.css";
import "@fontsource/cairo/500.css";
import "@fontsource/cairo/600.css";
import "@fontsource/cairo/700.css";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./print.css";
import { installAppUpdateGuard } from "./lib/appUpdateGuard";

installAppUpdateGuard();

// A saved non-English language is loaded before the first render, so the app
// never flashes English before switching (English itself is bundled).
void loadLanguage(i18n.language).finally(() => {
  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
});

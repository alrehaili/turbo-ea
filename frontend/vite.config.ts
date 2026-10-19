import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import fs from "fs";

const versionFile = [
  path.resolve(__dirname, "../VERSION"),
  path.resolve(__dirname, "VERSION"),
].find((f) => fs.existsSync(f));
const version = versionFile
  ? fs.readFileSync(versionFile, "utf-8").trim()
  : "0.0.0-dev";

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(version),
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    sourcemap: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        // The control panel (tools/control-panel) points this at the backend
        // port it runs; everyone else gets the usual :8000.
        target: process.env.TURBO_EA_API_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});

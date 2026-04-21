import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  plugins: [tailwindcss()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        "background/service-worker": resolve(__dirname, "src/background/service-worker.ts"),
        "content/gmail": resolve(__dirname, "src/content/gmail.ts"),
        "content/outlook": resolve(__dirname, "src/content/outlook.ts"),
        "content/yahoo": resolve(__dirname, "src/content/yahoo.ts"),
        "content/proton": resolve(__dirname, "src/content/proton.ts"),
        "content/fastmail": resolve(__dirname, "src/content/fastmail.ts"),
        "content/zimaapp": resolve(__dirname, "src/content/zimaapp.ts"),
        "popup/popup": resolve(__dirname, "src/popup/popup.tsx"),
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "chunks/[name]-[hash].js",
        assetFileNames: (assetInfo) => {
          if (assetInfo.name?.endsWith(".css")) return "popup/[name][extname]";
          return "[name][extname]";
        },
        format: "esm",
      },
    },
    // Content scripts cannot use dynamic imports — keep each entry self-contained
    modulePreload: { polyfill: false },
    target: "chrome120",
    sourcemap: true,
  },
  esbuild: {
    jsxImportSource: "react",
  },
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
});

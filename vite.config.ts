import adapter from "@sveltejs/adapter-static";
import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";

export default defineConfig({
  // Tauri loads a static SPA from disk: no server, every route falls back to index.html.
  plugins: [sveltekit({ adapter: adapter({ fallback: "index.html" }) })],
  clearScreen: false,
  server: { port: 1420, strictPort: true, watch: { ignored: ["**/src-tauri/**"] } },
  build: { chunkSizeWarningLimit: 6000 },
});

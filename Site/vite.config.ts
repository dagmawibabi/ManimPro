import adapter from "@sveltejs/adapter-static";
import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";

export default defineConfig({
  // A fully static site: every page is prerendered to plain HTML.
  plugins: [sveltekit({ adapter: adapter() })],
  server: { port: 5180 },
});

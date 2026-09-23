import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// Relative Pfade: gepackt laedt Electron die Seite per file://.
export default defineConfig({
  base: "./",
  plugins: [svelte()],
  build: { outDir: "dist", emptyOutDir: true, target: "chrome130" },
  server: { port: 5199, strictPort: true },
});

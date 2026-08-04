import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  // Relative base so the built app works under any subpath (e.g. GitHub Pages
  // project sites at /smartLearn-AI/), not just a domain root.
  base: "./",
  plugins: [react()],
})

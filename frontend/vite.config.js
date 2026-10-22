import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    // Recharts is most of the bundle and only two routes need it — split it out.
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/recharts") || id.includes("node_modules/d3-")) return "charts";
          if (id.includes("node_modules/react") || id.includes("node_modules/@tanstack")) return "vendor";
        },
      },
    },
  },
  server: {
    port: 5173,
    // Dev-only proxy so the browser talks to the same origin and CORS never bites.
    proxy: {
      "/api": {
        target: process.env.VITE_API_URL || "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Em desenvolvimento, /api é repassado para a API (sem CORS).
// No build, o painel é servido pela própria API em /painel/.
export default defineConfig({
  base: "/painel/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        rewrite: (caminho) => caminho.replace(/^\/api/, ""),
      },
    },
  },
});

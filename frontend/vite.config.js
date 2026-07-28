import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server port matches the compose-exposed port for a consistent URL.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});

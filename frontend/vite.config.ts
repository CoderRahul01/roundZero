import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@better-auth/utils/random": path.resolve(__dirname, "node_modules/@better-auth/utils/dist/random.mjs"),
      "@better-auth/utils/crypto": path.resolve(__dirname, "node_modules/@better-auth/utils/dist/crypto.mjs"),
      "@better-auth/utils/hash": path.resolve(__dirname, "node_modules/@better-auth/utils/dist/hash.mjs"),
      "@better-auth/utils/base64": path.resolve(__dirname, "node_modules/@better-auth/utils/dist/base64.mjs"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      // WebSocket: browser → Vite proxy → backend (avoids browser WS header quirks)
      '/ws': {
        target: 'ws://localhost:8080',
        ws: true,
        changeOrigin: true,
      },
      // HTTP API routes
      '/session': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/profile': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "build",
  },
});

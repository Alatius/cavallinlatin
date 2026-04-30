import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const apiTarget = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8001';

export default defineConfig({
  base: '/cavallinlatin/',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/cavallinlatin/api': {
        target: apiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/cavallinlatin/, ''),
      },
      '/cavallinlatin/columns': {
        target: apiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/cavallinlatin/, ''),
      },
    },
  },
});

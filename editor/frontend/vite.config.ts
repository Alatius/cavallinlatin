import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const apiTarget = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8001';

export default defineConfig({
  base: '/cavallinlatin/',
  plugins: [
    react(),
    {
      // React Router emits the home URL without a trailing slash
      // (`/cavallinlatin`), but Vite only matches the base with the
      // slash. Without this redirect, reloading the home page in dev
      // hits Vite's "did you mean /cavallinlatin/?" helper page.
      name: 'redirect-base-trailing-slash',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          const url = req.url ?? '';
          if (url === '/cavallinlatin'
              || url.startsWith('/cavallinlatin?')
              || url.startsWith('/cavallinlatin#')) {
            res.statusCode = 302;
            res.setHeader('Location', '/cavallinlatin/' + url.slice('/cavallinlatin'.length));
            res.end();
            return;
          }
          next();
        });
      },
    },
  ],
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

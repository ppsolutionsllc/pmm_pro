import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
const devProxyTarget = process.env.VITE_DEV_PROXY_TARGET || 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // listen on all addresses so Docker port mapping works
    port: 3000,
    proxy: {
      '/api': devProxyTarget,
    }
  }
});

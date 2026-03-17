import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // listen on all addresses so Docker port mapping works
    port: 3000,
    proxy: {
      // in Docker the backend runs on the internal service name
      '/api': 'http://backend:8000'
    }
  }
});

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        index: resolve(__dirname, 'index.html'),
        demo: resolve(__dirname, 'demo.html'),
        admin: resolve(__dirname, 'admin.html'),
        batch: resolve(__dirname, 'batch.html'),
      },
    },
  },
});

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The API and product images are served by the FastAPI backend on :8000.
// Proxying them keeps every request same-origin in development, so the browser
// never needs a CORS preflight and the frontend can use plain relative URLs.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/media': 'http://localhost:8000',
    },
  },
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// All API requests go through port 5173 via Vite proxy.
// This means ONLY port 5173 needs to be tunneled/exposed.
// The tunnel will then work for cross-device access.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: true,
    proxy: {
      // Auth Service
      '/auth': {
        target: 'http://127.0.0.1:3001',
        changeOrigin: true,
      },
      // Storage Service
      '/storage': {
        target: 'http://127.0.0.1:3003',
        changeOrigin: true,
      },
      // Encryption Service
      '/encrypt': {
        target: 'http://127.0.0.1:3002',
        changeOrigin: true,
      },
      '/decrypt': {
        target: 'http://127.0.0.1:3002',
        changeOrigin: true,
      },
      '/self-heal': {
        target: 'http://127.0.0.1:3002',
        changeOrigin: true,
      },
      // Risk Engine (Socket.IO + REST) - WebSocket must use ws: protocol in proxy
      '/socket.io': {
        target: 'http://127.0.0.1:3005',
        changeOrigin: true,
        ws: true,
      },
      '/ingest': {
        target: 'http://127.0.0.1:3005',
        changeOrigin: true,
      },
      '/inject-attack': {
        target: 'http://127.0.0.1:3005',
        changeOrigin: true,
      },
      // Anomaly ML Service
      '/analyze': {
        target: 'http://127.0.0.1:3004',
        changeOrigin: true,
      },
      // Notification Service (Socket.IO real-time alerts)
      '/notifications': {
        target: 'http://127.0.0.1:3006',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})

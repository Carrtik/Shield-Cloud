/**
 * ShieldCloud API Gateway
 * Runs on :8080 and proxies all microservice routes.
 * Local dev: http://localhost:8080
 * Vercel/Public: expose this port via cloudflared tunnel.
 *
 * Run: node gateway/index.js
 */

const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const http = require('http');

const app = express();
app.set('trust proxy', true);

// CORS for all origins (Vercel frontend + local dev)
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS,PATCH');
  res.header('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept');
  if (req.method === 'OPTIONS') return res.sendStatus(200);
  next();
});

// Health check
app.get('/health', (req, res) => res.json({ status: 'ok', service: 'ShieldCloud-Gateway' }));

const services = [
  { paths: ['/auth'],                              target: 'http://localhost:3001' },
  { paths: ['/storage'],                           target: 'http://localhost:3003' },
  { paths: ['/encrypt', '/decrypt', '/self-heal'], target: 'http://localhost:3002' },
  { paths: ['/ingest', '/inject-attack'],          target: 'http://localhost:3005' },
  { paths: ['/analyze'],                           target: 'http://localhost:3004' },
];

services.forEach(({ paths, target }) => {
  paths.forEach(path => {
    app.use(path, createProxyMiddleware({
      target,
      changeOrigin: true,
      logLevel: 'warn',
    }));
  });
});

// Socket.IO (WebSocket) proxy for Risk Engine
const socketProxy = createProxyMiddleware({
  target: 'http://localhost:3005',
  changeOrigin: true,
  ws: true,
  logLevel: 'warn',
});
app.use('/socket.io', socketProxy);

// Socket.IO (WebSocket) proxy for Notification Service
const notifProxy = createProxyMiddleware({
  target: 'http://localhost:3006',
  changeOrigin: true,
  ws: true,
  logLevel: 'warn',
});
app.use('/notifications', notifProxy);

const server = http.createServer(app);
server.on('upgrade', (req, socket, head) => {
  if (req.url && req.url.startsWith('/notifications')) {
    notifProxy.upgrade(req, socket, head);
  } else {
    socketProxy.upgrade(req, socket, head);
  }
});

const PORT = process.env.GATEWAY_PORT || 8080;
server.listen(PORT, '0.0.0.0', () => {
  console.log(`[Gateway] ShieldCloud API Gateway running on http://0.0.0.0:${PORT}`);
  console.log('[Gateway] Routes:');
  console.log('  /auth         -> :3001 (Auth Service)');
  console.log('  /storage      -> :3003 (Storage Service)');
  console.log('  /encrypt      -> :3002 (Encryption Service)');
  console.log('  /decrypt      -> :3002 (Encryption Service)');
  console.log('  /self-heal    -> :3002 (Encryption Service)');
  console.log('  /ingest       -> :3005 (Risk Engine)');
  console.log('  /socket.io    -> :3005 (Risk Engine WebSocket)');
  console.log('  /analyze      -> :3004 (Anomaly ML)');
});

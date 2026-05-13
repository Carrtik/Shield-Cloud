/**
 * Central API configuration.
 *
 * LOCAL dev  (Vite proxy): VITE_GATEWAY_URL is not set → uses relative paths
 *                          Vite proxies /auth, /storage, /encrypt, etc. → localhost microservices
 *
 * PROD (Cloudflare Tunnel): VITE_GATEWAY_URL=https://xxxx.trycloudflare.com
 *                          All requests prefixed with that URL → gateway → microservices
 */
const BASE = (import.meta.env.VITE_GATEWAY_URL as string) || '';

export const API = {
  auth:     `${BASE}/auth`,
  storage:  `${BASE}/storage`,
  encrypt:  `${BASE}`,          // /encrypt, /decrypt, /self-heal are top-level on enc service
  risk:     `${BASE}`,          // /ingest, /inject-attack
  // For Socket.IO - connect to same origin in dev; to gateway URL in prod
  socketUrl:     BASE || window.location.origin,
  notifSocketUrl: BASE || window.location.origin,
};

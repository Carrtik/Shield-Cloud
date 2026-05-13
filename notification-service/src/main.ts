/**
 * ShieldCloud Notification Service
 * - Real-time Socket.IO alerts to all connected dashboards
 * - Ethereal email preview (prints URL to console — open it in browser)
 * - Supports per-user context from RabbitMQ payload
 */
import * as amqp from 'amqplib';
import type { Connection, Channel, ConsumeMessage } from 'amqplib';
import nodemailer from 'nodemailer';
import { Server as SocketIOServer } from 'socket.io';
import { createServer } from 'http';

const RABBITMQ_URL = process.env.RABBITMQ_URL || 'amqp://guest:guest@localhost:5672';
const NOTIF_PORT = parseInt(process.env.NOTIF_PORT || '3006', 10);

// ── Socket.IO server ─────────────────────────────────────────────────────────
const httpServer = createServer();
const io = new SocketIOServer(httpServer, {
  cors: { origin: '*', methods: ['GET', 'POST'] },
  path: '/notifications',
});

io.on('connection', (socket) => {
  console.log('[Notification] Dashboard connected via Socket.IO:', socket.id);
  socket.on('disconnect', () => console.log('[Notification] Dashboard disconnected:', socket.id));
});

httpServer.listen(NOTIF_PORT, '0.0.0.0', () => {
  console.log(`[Notification] Socket.IO server running on http://0.0.0.0:${NOTIF_PORT}`);
});

// ── Ethereal transporter (preview URL in console) ────────────────────────────
let transporter: nodemailer.Transporter | null = null;
let etherealUser = '';

async function initTransporter(): Promise<void> {
  const account = await nodemailer.createTestAccount();
  etherealUser = account.user;
  transporter = nodemailer.createTransport({
    host: account.smtp.host,
    port: account.smtp.port,
    secure: account.smtp.secure,
    auth: { user: account.user, pass: account.pass },
  });
  console.log(`[Notification] Ethereal SMTP ready → ${account.user}`);
}

function generateTempPassword(): string {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789!@#$';
  return Array.from({ length: 12 }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
}

function formatBytes(b: number): string {
  if (!b) return '0 B';
  if (b < 1024) return `${b} B`;
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`;
  if (b < 1073741824) return `${(b / 1048576).toFixed(1)} MB`;
  return `${(b / 1073741824).toFixed(2)} GB`;
}

async function handleAlert(payload: Record<string, unknown>): Promise<void> {
  const score   = ((payload.anomaly_score as number) ?? 0);
  const pct     = (score * 100).toFixed(1);
  const geo     = ((payload.geo_velocity_kmh as number) ?? 0).toLocaleString();
  const bytes   = formatBytes((payload.bytes_transferred as number) ?? 0);
  const ts      = new Date(((payload.timestamp as number) ?? Date.now() / 1000) * 1000).toISOString();
  const userId  = (payload.user_id as string) ?? 'unknown';
  const tempPw  = generateTempPassword();

  // 1. Push real-time Socket.IO alert + force_logout to ALL connected clients
  const clients = io.engine.clientsCount;
  console.log(`[Notification] Broadcasting to ${clients} connected client(s)...`);
  io.emit('security_alert', {
    message: `🚨 HNDL Attack neutralized! Score: ${pct}% · All keys rotated · Re-login required`,
    anomaly_score: score,
    geo_velocity_kmh: payload.geo_velocity_kmh,
    timestamp: ts,
    user_id: userId,
    temp_password: tempPw,
  });
  io.emit('force_logout', {
    reason: 'HNDL attack detected. Your session has been terminated for security.',
    timestamp: ts,
    temp_password: tempPw,
  });

  // 2. Send Ethereal preview email
  if (!transporter) {
    console.error('[Notification] Transporter not ready — skipping email');
    return;
  }

  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
  body{margin:0;padding:0;background:#0D1117;font-family:Arial,sans-serif;color:#E6EDF3}
  .wrap{max-width:600px;margin:32px auto;background:#161B22;border-radius:12px;border:1px solid #30363D;overflow:hidden}
  .hdr{background:linear-gradient(135deg,#B91C1C,#7F1D1D);padding:28px;text-align:center}
  .hdr h1{font-size:22px;font-weight:900;margin:0}
  .hdr p{margin:6px 0 0;color:#FCA5A5;font-size:13px}
  .body{padding:28px}
  .badge{display:inline-block;background:#B91C1C22;border:1px solid #B91C1C;color:#FCA5A5;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;margin-bottom:20px}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:20px 0}
  .box{background:#0D1117;border:1px solid #21262D;border-radius:8px;padding:14px}
  .box label{display:block;font-size:10px;color:#8B949E;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px}
  .box value{font-size:17px;font-weight:700;color:#F85149}
  .ok{background:#0A2F1F;border:1px solid #238636;border-radius:8px;padding:14px;margin-top:16px}
  .ok h3{color:#3FB950;margin:0 0 8px;font-size:13px}
  .ok p{color:#7EE8A2;font-size:12px;margin:3px 0}
  .warn{background:#1A0E00;border:1px solid #F59E0B;border-radius:8px;padding:14px;margin-top:12px}
  .warn p{color:#FCD34D;font-size:12px;margin:3px 0}
  .pw-box{background:#1A1226;border:2px solid #7C3AED;border-radius:10px;padding:16px;margin-top:14px;text-align:center}
  .pw-box p{color:#A78BFA;font-size:11px;margin:0 0 8px;text-transform:uppercase;letter-spacing:.08em}
  .pw-box .pw{font-family:monospace;font-size:24px;font-weight:900;color:#DDD6FE;letter-spacing:.15em}
  .footer{padding:16px 28px;background:#0D1117;text-align:center;color:#484F58;font-size:11px}
</style></head>
<body><div class="wrap">
  <div class="hdr"><h1>🛡 ShieldCloud Security Alert</h1><p>Automated threat response — ${ts}</p></div>
  <div class="body">
    <span class="badge">CRITICAL THREAT NEUTRALIZED</span>
    <h2 style="margin:0 0 6px;font-size:17px">Harvest-Now-Decrypt-Later Attack Detected</h2>
    <p style="color:#8B949E;font-size:13px;margin:0">Your account's XGBoost ML anomaly detector flagged a suspicious access pattern.</p>
    <div class="grid">
      <div class="box"><label>ML Anomaly Score</label><value>${pct}%</value></div>
      <div class="box"><label>Geo Velocity</label><value>${geo} km/h</value></div>
      <div class="box"><label>Data Targeted</label><value style="font-size:13px">${bytes}</value></div>
      <div class="box"><label>Attack Vector</label><value style="font-size:12px">${payload.ip_location_mismatch ? 'Foreign IP / VPN' : 'Insider Threat'}</value></div>
    </div>
    <div class="ok">
      <h3>✅ Self-Healing Complete — Your Files Are Secure</h3>
      <p>• All AES-256-GCM encryption keys rotated</p>
      <p>• All ML-KEM-1024 (Kyber) keypairs regenerated</p>
      <p>• Your session terminated across all devices</p>
      <p>• Harvested ciphertext is now mathematically useless</p>
    </div>
    <div class="warn">
      <p><strong>⚠ ACTION REQUIRED:</strong> You have been signed out of all devices.</p>
      <p>Use the temporary password below to log back in, then update your password.</p>
    </div>
    <div class="pw-box">
      <p>Temporary Password (valid 24 hours)</p>
      <div class="pw">${tempPw}</div>
    </div>
    <p style="margin-top:20px;font-size:11px;color:#8B949E">User ID: ${userId} · Detected: ${ts}</p>
  </div>
  <div class="footer">ShieldCloud 2026 — Post-Quantum Cloud Security</div>
</div></body></html>`;

  try {
    const info = await transporter.sendMail({
      from: '"ShieldCloud Security" <no-reply@shieldcloud.io>',
      to:   etherealUser,   // Ethereal always delivers to test account
      subject: `[CRITICAL] HNDL Attack Neutralized — Re-login Required — ${ts}`,
      html,
    });
    const url = nodemailer.getTestMessageUrl(info);

    console.log('\n╔═══════════════════════════════════════════════════════════╗');
    console.log('║     SECURITY EMAIL SENT — CLICK THE URL BELOW            ║');
    console.log('╠═══════════════════════════════════════════════════════════╣');
    console.log(`║  ML Score : ${pct}%`.padEnd(62) + '║');
    console.log(`║  Temp PW  : ${tempPw}`.padEnd(62) + '║');
    console.log('╠═══════════════════════════════════════════════════════════╣');
    console.log('║  EMAIL PREVIEW (open in browser):'.padEnd(62) + '║');
    console.log(`║  ${String(url)}`.substring(0, 62).padEnd(62) + '║');
    console.log('╚═══════════════════════════════════════════════════════════╝\n');
  } catch (err) {
    console.error('[Notification] Email failed:', err);
  }
}

// ── RabbitMQ consumer ────────────────────────────────────────────────────────
async function startConsumer(): Promise<void> {
  await initTransporter();

  let retries = 0;
  while (true) {
    try {
      const conn = await amqp.connect(RABBITMQ_URL) as unknown as Connection;
      const ch   = await conn.createChannel() as unknown as Channel;
      retries = 0;

      // Declare both queues this service cares about
      await ch.assertQueue('risk.high',       { durable: true });
      await ch.assertQueue('healing.complete', { durable: true });
      await ch.prefetch(1);

      console.log('[Notification] Connected to RabbitMQ. Listening on risk.high ...');

      // *** AWAIT the consume calls so the consumer is fully registered ***
      await ch.consume('risk.high', async (msg: ConsumeMessage | null) => {
        if (!msg) return;
        console.log('[Notification] *** risk.high message received ***');
        try {
          const payload = JSON.parse(msg.content.toString()) as Record<string, unknown>;
          await handleAlert(payload);
          ch.ack(msg);
        } catch (e) {
          console.error('[Notification] Failed to handle alert:', e);
          ch.nack(msg, false, false);
        }
      }, { noAck: false });

      await ch.consume('healing.complete', async (msg: ConsumeMessage | null) => {
        if (!msg) return;
        try {
          const payload = JSON.parse(msg.content.toString()) as Record<string, unknown>;
          io.emit('healing_complete', { message: '✅ Key rotation complete. Your vault is secure.', timestamp: new Date().toISOString() });
          ch.ack(msg);
        } catch (e) {
          ch.nack(msg, false, false);
        }
      }, { noAck: false });

      // Keep alive — reconnect if connection drops
      await new Promise<void>((_, reject) => {
        (conn as any).on('error', reject);
        (conn as any).on('close', reject);
      });
    } catch (e) {
      retries++;
      const wait = Math.min(retries * 3, 30);
      console.log(`[Notification] RabbitMQ unavailable. Retry in ${wait}s... (attempt ${retries})`);
      await new Promise(r => setTimeout(r, wait * 1000));
    }
  }
}

startConsumer().catch(console.error);

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(16, 11))
ax.set_xlim(0, 16)
ax.set_ylim(0, 11)
ax.axis('off')
fig.patch.set_facecolor('white')

def box(x, y, w, h, title, sub='', fs=8.5):
    ax.add_patch(FancyBboxPatch((x,y), w, h,
        boxstyle="round,pad=0.08", lw=1.2,
        edgecolor='black', facecolor='white', zorder=2))
    if sub:
        ax.text(x+w/2, y+h*0.65, title, ha='center', va='center',
            fontsize=fs, fontweight='bold', zorder=3)
        ax.text(x+w/2, y+h*0.28, sub, ha='center', va='center',
            fontsize=6.5, fontstyle='italic', color='#222222', zorder=3)
    else:
        ax.text(x+w/2, y+h/2, title, ha='center', va='center',
            fontsize=fs, fontweight='bold', zorder=3)

def layer(x, y, w, h, label):
    ax.add_patch(FancyBboxPatch((x,y), w, h,
        boxstyle="round,pad=0.1", lw=1.8,
        edgecolor='black', facecolor='#efefef', zorder=1))
    ax.text(x+0.22, y+h/2, label, ha='center', va='center',
        fontsize=7, fontweight='bold', rotation=90, color='black', zorder=2)

def arr(x1, y1, x2, y2):
    ax.annotate('', xy=(x2,y2), xytext=(x1,y1),
        arrowprops=dict(arrowstyle='->', color='black', lw=1.2), zorder=4)

# ── LAYER BACKGROUNDS ─────────────────────────────────────────────────────────
layer(0.15, 8.8,  15.7, 1.9,  'INGESTION &\nEDGE LAYER')
layer(0.15, 6.3,  15.7, 2.2,  'CORE BUSINESS &\nCRYPTOGRAPHIC LAYER')
layer(0.15, 3.1,  15.7, 2.9,  'ANALYTICS &\nAUTONOMOUS\nMITIGATION LAYER')
layer(0.15, 0.2,  15.7, 2.65, 'PERSISTENCE\nTIER')

# ── LAYER 1: Ingestion & Edge ─────────────────────────────────────────────────
box(2.0,  9.1, 3.2, 1.3, 'Client Frontend',  'React/Vite — Port 5173')
box(7.5,  9.1, 3.2, 1.3, 'API Gateway',      'Express.js — Port 8080')

# ── LAYER 2: Core Business ────────────────────────────────────────────────────
box(0.8,  6.6, 3.0, 1.3, 'Auth Service',       'NestJS — Port 3001')
box(4.5,  6.6, 3.0, 1.3, 'Storage Service',    'NestJS — Port 3003')
box(8.2,  6.6, 3.8, 1.3, 'Encryption Service', 'FastAPI — Port 3002\nML-KEM-1024 | AES-256-GCM | liboqs')

# ── LAYER 3: Analytics ────────────────────────────────────────────────────────
box(0.8,  3.4, 3.0, 1.3, 'Anomaly ML Service',  'FastAPI — Port 3004\nXGBoost | 24 features')
box(4.5,  3.4, 3.0, 1.3, 'Risk Engine',          'FastAPI — Port 3005\nComposite Scoring')
box(8.2,  3.4, 3.0, 1.3, 'Notification Service', 'NestJS — Port 3006\nEmail | Socket.IO')
box(12.0, 3.4, 3.0, 1.3, 'Self-Healing\nWorker', 'Python Consumer\nrisk.heal queue')

# ── PERSISTENCE TIER ──────────────────────────────────────────────────────────
box(0.8,  0.5, 3.0, 1.4, 'PostgreSQL', 'kyber_ciphertext\nsk_Kyber | key_rotation_log')
box(4.5,  0.5, 3.0, 1.4, 'MinIO',      'Encrypted object blobs\nC_data | IV')
box(8.2,  0.5, 3.0, 1.4, 'Redis',      'Sliding-window counters\nEphemeral telemetry')
box(12.0, 0.5, 3.0, 1.4, 'RabbitMQ',  'Durable message broker\nrisk.high | risk.heal')

# ── ARROWS: Layer 1 → 2 ───────────────────────────────────────────────────────
arr(3.6,  9.1,  2.3,  7.9)    # Frontend → Auth
arr(9.1,  9.1,  6.0,  7.9)    # Gateway → Storage
arr(9.1,  9.1,  10.1, 7.9)    # Gateway → Encryption

# ── ARROWS: Layer 2 → 3 ───────────────────────────────────────────────────────
arr(2.3,  6.6,  2.3,  4.7)    # Auth → Anomaly ML
arr(6.0,  6.6,  6.0,  4.7)    # Storage → Risk Engine
arr(10.1, 6.6,  9.7,  4.7)    # Encryption → Notification

# ── ARROWS: Layer 3 internal ──────────────────────────────────────────────────
arr(3.8,  4.05, 4.5,  4.05)   # Anomaly → Risk Engine
arr(7.5,  4.05, 8.2,  4.05)   # Risk → Notification
arr(11.2, 4.05, 12.0, 4.05)   # Notification → Worker (via RabbitMQ)

# ── ARROWS: Layer 3 → Persistence ────────────────────────────────────────────
arr(2.3,  3.4,  2.3,  1.9)    # Anomaly ML → PostgreSQL
arr(6.0,  3.4,  6.0,  1.9)    # Risk Engine → MinIO
arr(9.7,  3.4,  9.7,  1.9)    # Notification → Redis
arr(13.5, 3.4,  13.5, 1.9)    # Worker → RabbitMQ

# ── SELF-HEALING LOOP ARROW ───────────────────────────────────────────────────
# Worker → back up to Encryption Service (curved)
ax.annotate('', xy=(12.0, 7.25), xytext=(13.5, 4.7),
    arrowprops=dict(
        arrowstyle='->',
        color='black',
        lw=1.5,
        connectionstyle='arc3,rad=-0.35'),
    zorder=4)

# Self-healing loop label
ax.text(15.4, 5.9, 'SELF-\nHEALING\nLOOP',
    ha='center', va='center', fontsize=7,
    fontweight='bold', color='black', zorder=5,
    bbox=dict(boxstyle='round,pad=0.3',
    facecolor='white', edgecolor='black', lw=1.2))

# ── TITLE ─────────────────────────────────────────────────────────────────────
ax.text(8.0, 10.88,
    'Shield Cloud — Nine-Service Microservices Architecture with MAPE-K Self-Healing Loop',
    ha='center', va='center', fontsize=11, fontweight='bold')

plt.tight_layout(pad=0.4)
plt.savefig('fig1_architecture.svg', format='svg', dpi=300, bbox_inches='tight')
plt.savefig('fig1_architecture.png', format='png', dpi=300, bbox_inches='tight')
print('Done — fig1_architecture.svg and fig1_architecture.png saved')

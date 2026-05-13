"""
generate_dataset.py
====================
Generates a rich, synthetic security access-log dataset for training the
XGBoost anomaly-detection model.

ATTACK TYPES SIMULATED
-----------------------
1. Harvest-Now-Decrypt-Later (HNDL) — mass bulk download + IP mismatch
2. Brute-Force Login             — many failed logins, then success
3. Credential Stuffing           — many users, many failures, low download
4. Insider Data Exfiltration     — legitimate user, huge bytes, odd hours
5. Normal traffic                — the majority of records (95 %)

COLUMN SCHEMA (CSV)
--------------------
timestamp               : int   — Unix epoch of the event
user_id                 : str   — UUID of the user making the request
action_type             : str   — login | upload | download | list | delete | share
hour_of_day             : int   — 0-23 extracted from timestamp
is_weekend              : int   — 1 if Saturday/Sunday, else 0
ip_location_mismatch    : int   — 1 if request country ≠ registered country
geo_velocity_kmh        : float — km/h between this login and last login location
download_count_last_1h  : int   — number of download operations in last 60 min
upload_count_last_1h    : int   — number of upload operations in last 60 min
bytes_transferred_last_1h: int  — total bytes in/out in last 60 min
failed_logins_last_1h   : int   — # failed auth attempts by this user in 1 h
failed_logins_last_24h  : int   — # failed auth attempts by this user in 24 h
unique_ips_last_24h     : int   — distinct source IPs used by user in 24 h
session_duration_min    : float — length of current session in minutes
file_size_bytes         : int   — size of file in the current operation (0 if N/A)
file_type_risk_score    : float — 0.0 (txt) → 1.0 (.kyber encrypted blob)
request_rate_per_min    : float — requests per minute from this IP
tor_exit_node           : int   — 1 if source IP belongs to known Tor exit list
vpn_detected            : int   — 1 if IP is flagged as a commercial VPN
user_agent_anomaly      : int   — 1 if user-agent differs from usual pattern
time_since_last_login_h : float — hours since the user's previous successful login
label_anomaly           : int   — 0 = normal, 1 = anomalous / attack
attack_type             : str   — NORMAL | HNDL | BRUTE_FORCE | CRED_STUFFING | EXFILTRATION
"""

import csv
import math
import random
import time
import uuid
from datetime import datetime, timedelta

# ── Config ────────────────────────────────────────────────────────────────────
NUM_RECORDS   = 10_000          # total rows to generate
ATTACK_RATIO  = 0.08            # 8% anomalies (realistic imbalance)
OUTPUT_FILE   = "access_logs.csv"
RANDOM_SEED   = 42
random.seed(RANDOM_SEED)

# ── Helpers ───────────────────────────────────────────────────────────────────
FILE_TYPE_RISK = {
    'txt':  0.1, 'pdf': 0.3, 'docx': 0.3, 'xlsx': 0.4,
    'zip':  0.6, 'tar': 0.6, 'exe':  0.8,
    'kyber': 1.0, 'bin': 0.9, 'db': 0.85
}

def rand_file_size_risk(action):
    """Return (file_size_bytes, file_type_risk_score) for a given action."""
    if action not in ('upload', 'download', 'share', 'delete'):
        return 0, 0.0
    ext = random.choice(list(FILE_TYPE_RISK.keys()))
    base = {
        'txt': (1_000, 500_000),
        'pdf': (50_000, 5_000_000),
        'docx': (30_000, 2_000_000),
        'xlsx': (50_000, 3_000_000),
        'zip': (1_000_000, 100_000_000),
        'tar': (1_000_000, 200_000_000),
        'exe': (500_000, 50_000_000),
        'kyber': (200_000, 10_000_000),
        'bin': (100_000, 500_000_000),
        'db': (500_000, 2_000_000_000),
    }
    lo, hi = base[ext]
    return random.randint(lo, hi), FILE_TYPE_RISK[ext]

def gen_normal_row(user, base_ts, i):
    ts = base_ts + i * random.randint(5, 60)
    dt = datetime.fromtimestamp(ts)
    action = random.choices(
        ['login', 'upload', 'download', 'list', 'delete', 'share'],
        weights=[15, 20, 30, 25, 5, 5]
    )[0]
    size, type_risk = rand_file_size_risk(action)
    dl = random.randint(1, 5) if action == 'download' else random.randint(0, 2)
    ul = random.randint(0, 3) if action == 'upload' else 0
    return {
        'timestamp': ts,
        'user_id': user,
        'action_type': action,
        'hour_of_day': dt.hour,
        'is_weekend': 1 if dt.weekday() >= 5 else 0,
        'ip_location_mismatch': 1 if random.random() < 0.005 else 0,
        'geo_velocity_kmh': round(random.uniform(0, 50), 2),
        'download_count_last_1h': dl,
        'upload_count_last_1h': ul,
        'bytes_transferred_last_1h': random.randint(1_024, 5_000_000),
        'failed_logins_last_1h': random.randint(0, 1) if action == 'login' else 0,
        'failed_logins_last_24h': random.randint(0, 2),
        'unique_ips_last_24h': random.randint(1, 2),
        'session_duration_min': round(random.uniform(1, 60), 2),
        'file_size_bytes': size,
        'file_type_risk_score': round(type_risk, 2),
        'request_rate_per_min': round(random.uniform(0.1, 3.0), 2),
        'tor_exit_node': 0,
        'vpn_detected': 1 if random.random() < 0.03 else 0,
        'user_agent_anomaly': 0,
        'time_since_last_login_h': round(random.uniform(0.5, 24), 2),
        'label_anomaly': 0,
        'attack_type': 'NORMAL',
    }

def gen_hndl_row(attacker, base_ts, i):
    """Harvest-Now-Decrypt-Later: bulk download from a foreign IP."""
    ts = base_ts + i * random.randint(1, 5)       # very fast requests
    dt = datetime.fromtimestamp(ts)
    return {
        'timestamp': ts,
        'user_id': attacker,
        'action_type': 'download',
        'hour_of_day': dt.hour,
        'is_weekend': 1 if dt.weekday() >= 5 else 0,
        'ip_location_mismatch': 1 if random.random() < 0.92 else 0,
        'geo_velocity_kmh': round(random.uniform(8_000, 15_000), 2),  # impossible speed
        'download_count_last_1h': random.randint(80, 500),
        'upload_count_last_1h': 0,
        'bytes_transferred_last_1h': random.randint(100_000_000, 1_073_741_824),  # 100MB–1GB
        'failed_logins_last_1h': 0,
        'failed_logins_last_24h': 0,
        'unique_ips_last_24h': random.randint(1, 3),
        'session_duration_min': round(random.uniform(60, 480), 2),
        'file_size_bytes': random.randint(5_000_000, 500_000_000),
        'file_type_risk_score': round(random.uniform(0.7, 1.0), 2),
        'request_rate_per_min': round(random.uniform(15, 80), 2),
        'tor_exit_node': 1 if random.random() < 0.5 else 0,
        'vpn_detected': 1 if random.random() < 0.6 else 0,
        'user_agent_anomaly': 1 if random.random() < 0.7 else 0,
        'time_since_last_login_h': round(random.uniform(0.01, 0.5), 2),
        'label_anomaly': 1,
        'attack_type': 'HNDL',
    }

def gen_brute_force_row(attacker, base_ts, i):
    """Brute-Force: many failed logins then sudden success."""
    ts = base_ts + i * random.randint(1, 10)
    dt = datetime.fromtimestamp(ts)
    failed = random.randint(5, 50)
    return {
        'timestamp': ts,
        'user_id': attacker,
        'action_type': 'login',
        'hour_of_day': dt.hour,
        'is_weekend': 1 if dt.weekday() >= 5 else 0,
        'ip_location_mismatch': 1 if random.random() < 0.7 else 0,
        'geo_velocity_kmh': round(random.uniform(0, 500), 2),
        'download_count_last_1h': 0,
        'upload_count_last_1h': 0,
        'bytes_transferred_last_1h': random.randint(0, 50_000),
        'failed_logins_last_1h': failed,
        'failed_logins_last_24h': failed + random.randint(10, 100),
        'unique_ips_last_24h': random.randint(1, 5),
        'session_duration_min': round(random.uniform(0, 5), 2),
        'file_size_bytes': 0,
        'file_type_risk_score': 0.0,
        'request_rate_per_min': round(random.uniform(5, 30), 2),
        'tor_exit_node': 1 if random.random() < 0.3 else 0,
        'vpn_detected': 1 if random.random() < 0.4 else 0,
        'user_agent_anomaly': 1 if random.random() < 0.5 else 0,
        'time_since_last_login_h': round(random.uniform(0, 0.1), 3),
        'label_anomaly': 1,
        'attack_type': 'BRUTE_FORCE',
    }

def gen_credential_stuffing_row(attacker, base_ts, i):
    """Credential Stuffing: same IP, many users, moderate failure rate."""
    ts = base_ts + i * random.randint(2, 15)
    dt = datetime.fromtimestamp(ts)
    return {
        'timestamp': ts,
        'user_id': attacker,
        'action_type': 'login',
        'hour_of_day': dt.hour,
        'is_weekend': 1 if dt.weekday() >= 5 else 0,
        'ip_location_mismatch': 1 if random.random() < 0.6 else 0,
        'geo_velocity_kmh': round(random.uniform(0, 3_000), 2),
        'download_count_last_1h': 0,
        'upload_count_last_1h': 0,
        'bytes_transferred_last_1h': random.randint(0, 200_000),
        'failed_logins_last_1h': random.randint(3, 20),
        'failed_logins_last_24h': random.randint(20, 200),
        'unique_ips_last_24h': random.randint(1, 8),
        'session_duration_min': round(random.uniform(0, 2), 2),
        'file_size_bytes': 0,
        'file_type_risk_score': 0.0,
        'request_rate_per_min': round(random.uniform(2, 15), 2),
        'tor_exit_node': 1 if random.random() < 0.4 else 0,
        'vpn_detected': 1 if random.random() < 0.5 else 0,
        'user_agent_anomaly': 1,
        'time_since_last_login_h': round(random.uniform(0, 0.3), 3),
        'label_anomaly': 1,
        'attack_type': 'CRED_STUFFING',
    }

def gen_exfiltration_row(insider, base_ts, i):
    """Insider Exfiltration: real user, huge bytes, night-time, risky files."""
    # Force it to night hours (00-05 or 22-23)
    hour = random.choice(list(range(0, 5)) + [22, 23])
    ts = base_ts + i * random.randint(10, 120)
    return {
        'timestamp': ts,
        'user_id': insider,
        'action_type': random.choice(['download', 'share', 'delete']),
        'hour_of_day': hour,
        'is_weekend': 1 if random.random() < 0.5 else 0,
        'ip_location_mismatch': 1 if random.random() < 0.4 else 0,
        'geo_velocity_kmh': round(random.uniform(0, 200), 2),
        'download_count_last_1h': random.randint(10, 100),
        'upload_count_last_1h': 0,
        'bytes_transferred_last_1h': random.randint(50_000_000, 800_000_000),
        'failed_logins_last_1h': 0,
        'failed_logins_last_24h': 0,
        'unique_ips_last_24h': random.randint(1, 2),
        'session_duration_min': round(random.uniform(120, 600), 2),
        'file_size_bytes': random.randint(10_000_000, 2_000_000_000),
        'file_type_risk_score': round(random.uniform(0.6, 1.0), 2),
        'request_rate_per_min': round(random.uniform(3, 20), 2),
        'tor_exit_node': 0,
        'vpn_detected': 1 if random.random() < 0.2 else 0,
        'user_agent_anomaly': 0,
        'time_since_last_login_h': round(random.uniform(0.1, 3), 2),
        'label_anomaly': 1,
        'attack_type': 'EXFILTRATION',
    }

FIELDNAMES = [
    'timestamp', 'user_id', 'action_type', 'hour_of_day', 'is_weekend',
    'ip_location_mismatch', 'geo_velocity_kmh',
    'download_count_last_1h', 'upload_count_last_1h',
    'bytes_transferred_last_1h',
    'failed_logins_last_1h', 'failed_logins_last_24h',
    'unique_ips_last_24h', 'session_duration_min',
    'file_size_bytes', 'file_type_risk_score',
    'request_rate_per_min', 'tor_exit_node', 'vpn_detected',
    'user_agent_anomaly', 'time_since_last_login_h',
    'label_anomaly', 'attack_type',
]

def generate_dataset(filename=OUTPUT_FILE):
    base_ts = int(time.time()) - (NUM_RECORDS * 60)
    users   = [str(uuid.uuid4()) for _ in range(100)]

    # Designate a few special actors
    hndl_attacker  = str(uuid.uuid4())
    brute_attacker = str(uuid.uuid4())
    stuff_attacker = str(uuid.uuid4())
    insiders       = [str(uuid.uuid4()) for _ in range(3)]

    rows = []

    # ── Inject attack bursts first ────────────────────────────────────────────
    num_attacks = int(NUM_RECORDS * ATTACK_RATIO)
    attack_split = num_attacks // 4   # share equally among 4 attack types

    for i in range(attack_split):
        rows.append(gen_hndl_row(hndl_attacker, base_ts, i))
    for i in range(attack_split):
        rows.append(gen_brute_force_row(brute_attacker, base_ts, i))
    for i in range(attack_split):
        rows.append(gen_credential_stuffing_row(stuff_attacker, base_ts, i))
    for i in range(attack_split):
        rows.append(gen_exfiltration_row(random.choice(insiders), base_ts, i))

    # ── Fill rest with normal traffic ─────────────────────────────────────────
    num_normal = NUM_RECORDS - len(rows)
    for i in range(num_normal):
        rows.append(gen_normal_row(random.choice(users), base_ts, i))

    # Shuffle so attacks are not all at the top
    random.shuffle(rows)

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    total_attacks = sum(1 for r in rows if r['label_anomaly'] == 1)
    print(f"Success: Dataset written to {filename}")
    print(f"  Total rows   : {len(rows)}")
    print(f"  Normal rows  : {len(rows) - total_attacks}")
    print(f"  Attack rows  : {total_attacks}  ({100*total_attacks/len(rows):.1f}%)")
    attack_breakdown = {}
    for r in rows:
        at = r['attack_type']
        attack_breakdown[at] = attack_breakdown.get(at, 0) + 1
    for k, v in attack_breakdown.items():
        print(f"    {k:<20}: {v}")


if __name__ == "__main__":
    generate_dataset()

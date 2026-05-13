# Shield Cloud — Post-Quantum Secured Self-Healing Cloud Environment

Autonomous cloud storage environment that protects against both 
contemporary threats and future quantum cryptanalysis.

## What it does

- **Hybrid encryption:** AES-256-GCM for data + CRYSTALS-Kyber 
  (ML-KEM-1024) for key encapsulation — NIST PQC standard
- **AI threat detection:** XGBoost model trained on 10,000 synthetic 
  attack logs, monitoring 20 behavioral vectors including geo-velocity, 
  API spike rates, and rolling byte transfers
- **Autonomous self-healing:** When anomaly score > 0.90, system 
  automatically severs connection, isolates account, rotates all keys — 
  within 8 seconds. No human intervention required.
- **Harvest Now Decrypt Later (HNDL) protection:** Exfiltrated 
  ciphertext becomes mathematically obsolete after key rotation

## Architecture

- MinIO object storage
- RabbitMQ event-driven architecture
- XGBoost risk engine with SMOTE class balancing
- Python-based cryptographic worker for key rotation
- Docker containerized deployment

## Cryptography

| Component | Algorithm |
|---|---|
| Bulk encryption | AES-256-GCM |
| Key encapsulation | CRYSTALS-Kyber / ML-KEM-1024 |
| Threat model | Shor's Algorithm resistant |

## Team

Final year capstone project — MS Ramaiah University of Applied 
Sciences, Department of CSE, April 2026.

- Adhithyan S
- Hrishikesh E  
- Kartik Nair
- Mohammed Sahis NP

Supervisor: Ms. S. Maragatham

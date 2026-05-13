-- ============================================================
--  ShieldCloud -- Live Database Demonstration Queries
--  Run these inside PostgreSQL to show the judges live data.
--
--  HOW TO CONNECT:
--    docker exec -it infra-postgres-1 psql -U postgres_user -d shieldcloud
--
--  OR from your machine (if psql is installed):
--    psql -h localhost -p 5432 -U postgres_user -d shieldcloud
--    Password: postgres_password
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- 1. SHOW ALL REGISTERED USERS
--    Proves the auth system is working and accounts are stored.
-- ────────────────────────────────────────────────────────────
SELECT
    id,
    email,
    role,
    risk_state,
    is_locked,
    created_at
FROM users
ORDER BY created_at DESC;


-- ────────────────────────────────────────────────────────────
-- 2. SHOW ALL ENCRYPTED FILES IN THE VAULT
--    See the quantum keys live in the database!
-- ────────────────────────────────────────────────────────────
SELECT
    f.id                                          AS file_id,
    f.original_name,
    f.size_bytes,
    f.key_version,
    f.minio_bucket,
    f.minio_key,
    left(f.encrypted_aes_key, 64)  || '...'      AS aes_key_preview,
    left(f.kyber_ciphertext, 80)   || '...'      AS kyber_key_preview,
    f.created_at
FROM files f
WHERE f.is_deleted = FALSE
ORDER BY f.created_at DESC;


-- ────────────────────────────────────────────────────────────
-- 3. SHOW THE FULL KYBER KEY FOR A SPECIFIC FILE
--    Paste a file ID from query 2.
--    This is the CRYSTALS-Kyber (ML-KEM-1024) lattice key.
--    It is immune to Shor's Algorithm.
-- ────────────────────────────────────────────────────────────
-- SELECT kyber_ciphertext FROM files WHERE id = 'PASTE-FILE-UUID-HERE';


-- ────────────────────────────────────────────────────────────
-- 4. KEY ROTATION LOG
--    After the self-healing fires, this table fills up with
--    a record for every file whose keys were rotated.
-- ────────────────────────────────────────────────────────────
SELECT
    krl.id,
    krl.file_id,
    krl.old_key_version,
    krl.new_key_version,
    krl.trigger_reason,
    krl.rotated_at
FROM key_rotation_log krl
ORDER BY krl.rotated_at DESC
LIMIT 20;


-- ────────────────────────────────────────────────────────────
-- 5. HEALING EVENTS
--    Shows every time the AI triggered a healing event.
-- ────────────────────────────────────────────────────────────
SELECT
    he.id,
    he.user_id,
    he.from_state,
    he.to_state,
    he.trigger_reason,
    he.risk_score,
    he.action_taken,
    he.timestamp
FROM healing_events he
ORDER BY he.timestamp DESC
LIMIT 10;


-- ────────────────────────────────────────────────────────────
-- 6. ACTIVITY LOG (ML anomaly scores per request)
--    Shows what ML score was given to each API request.
-- ────────────────────────────────────────────────────────────
SELECT
    al.action_type,
    al.ip_address,
    al.anomaly_score,
    al.risk_level,
    al.timestamp
FROM activity_log al
ORDER BY al.timestamp DESC
LIMIT 20;


-- ────────────────────────────────────────────────────────────
-- 7. FILE COUNT PER USER
--    Shows how many files each user has stored securely.
-- ────────────────────────────────────────────────────────────
SELECT
    u.email,
    COUNT(f.id)      AS total_files,
    SUM(f.size_bytes) AS total_bytes_stored
FROM users u
LEFT JOIN files f ON f.owner_id = u.id AND f.is_deleted = FALSE
GROUP BY u.email
ORDER BY total_files DESC;


-- ────────────────────────────────────────────────────────────
-- 8. LOCKED ACCOUNTS (after self-healing isolation)
--    Shows any accounts that were locked by the AI.
-- ────────────────────────────────────────────────────────────
SELECT
    id,
    email,
    is_locked,
    risk_state,
    updated_at
FROM users
WHERE is_locked = TRUE OR risk_state != 'NORMAL';


-- ────────────────────────────────────────────────────────────
-- 9. FULL AUDIT LOG
--    Every action ever taken in the system, immutable.
-- ────────────────────────────────────────────────────────────
SELECT
    al.action,
    al.target_type,
    al.target_id,
    al.metadata,
    al.timestamp
FROM audit_log al
ORDER BY al.timestamp DESC
LIMIT 20;


-- ────────────────────────────────────────────────────────────
-- 10. DATABASE SUMMARY (the big picture)
--     Run this at the START of your presentation to show
--     how much data is protected.
-- ────────────────────────────────────────────────────────────
SELECT
    (SELECT COUNT(*) FROM users)               AS total_users,
    (SELECT COUNT(*) FROM files WHERE is_deleted = FALSE) AS total_files,
    (SELECT COALESCE(SUM(size_bytes), 0) FROM files WHERE is_deleted = FALSE) AS total_bytes_protected,
    (SELECT COUNT(*) FROM key_rotation_log)    AS total_key_rotations,
    (SELECT COUNT(*) FROM healing_events)      AS total_healing_events,
    (SELECT COUNT(*) FROM audit_log)           AS total_audit_entries;

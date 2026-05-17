CREATE TYPE role_enum AS ENUM ('admin', 'user', 'auditor');
CREATE TYPE risk_state_enum AS ENUM ('NORMAL', 'SUSPICIOUS', 'ISOLATED', 'HEALING', 'RECOVERED');

-- users table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    mfa_secret VARCHAR,
    kyber_public_key TEXT,
    kyber_private_key_encrypted TEXT,
    role role_enum DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_locked BOOLEAN DEFAULT FALSE,
    risk_state risk_state_enum DEFAULT 'NORMAL'
);

-- files table
CREATE TABLE files (
    id UUID PRIMARY KEY,
    owner_id UUID REFERENCES users(id),
    original_name VARCHAR NOT NULL,
    stored_name VARCHAR NOT NULL,
    minio_bucket VARCHAR NOT NULL,
    minio_key VARCHAR NOT NULL,
    size_bytes BIGINT NOT NULL,
    encrypted_aes_key TEXT, -- DEPRECATED: retained for migration of pre-Kyber-fix files only. New files never populate this column.
    kyber_ciphertext VARCHAR(2200),
    kyber_public_key TEXT,
    key_version INTEGER DEFAULT 1,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- key_rotation_log table
CREATE TABLE key_rotation_log (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    file_id UUID REFERENCES files(id),
    old_key_version INTEGER,
    new_key_version INTEGER,
    trigger_reason VARCHAR,
    rotated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- activity_log table
CREATE TABLE activity_log (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    action_type VARCHAR NOT NULL,
    ip_address VARCHAR,
    geolocation VARCHAR,
    device_fingerprint VARCHAR,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    anomaly_score FLOAT,
    risk_level VARCHAR
);

-- healing_events table
CREATE TABLE healing_events (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    from_state VARCHAR,
    to_state VARCHAR,
    trigger_reason TEXT,
    risk_score FLOAT,
    action_taken TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved_by VARCHAR
);

-- audit_log table
CREATE TABLE audit_log (
    id UUID PRIMARY KEY,
    actor_id UUID,
    action VARCHAR NOT NULL,
    target_type VARCHAR,
    target_id UUID,
    metadata JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

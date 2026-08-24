-- FreeFlexVPN v2 A0 control database. Additive and safe to run repeatedly.
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK(status IN ('active','deletion_requested','deleted')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS api_claims (
    claim_hash TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    is_new_account INTEGER NOT NULL CHECK(is_new_account IN (0,1)),
    expires_at TEXT NOT NULL,
    consumed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(account_id) REFERENCES accounts(account_id)
);
CREATE TABLE IF NOT EXISTS api_sessions (
    session_hash TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(account_id) REFERENCES accounts(account_id)
);
CREATE INDEX IF NOT EXISTS api_sessions_account ON api_sessions(account_id, expires_at);
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    wg_public_key TEXT NOT NULL UNIQUE,
    server_id TEXT NOT NULL,
    assigned_address TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active','revocation_pending','revoked')),
    created_at TEXT NOT NULL,
    revoked_at TEXT,
    FOREIGN KEY(account_id) REFERENCES accounts(account_id)
);
CREATE INDEX IF NOT EXISTS devices_account ON devices(account_id, status);
CREATE TABLE IF NOT EXISTS peer_runtime (
    device_id TEXT PRIMARY KEY,
    server_id TEXT NOT NULL,
    counter_epoch INTEGER NOT NULL DEFAULT 0 CHECK(counter_epoch >= 0),
    handshake_at TEXT,
    rx_bytes INTEGER NOT NULL DEFAULT 0 CHECK(rx_bytes >= 0),
    tx_bytes INTEGER NOT NULL DEFAULT 0 CHECK(tx_bytes >= 0),
    observed_at TEXT NOT NULL,
    FOREIGN KEY(device_id) REFERENCES devices(device_id)
);
CREATE TABLE IF NOT EXISTS safety_observations (
    device_id TEXT PRIMARY KEY,
    os_family TEXT NOT NULL,
    dns_protected INTEGER CHECK(dns_protected IN (0,1)),
    ipv6_protected INTEGER CHECK(ipv6_protected IN (0,1)),
    kill_switch_protected INTEGER CHECK(kill_switch_protected IN (0,1)),
    observed_at TEXT NOT NULL,
    FOREIGN KEY(device_id) REFERENCES devices(device_id)
);
CREATE TABLE IF NOT EXISTS deletion_requests (
    request_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK(status IN ('requested','completed','rejected')),
    requested_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY(account_id) REFERENCES accounts(account_id)
);
CREATE TABLE IF NOT EXISTS deletion_status_tokens (
    request_id TEXT PRIMARY KEY,
    status_token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    FOREIGN KEY(request_id) REFERENCES deletion_requests(request_id)
);

CREATE TABLE IF NOT EXISTS wallet_entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    bucket TEXT NOT NULL CHECK(bucket IN ('free','earned','paid')),
    delta_bytes INTEGER NOT NULL CHECK(delta_bytes != 0),
    reason TEXT NOT NULL,
    idem_key TEXT NOT NULL UNIQUE,
    free_month TEXT,
    created_at TEXT NOT NULL,
    CHECK((bucket = 'free' AND free_month IS NOT NULL) OR
          (bucket != 'free' AND free_month IS NULL))
);
CREATE INDEX IF NOT EXISTS wallet_entries_account ON wallet_entries(account_id, bucket, free_month);
CREATE TABLE IF NOT EXISTS wallet_events (
    event_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS session_receipts (
    session_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    usage_event_id TEXT NOT NULL UNIQUE,
    used_bytes INTEGER NOT NULL CHECK(used_bytes > 0),
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS referral_tokens (
    token_hash TEXT PRIMARY KEY,
    inviter_id TEXT NOT NULL,
    issued_month TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    claimed_referral_id TEXT UNIQUE
);
CREATE INDEX IF NOT EXISTS referral_tokens_inviter ON referral_tokens(inviter_id, issued_month);
CREATE TABLE IF NOT EXISTS referrals (
    referral_id TEXT PRIMARY KEY,
    inviter_id TEXT NOT NULL,
    invitee_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK(status IN ('attributed','protected','rewarded','held')),
    created_month TEXT NOT NULL,
    reward_month TEXT,
    protected_at TEXT,
    rewarded_at TEXT,
    held_reason TEXT,
    created_at TEXT NOT NULL,
    CHECK(inviter_id != invitee_id)
);
CREATE INDEX IF NOT EXISTS referrals_inviter ON referrals(inviter_id, status, reward_month);
CREATE TABLE IF NOT EXISTS referral_usage_events (
    event_id TEXT PRIMARY KEY,
    referral_id TEXT NOT NULL,
    used_bytes INTEGER NOT NULL CHECK(used_bytes > 0),
    created_at TEXT NOT NULL,
    FOREIGN KEY(referral_id) REFERENCES referrals(referral_id)
);

CREATE TABLE IF NOT EXISTS servers (
    server_id TEXT PRIMARY KEY,
    country_code TEXT NOT NULL,
    country TEXT NOT NULL,
    city TEXT NOT NULL,
    provider_ref TEXT NOT NULL,
    health TEXT NOT NULL CHECK(health IN ('healthy','busy','maintenance','unavailable')),
    capacity_percent INTEGER NOT NULL CHECK(capacity_percent BETWEEN 0 AND 100),
    exit_ip TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    wg_public_key TEXT NOT NULL,
    dns_addresses TEXT NOT NULL,
    contract_active INTEGER NOT NULL CHECK(contract_active IN (0,1)),
    provisioned INTEGER NOT NULL CHECK(provisioned IN (0,1)),
    exit_verified INTEGER NOT NULL CHECK(exit_verified IN (0,1)),
    verified_at TEXT,
    measured_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS servers_public_state
    ON servers(contract_active, provisioned, exit_verified, health, measured_at);

CREATE TABLE IF NOT EXISTS usage_events (
    event_id TEXT PRIMARY KEY,
    node_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    epoch INTEGER NOT NULL CHECK(epoch >= 0),
    rx_bytes INTEGER NOT NULL CHECK(rx_bytes >= 0),
    tx_bytes INTEGER NOT NULL CHECK(tx_bytes >= 0),
    observed_delta_bytes INTEGER NOT NULL CHECK(observed_delta_bytes >= 0),
    applied_delta_bytes INTEGER NOT NULL CHECK(applied_delta_bytes >= 0),
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(node_id, device_id, epoch, rx_bytes, tx_bytes),
    FOREIGN KEY(device_id) REFERENCES devices(device_id),
    FOREIGN KEY(account_id) REFERENCES accounts(account_id)
);
CREATE INDEX IF NOT EXISTS usage_events_account ON usage_events(account_id, created_at);
CREATE TABLE IF NOT EXISTS peer_counter_state (
    node_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    epoch INTEGER NOT NULL CHECK(epoch >= 0),
    rx_bytes INTEGER NOT NULL CHECK(rx_bytes >= 0),
    tx_bytes INTEGER NOT NULL CHECK(tx_bytes >= 0),
    updated_at TEXT NOT NULL,
    PRIMARY KEY(node_id, device_id),
    FOREIGN KEY(device_id) REFERENCES devices(device_id)
);
CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    result TEXT NOT NULL,
    created_at TEXT NOT NULL
);

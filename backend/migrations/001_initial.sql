-- 001_initial.sql — Atticus PostgreSQL schema
-- Matches the schema from atticus_documentaion.md

CREATE TABLE IF NOT EXISTS users (
    user_id       UUID PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin', 'lawyer')),
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cases (
    case_id          UUID PRIMARY KEY,
    name             TEXT NOT NULL,
    client_name      TEXT,
    status           TEXT NOT NULL CHECK (status IN ('active', 'closed')) DEFAULT 'active',
    closed_at        TIMESTAMP,
    created_by       UUID REFERENCES users(user_id),
    created_at       TIMESTAMP DEFAULT NOW(),
    assigned_lawyers UUID[] DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS documents (
    file_id      UUID PRIMARY KEY,
    case_id      UUID REFERENCES cases(case_id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    version      INTEGER NOT NULL DEFAULT 1,
    is_latest    BOOLEAN NOT NULL DEFAULT TRUE,
    status       TEXT NOT NULL CHECK (status IN ('processing', 'ready', 'failed', 'review_required')) DEFAULT 'processing',
    s3_key       TEXT,
    uploaded_by  UUID REFERENCES users(user_id),
    uploaded_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id UUID PRIMARY KEY,
    user_id         UUID REFERENCES users(user_id) ON DELETE CASCADE,
    case_id         UUID REFERENCES cases(case_id) ON DELETE CASCADE,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    message_id      UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    query           TEXT NOT NULL,
    answer          TEXT,
    chunks_used     JSONB,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    file_id UUID PRIMARY KEY,
    file_path TEXT NOT NULL,
    status TEXT NOT NULL,
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,
    category TEXT,
    structure_type TEXT,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    indexed BOOLEAN NOT NULL DEFAULT FALSE,
    status_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    stage_timings_ms JSONB,
    failed_stage TEXT,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Useful indexes
CREATE INDEX IF NOT EXISTS idx_documents_case_id ON documents(case_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_case_id ON conversations(case_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status ON ingestion_jobs(status);

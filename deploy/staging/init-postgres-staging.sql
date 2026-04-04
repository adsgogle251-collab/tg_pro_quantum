-- ─────────────────────────────────────────────────────────────────────────────
-- TG PRO QUANTUM – PostgreSQL Staging Initialization
-- Run once by docker-entrypoint-initdb.d on first container start.
-- ─────────────────────────────────────────────────────────────────────────────

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- The database and user are created by POSTGRES_DB / POSTGRES_USER env vars.
-- This script runs as the superuser to finalize setup.

-- Grant connect & usage on the staging database
GRANT CONNECT ON DATABASE tg_quantum_staging TO tgpq_staging;

-- Grant schema privileges
\c tg_quantum_staging
GRANT USAGE  ON SCHEMA public TO tgpq_staging;
GRANT CREATE ON SCHEMA public TO tgpq_staging;
GRANT ALL    ON ALL TABLES    IN SCHEMA public TO tgpq_staging;
GRANT ALL    ON ALL SEQUENCES IN SCHEMA public TO tgpq_staging;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON TABLES    TO tgpq_staging;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON SEQUENCES TO tgpq_staging;

-- Performance tuning for staging workload
ALTER DATABASE tg_quantum_staging SET work_mem               = '64MB';
ALTER DATABASE tg_quantum_staging SET maintenance_work_mem   = '256MB';
ALTER DATABASE tg_quantum_staging SET effective_cache_size   = '2GB';
ALTER DATABASE tg_quantum_staging SET random_page_cost       = '1.1';
ALTER DATABASE tg_quantum_staging SET checkpoint_completion_target = '0.9';

-- Log slow queries (>500ms) for monitoring
ALTER DATABASE tg_quantum_staging SET log_min_duration_statement = '500';

-- Verify setup
SELECT current_database(), current_user, version();

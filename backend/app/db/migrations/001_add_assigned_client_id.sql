-- Minimal migration: add assigned_client_id to users if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='users' AND column_name='assigned_client_id'
    ) THEN
        ALTER TABLE users ADD COLUMN assigned_client_id INTEGER REFERENCES tenants(id);
    END IF;
END
$$;
-- Template migration (copy and edit)
-- Rename this file to e.g. 002_add_new_table.sql
DO $$
BEGIN
    -- Example: create a table if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name='example'
    ) THEN
        CREATE TABLE example (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    END IF;
END
$$;
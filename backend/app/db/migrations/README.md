Minimal SQL migrations

- Place idempotent `.sql` files here named `NNN_description.sql`.
- Files run in lexicographic order on app startup via `run_migrations.py`.
- Prefer `IF NOT EXISTS` guards to ensure safe re-runs.

Example pattern:

```sql
-- 002_add_example_table.sql
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name='example'
    ) THEN
        CREATE TABLE example (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL
        );
    END IF;
END
$$;
```

To verify applied migrations in Postgres:

```powershell
podman exec -it pca_db_1 psql -U postgres -d pca -c "\\d+ users"
```
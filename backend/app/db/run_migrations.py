import os
import logging
from pathlib import Path
from sqlalchemy import text
from app.db.database import engine

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

async def run_migrations():
    if not MIGRATIONS_DIR.exists():
        logging.info("Migrations directory not found: %s", MIGRATIONS_DIR)
        return
    # Run *.sql files in alphabetical order
    sql_files = sorted([p for p in MIGRATIONS_DIR.glob("*.sql")])
    if not sql_files:
        logging.info("No migration files to run in %s", MIGRATIONS_DIR)
        return
    async with engine.begin() as conn:
        for sql_path in sql_files:
            sql_text = sql_path.read_text(encoding="utf-8")
            logging.info("Applying migration: %s", sql_path.name)
            await conn.execute(text(sql_text))
        logging.info("Applied %d migration file(s)", len(sql_files))

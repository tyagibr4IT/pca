import os
import asyncio
import bcrypt
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/pca")

async def main():
    engine = create_async_engine(DATABASE_URL, future=True)
    pwd = os.getenv("NEW_PASSWORD", "password")
    username = os.getenv("USERNAME", "testuser")
    hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE users SET hashed_password=:hp WHERE username=:un"), {"hp": hashed, "un": username})
    await engine.dispose()
    print(f"Updated {username} password.")

if __name__ == "__main__":
    asyncio.run(main())
import asyncio
from app.db.database import engine
from sqlalchemy import text

async def update_pwd():
    async with engine.begin() as conn:
        await conn.execute(text(
            "UPDATE users SET hashed_password = :pwd WHERE id = 1"
        ), {
            'pwd': '$2b$12$gcVRkW78AUAB3RS71pUKyOBDIuOSbNHoctKVAzgjBkX6bF/puq1mu'
        })
        print('Password updated successfully')

asyncio.run(update_pwd())

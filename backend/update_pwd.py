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

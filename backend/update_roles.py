import asyncio
import sys
import os
os.chdir('/app')
sys.path.insert(0, '/app')

from app.db.database import engine
from sqlalchemy import text

async def update_roles():
    async with engine.begin() as conn:
        # Update testuser to superadmin
        result1 = await conn.execute(text("UPDATE users SET role = 'superadmin' WHERE username = 'testuser'"))
        print(f"Updated {result1.rowcount} user(s) to superadmin")
        
        # Update any 'user' role to 'member'
        result2 = await conn.execute(text("UPDATE users SET role = 'member' WHERE role = 'user'"))
        print(f"Updated {result2.rowcount} user(s) from 'user' to 'member'")
        
        print("All roles updated successfully")

if __name__ == "__main__":
    asyncio.run(update_roles())


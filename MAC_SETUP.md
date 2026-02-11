# Database Setup for Mac

This guide will help you set up the database and create initial users on Mac.

## Prerequisites

- Podman or Docker installed
- Python 3.11+ (if running scripts locally)

## Quick Start

### 1. Start the containers

```bash
chmod +x start_all.sh
./start_all.sh
```

### 2. Initialize the database

```bash
chmod +x init_mac.sh
./init_mac.sh
```

This will:
- Run all Alembic migrations
- Create default tenant
- Create roles (superadmin, admin, member)
- Create 25 default permissions
- Create superadmin user with credentials:
  - **Username**: `superadmin`
  - **Password**: `superadmin123`

### 3. Access the application

Open your browser and go to: **http://localhost:3001**

Login with:
- Username: `superadmin`
- Password: `superadmin123`

## Troubleshooting

### Connection Refused Error

If you see `ERR_CONNECTION_REFUSED` when trying to access the backend:

1. **Check if containers are running:**
   ```bash
   podman ps
   # or
   docker ps
   ```
   
   You should see 4 containers running:
   - pca-backend-1
   - pca-frontend-1
   - pca-db-1
   - pca-redis-1

2. **Check backend logs:**
   ```bash
   podman logs pca-backend-1 --tail 50
   # or
   docker logs pca-backend-1 --tail 50
   ```

3. **Try accessing with 127.0.0.1 instead of localhost:**
   - Frontend: http://127.0.0.1:3001
   - Backend: http://127.0.0.1:8001

4. **Check if port 8001 is already in use:**
   ```bash
   lsof -i :8001
   ```

5. **Restart containers:**
   ```bash
   podman compose -f podman-compose.yml down
   ./start_all.sh
   ```

### Login Issues

If you can't login with testuser/superadmin:

1. **Re-run the initialization script:**
   ```bash
   ./init_mac.sh
   ```
   This will reset the superadmin password to `superadmin123`

2. **Check if user exists:**
   ```bash
   podman exec pca-backend-1 python -c "
   import asyncio
   from sqlalchemy import text
   from app.db.database import engine
   
   async def check():
       async with engine.begin() as conn:
           result = await conn.execute(text('SELECT id, username FROM users'))
           users = result.fetchall()
           print('Users in database:')
           for u in users:
               print(f'  - ID: {u[0]}, Username: {u[1]}')
   
   asyncio.run(check())
   "
   ```

### Database Connection Issues

If the backend can't connect to the database:

1. **Check database container:**
   ```bash
   podman exec pca-db-1 pg_isready -U postgres
   ```

2. **Check database logs:**
   ```bash
   podman logs pca-db-1 --tail 50
   ```

3. **Verify database exists:**
   ```bash
   podman exec pca-db-1 psql -U postgres -c "\l"
   ```

### CORS Issues

If you see CORS errors in the browser console:

1. The application is already configured for development mode with CORS allowing all origins
2. Make sure you're accessing via the frontend (port 3001), not directly calling the backend (port 8001)
3. Clear browser cache and reload

## Manual Database Commands

### Run migrations manually:
```bash
podman exec pca-backend-1 alembic upgrade head
```

### Create a new user manually:
```bash
podman exec pca-backend-1 python -c "
import asyncio
import bcrypt
from sqlalchemy import text
from app.db.database import engine

async def create_user():
    username = 'myuser'
    password = 'mypassword'
    email = 'myuser@example.com'
    
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    async with engine.begin() as conn:
        # Get member role ID
        role_result = await conn.execute(text('SELECT id FROM roles WHERE name = \"member\"'))
        role_id = role_result.scalar()
        
        await conn.execute(text('''
            INSERT INTO users (tenant_id, username, email, hashed_password, role_id, is_active, status)
            VALUES (1, :user, :email, :pwd, :role_id, true, 'active')
        '''), {'user': username, 'email': email, 'pwd': hashed, 'role_id': role_id})
        
    print(f'User {username} created successfully')

asyncio.run(create_user())
"
```

### Reset superadmin password:
```bash
podman exec pca-backend-1 python init_db.py
```

## Useful Commands

### Stop all containers:
```bash
podman compose -f podman-compose.yml down
```

### View all container logs:
```bash
podman compose -f podman-compose.yml logs -f
```

### Access database directly:
```bash
podman exec -it pca-db-1 psql -U postgres -d pca
```

### Rebuild backend after code changes:
```bash
podman compose -f podman-compose.yml up -d --build backend
```

## Need Help?

If you're still having issues:
1. Check all containers are running: `podman ps`
2. Check backend logs: `podman logs pca-backend-1`
3. Check database logs: `podman logs pca-db-1`
4. Ensure ports 3001, 8001, 5433, 6380 are not in use by other applications

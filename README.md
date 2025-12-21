# PCA Dev Quick Start (Windows)

This repo provides a single-command workflow to run the full stack: FastAPI backend, Postgres, Redis, and an NGINX-based static frontend.

## Prerequisites
- Podman (or Docker Desktop)
- Podman Compose plugin (or Docker Compose)
- Windows PowerShell 5.1

## One-Command Start
```powershell
# From the repo root
.\start_all.bat
```
- Backend: http://localhost:8000
- Frontend: http://localhost:3001/login.html
- Postgres: localhost:5432 (internal to containers)
- Redis: localhost:6379 (internal to containers)

## Stop Everything
```powershell
.\stop_all.bat
```

## Health Check
Runs a quick end-to-end test (frontend reachable, login works, metrics returns).
```powershell
powershell -ExecutionPolicy Bypass -File .\health_check.ps1
```
Expected output:
- Frontend OK
- Backend login OK
- Metrics OK

## Auto-Start on System Reboot
Containers and all persisted data survive a system restart automatically.
```powershell
# Run once as Administrator to enable
powershell -ExecutionPolicy Bypass -File .\enable_autostart.ps1
```
- Postgres and Redis data stored in named volumes persist across reboots.
- Scheduled task runs `start_all.bat` on system startup.
- To disable: `Unregister-ScheduledTask -TaskName "PCA-Stack-AutoStart" -Confirm:$false`

## Default Login
- Username: `testuser`
- Password: `password`

If you ever see a 401 with that user, reset the password hash using the helper script inside the backend container:
```powershell
# Example (Podman):
podman exec -it backend-app bash -lc "python backend/update_pwd.py --username testuser --password password"
```

## Compose Details
See [podman-compose.yml](podman-compose.yml) for services and ports.
- `frontend`: NGINX serving `frontend/static` on port 3001
- `backend`: FastAPI on port 8000
- `db`: Postgres 15
- `redis`: Redis 7

## Provider Credentials (Metrics)
Metrics will show zeros until tenant metadata includes credentials.
- AWS: Access key, secret key; optional session token, region.
- Azure: Service principal (tenant ID, client ID, client secret, subscription ID).
- GCP: Service account JSON (upload via clients UI) and project ID.

GCP roles typically required for discovery:
- Compute Viewer
- Storage Object Viewer
- Cloud SQL Viewer

After adding credentials in the UI, re-run the health check.

## Troubleshooting
- Port in use (3001 or 8000): Stop existing services using those ports or change mappings in [podman-compose.yml](podman-compose.yml).
- Orphan containers: Scripts use `--remove-orphans`, but if issues persist, run:
  ```powershell
  podman compose -f podman-compose.yml down --remove-orphans; podman system prune -f
  ```
- Login blocked: Ensure login route is whitelisted in middleware; use the password reset command above.
- Metrics error: Confirm credentials are present and valid in tenant metadata; check backend logs.

## Alternative: Docker Compose
If you prefer Docker:
```powershell
# Start
docker compose -f podman-compose.yml up -d --remove-orphans
# Stop
docker compose -f podman-compose.yml down --remove-orphans
```

## Structure
- Backend code: [backend/app](backend/app)
- Frontend static assets: [frontend/static](frontend/static)
- Tests: [backend/tests](backend/tests)

Happy building!
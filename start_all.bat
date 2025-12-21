@echo off
cd /d "%~dp0"
echo Starting PCA stack via podman-compose.yml...
podman compose -f "%~dp0podman-compose.yml" up -d --remove-orphans
if %ERRORLEVEL% NEQ 0 (
  echo Error starting containers. Check podman installation and compose file.
  exit /b 1
)
echo Stack started. Frontend: http://localhost:3001  Backend: http://localhost:8000

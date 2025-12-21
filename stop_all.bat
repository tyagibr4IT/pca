@echo off
cd /d "%~dp0"
echo Stopping PCA stack via podman-compose.yml...
podman compose -f "%~dp0podman-compose.yml" down --remove-orphans
if %ERRORLEVEL% NEQ 0 (
  echo Error stopping containers. Check podman installation and compose file.
  exit /b 1
)
echo Stack stopped.

@echo off
cd /d "%~dp0"
echo Starting server from: %CD%
python -m http.server 3001

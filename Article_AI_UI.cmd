@echo off
setlocal
cd /d "%~dp0"
start "Article AI UI" "http://127.0.0.1:8080"
.\.venv\Scripts\python.exe main.py --ui
endlocal

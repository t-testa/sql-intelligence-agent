@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m scripts.local %*
) else (
  py -3 -m scripts.local %*
)
exit /b %errorlevel%

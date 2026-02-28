@echo off
echo =======================================
echo HiveBuzz Flask Application Starter
echo =======================================

echo Checking for Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
  echo Python is not installed or not in PATH
  echo Please install Python and try again
  pause
  exit /b 1
)

echo Checking for required packages...
pip install -r requirements.txt

echo Starting HiveBuzz application...
python app.py
pause

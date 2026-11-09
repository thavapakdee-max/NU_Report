@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment is missing. Please complete the installation steps in README.md first.
  pause
  exit /b 1
)
echo Make sure MySQL is running in XAMPP before opening the website.
echo When Flask shows "Running on http://127.0.0.1:5000", open that address in your browser.
echo Close this window to stop the local web server.
echo.
".venv\Scripts\python.exe" -m flask --app app run --host 127.0.0.1
pause
endlocal

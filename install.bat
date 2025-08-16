@echo off
echo Installing Players of Games...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

echo Python found, installing dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Installation completed successfully!
echo.
echo Next steps:
echo 1. Copy .env.example to .env and add your API keys
echo 2. Run: python main.py --help for usage options
echo 3. Try: python run_example.py for a demo without API keys
echo.
pause

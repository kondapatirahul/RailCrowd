@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creating Python virtual environment...
  py -3.12 -m venv .venv
  if errorlevel 1 goto failed
)
call ".venv\Scripts\activate.bat"
python -c "import flask, flask_sqlalchemy, flask_migrate" >nul 2>nul
if errorlevel 1 (
  echo Installing project dependencies...
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  if errorlevel 1 goto failed
)
echo Preparing database and sample records...
python setup.py
if errorlevel 1 goto failed
echo Starting RailCrowd at http://127.0.0.1:5000
python -m flask --app backend.run run --debug
if errorlevel 1 goto failed
goto end
:failed
echo.
echo RailCrowd could not start. Review the error above.
pause
:end
endlocal

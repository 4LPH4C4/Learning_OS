@echo off
setlocal EnableExtensions
pushd "%~dp0"
if errorlevel 1 goto :root_failed

where python >nul 2>&1
if errorlevel 1 goto :python_missing

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 goto :python_missing

if exist ".venv\Scripts\python.exe" goto :check_dependencies

echo [Learning OS] Creating the virtual environment...
python -m venv ".venv"
if errorlevel 1 goto :venv_failed

:check_dependencies
".venv\Scripts\python.exe" -c "import streamlit, yaml, pandas, jupyterlab" >nul 2>&1
if not errorlevel 1 goto :run_app

echo [Learning OS] Installing dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :dependency_failed

:run_app
echo [Learning OS] Starting the app...
".venv\Scripts\python.exe" -m streamlit run app.py
set "APP_EXIT=%ERRORLEVEL%"
popd
exit /b %APP_EXIT%

:root_failed
echo [Learning OS] Could not open the project directory. 1>&2
exit /b 1

:python_missing
echo [Learning OS] Python 3.11 or newer is required. 1>&2
popd
exit /b 1

:venv_failed
echo [Learning OS] Could not create .venv. 1>&2
popd
exit /b 1

:dependency_failed
echo [Learning OS] Could not install dependencies. 1>&2
popd
exit /b 1

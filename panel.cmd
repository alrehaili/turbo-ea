@echo off
REM ===========================================================================
REM  Turbo EA - control panel (Windows)
REM
REM  Opens a desktop window that runs the backend and the frontend: live logs,
REM  ports, start / stop / restart, keep running, and a Settings dialog that
REM  edits backend\.env. Closing the window stops both apps.
REM
REM  Needs a JDK 17+ (javac), Python 3.12+ and Node 20+ on PATH, and a
REM  PostgreSQL the backend can reach. See tools\control-panel\README.md.
REM ===========================================================================
cd /d "%~dp0"
set "PANEL_SRC=tools\control-panel\ControlPanel.java"
set "PANEL_OUT=tools\control-panel\.runtime\classes"

where javac >nul 2>&1
if errorlevel 1 (
  echo.
  echo   [X] javac was not found on PATH. Install a JDK 17 or newer.
  echo.
  pause
  exit /b 1
)
where node >nul 2>&1
if errorlevel 1 (
  echo.
  echo   [!] Node.js was not found on PATH. The backend will run; the frontend will not.
  echo.
  pause
)

REM Compiled on every launch - a second or two - so it never runs stale code.
javac --release 17 -encoding UTF-8 -d "%PANEL_OUT%" "%PANEL_SRC%"
if errorlevel 1 (
  echo.
  echo   [X] The control panel did not compile. See the messages above.
  echo.
  pause
  exit /b 1
)
start "" javaw -cp "%PANEL_OUT%" ControlPanel "%~dp0."

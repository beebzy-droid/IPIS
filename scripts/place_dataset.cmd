@echo off
REM ============================================================================
REM place_dataset.cmd  -  copy a downloaded dataset from Downloads into data\raw\
REM ----------------------------------------------------------------------------
REM Run from repo root: C:\Users\yubyu\Projects\IPIS
REM
REM   scripts\place_dataset.cmd <downloads_subpath> <data_raw_target>
REM
REM Examples:
REM   scripts\place_dataset.cmd "phm-ieee-2012-data-challenge-dataset" "femto"
REM   scripts\place_dataset.cmd "cwru_download" "cwru"
REM
REM Copies %USERPROFILE%\Downloads\<downloads_subpath>  ->  data\raw\<data_raw_target>\
REM Creates the target dir if missing. data\raw\* is gitignored, so the copied
REM data is never committed (only the per-dataset README is tracked).
REM ============================================================================

setlocal
if "%~1"=="" goto :usage
if "%~2"=="" goto :usage

set "SRC=%USERPROFILE%\Downloads\%~1"
set "DST=%CD%\data\raw\%~2"

if not exist "%SRC%" (
  echo [ERROR] Source not found: "%SRC%"
  echo Check the folder name under %USERPROFILE%\Downloads
  exit /b 1
)

if not exist "%DST%" mkdir "%DST%"

echo Copying:
echo   from "%SRC%"
echo   to   "%DST%"
xcopy /E /I /Y "%SRC%" "%DST%"
if errorlevel 1 (
  echo [ERROR] xcopy failed.
  exit /b 1
)

echo.
echo [OK] Copy complete. Top-level entries now in "%DST%":
dir /b "%DST%"
echo.
echo Reminder: raw data stays gitignored. Commit only the dataset README.
exit /b 0

:usage
echo Usage: scripts\place_dataset.cmd ^<downloads_subpath^> ^<data_raw_target^>
echo   e.g. scripts\place_dataset.cmd "phm-ieee-2012-data-challenge-dataset" "femto"
exit /b 1

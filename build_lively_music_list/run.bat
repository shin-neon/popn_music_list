@echo off
cd /d "%~dp0"
py -3 build_lively_music_list.py
if errorlevel 1 (
  echo.
  echo Lively music list build failed.
)
pause

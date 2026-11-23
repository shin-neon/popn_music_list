@echo off
cd /d "%~dp0"
py -3 build_ac_music_list.py
if errorlevel 1 (
  echo.
  echo AC music list build failed.
)
pause

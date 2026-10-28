@echo off
chcp 65001 >nul
title Desinstalar Tradução PT-BR - Ostriv
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Desinstalar.ps1"
echo.
pause

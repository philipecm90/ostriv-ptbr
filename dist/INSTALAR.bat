@echo off
chcp 65001 >nul
title Instalar Tradução PT-BR - Ostriv
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Instalar.ps1"
echo.
pause

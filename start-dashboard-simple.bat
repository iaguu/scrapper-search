@echo off
title Telegram Bridge - Dashboard Simples
color 0B

echo ========================================
echo  TELEGRAM QUERY BRIDGE - DASHBOARD SIMPLES
echo ========================================
echo.

echo [1/3] Iniciando Dashboard Manager...
start "Dashboard Manager" cmd /k "python server.py"

echo [2/3] Aguardando Dashboard...
timeout /t 5 /nobreak > nul

echo [3/3] Dashboard iniciado!
echo.
echo Dashboard: http://localhost:9000
echo.
echo Para iniciar os servicos manualmente:
echo   Python Service: cd telegram_service ^&^& python -m uvicorn main:app --host 127.0.0.1 --port 8001
echo   Node.js API:    node api/index.js
echo.
echo Use os botoes na dashboard para controlar os servicos
echo ========================================

timeout /t 9999 /nobreak > nul

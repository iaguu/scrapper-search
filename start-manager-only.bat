@echo off
title Telegram Query Bridge - Web Manager Only
color 0B

echo ========================================
echo  TELEGRAM QUERY BRIDGE - WEB MANAGER
echo ========================================
echo.

echo [1/2] Verificando dependencias...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado!
    echo Instale Python 3.9+ e adicione ao PATH
    pause
    exit /b 1
)

echo [2/2] Iniciando Web Manager GUI...
echo Iniciando Python FastAPI server...
start "Web Manager" cmd /k "python server.py"

echo.
echo Aguardando 3 segundos para o servidor iniciar...
timeout /t 3 /nobreak > nul

echo.
echo Abrindo dashboard no navegador...
start http://localhost:9000

echo.
echo ========================================
echo  WEB MANAGER INICIADO COM SUCESSO!
echo ========================================
echo.
echo Dashboard disponivel: http://localhost:9000
echo.
echo Para iniciar os outros servicos manualmente:
echo  - Python Service: python -m uvicorn main:app --host 127.0.0.1 --port 8001
echo  - Node.js API:    node api/index.js
echo.
echo Execute a partir da pasta telegram_service para o servico Python.
echo.

timeout /t 2 /nobreak > nul
exit

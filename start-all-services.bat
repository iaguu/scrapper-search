@echo off
title Telegram Bridge - Iniciar Todos os Servicos
color 0B

echo ========================================
echo  TELEGRAM QUERY BRIDGE - STARTER COMPLETO
echo ========================================
echo.

echo [1/4] Verificando servicos ja rodando...
powershell -Command "Invoke-WebRequest -Uri http://localhost:9000/health -UseBasicParsing" > nul 2>&1
if %errorlevel% equ 0 (
    echo [AVISO] Manager ja esta rodando!
) else (
    echo [1/4] Iniciando Manager...
    start "Manager" cmd /k "python server.py"
    echo [2/4] Aguardando Manager...
    timeout /t 3 /nobreak > nul
)

echo [3/4] Verificando Python Service...
powershell -Command "Invoke-WebRequest -Uri http://localhost:8001/health -UseBasicParsing" > nul 2>&1
if %errorlevel% equ 0 (
    echo [AVISO] Python Service ja esta rodando!
) else (
    echo [3/4] Iniciando Python Service...
    cd /d "%~dp0telegram_service"
    start "Python Service" cmd /k "python -m uvicorn main:app --host 127.0.0.1 --port 8001"
    echo [4/4] Aguardando Python Service...
    timeout /t 5 /nobreak > nul
)

echo [5/4] Verificando Node.js API...
powershell -Command "Invoke-WebRequest -Uri http://localhost:3000/health -UseBasicParsing" > nul 2>&1
if %errorlevel% equ 0 (
    echo [AVISO] Node.js API ja esta rodando!
) else (
    echo [5/4] Iniciando Node.js API...
    cd /d "%~dp0"
    start "Node.js API" cmd /k "node api/index.js"
    echo [6/4] Aguardando Node.js API...
    timeout /t 5 /nobreak > nul
)

echo.
echo [7/8] Verificando status dos servicos...
timeout /t 3 /nobreak > nul

echo [8/8] Verificando autenticacao Telegram...
cd /d "%~dp0telegram_service"
powershell -Command "Invoke-WebRequest -Uri http://localhost:8001/status -UseBasicParsing" | findstr "authenticated" > temp_auth.txt

set /p auth_status=<temp_auth.txt
del temp_auth.txt

if "%auth_status%"=="authenticated" (
    echo [9/9] ✅ Telegram ja esta autenticado!
) else (
    echo [9/9] ⚠️  Telegram nao autenticado - solicitando autenticacao...
    cd /d "%~dp0telegram_service"
    powershell -Command "Invoke-WebRequest -Uri http://localhost:9000/telegram/auth -Method POST -UseBasicParsing" > nul
    echo [10/10] 📱 Aguardando codigo SMS...
    echo     Abra o Telegram e digite o codigo recebido
    echo     Depois de digitar, pressione qualquer tecla para continuar...
    pause > nul
)

echo.
echo ========================================
echo  SISTEMA INICIADO COM SUCESSO!
echo ========================================
echo.
echo Dashboard: http://localhost:9000
echo Python API: http://localhost:8001
echo Node.js API: http://localhost:3000
echo.
echo Para parar todos os servicos: CTRL+C em cada janela
echo ========================================

timeout /t 9999 /nobreak > nul

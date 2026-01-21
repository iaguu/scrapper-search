@echo off
title Telegram Query Bridge - Inicializador Completo
color 0A

echo ========================================
echo  TELEGRAM QUERY BRIDGE - START COMPLETO
echo ========================================
echo.

echo [1/3] Verificando dependencias...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado!
    echo Instale Python 3.9+ e adicione ao PATH
    pause
    exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Node.js nao encontrado!
    echo Instale Node.js 18+ e adicione ao PATH
    pause
    exit /b 1
)

echo [2/3] Instalando dependencias Python...
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    echo AVISO: requirements.txt nao encontrado na raiz.
)

echo [3/3] Instalando dependencias Node.js...
echo npm install em andamento...
call npm install
echo npm install concluido!

echo.
echo Iniciando sistema completo...
echo.

echo 1. Iniciando Python Service (Telegram)...
if not exist telegram_service (
    echo ERRO: Pasta telegram_service nao encontrada!
    pause
    exit /b 1
)

echo Copiando .env para telegram_service...
if exist .env (
    copy /Y .env telegram_service\.env >nul
)

cd telegram_service
echo Iniciando Python uvicorn...
start "Python Service" cmd /k "python -m uvicorn main:app --host 127.0.0.1 --port 8000"

echo 2. Aguardando 3 segundos...
timeout /t 3 /nobreak > nul

echo 3. Iniciando Node.js API...
cd ..
echo Iniciando Node.js server...
start "Node.js API" cmd /k "node api/index.js"

echo 4. Aguardando 3 segundos...
timeout /t 3 /nobreak > nul

echo 5. Iniciando Web Manager GUI...
start "Web Manager" cmd /k "python server.py"

echo 6. Aguardando 5 segundos para servicos iniciarem...
timeout /t 5 /nobreak > nul

echo 7. Abrindo dashboard no navegador...
start http://localhost:9000

echo.
echo ========================================
echo  SISTEMA COMPLETO INICIADO COM SUCESSO!
echo ========================================
echo.
echo Servicos disponiveis:
echo  - Dashboard:      http://localhost:9000
echo  - Node.js API:    http://localhost:3000  
echo  - Python Service: http://localhost:8000
echo.
echo Comandos uteis:
echo  - Parar tudo:     npm run stop
echo  - Reiniciar:      npm run restart
echo  - Ver status:     curl http://localhost:9000/health
echo.
echo Dashboard abrindo automaticamente...
echo.

timeout /t 2 /nobreak > nul
exit

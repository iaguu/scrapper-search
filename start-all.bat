@echo off
echo Iniciando Telegram Query Bridge - Sistema Completo...

echo 1. Iniciando Python Service (Telegram)...
cd telegram_service
start "Python Service" cmd /k "python -m uvicorn demo:app --host 127.0.0.1 --port 8000"

echo 2. Aguardando 3 segundos...
timeout /t 3 /nobreak > nul

echo 3. Iniciando Node.js API...
cd ..
start "Node.js API" cmd /k "node api/index.js"

echo 4. Aguardando 3 segundos...
timeout /t 3 /nobreak > nul

echo 5. Iniciando Web Manager GUI...
start "Web Manager" cmd /k "python server.py"

echo.
echo ========================================
echo Sistema Completo Iniciado!
echo ========================================
echo.
echo Acesse os servicos:
echo - GUI Web Manager: http://localhost:9000
echo - Node.js API:      http://localhost:3000
echo - Python Service:   http://localhost:8000
echo.
echo Para testar:
echo curl http://localhost:9000
echo curl http://localhost:3000/health
echo curl http://localhost:8000/health
echo.
echo Para parar tudo: npm run stop
echo ========================================
echo.
pause

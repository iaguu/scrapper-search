@echo off
echo Iniciando Telegram Query Bridge API...

echo Iniciando Python Service...
cd telegram_service
start "Python Service" cmd /k "python -m uvicorn demo:app --host 127.0.0.1 --port 8000"

echo Aguardando 3 segundos...
timeout /t 3 /nobreak

echo Iniciando Node.js API...
cd ..
start "Node.js API" cmd /k "npm start"

echo Servicos iniciados!
echo Python: http://localhost:8000
echo Node.js: http://localhost:3000
echo.
echo Para testar:
echo curl http://localhost:8000/health
echo curl http://localhost:3000/health
echo.
pause

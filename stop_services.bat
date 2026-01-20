@echo off
echo Parando Telegram Query Bridge API...

echo Parando Python Service...
taskkill /F /IM python.exe 2>nul

echo Parando Node.js API...
taskkill /F /IM node.exe 2>nul

echo Verificando portas...
netstat -ano | findstr ":8000\|:3000"

echo Servicos parados!
pause

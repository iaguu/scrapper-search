@echo off
echo ========================================
echo  PARANDO SERVICOS TELEGRAM QUERY BRIDGE
echo ========================================
echo.

echo [1/3] Parando Node.js API (Porta 3000)...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":3000" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
if errorlevel 1 echo    - Nenhum processo encontrado na porta 3000.

echo [2/3] Parando Python Service (Porta 8000)...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
if errorlevel 1 echo    - Nenhum processo encontrado na porta 8000.

echo [3/3] Parando Web Manager (Porta 9000)...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":9000" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
if errorlevel 1 echo    - Nenhum processo encontrado na porta 9000.

echo.
echo [LIMPEZA] Fechando janelas de terminal associadas...
taskkill /F /FI "WINDOWTITLE eq Python Service*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Node.js API*" >nul 2>&1
taskkill /F /FI "Web Manager*" >nul 2>&1

echo.
echo Todos os servicos foram parados.
timeout /t 2 >nul
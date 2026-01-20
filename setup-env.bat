@echo off
setlocal enabledelayedexpansion

:: Script Automático de Configuração do .env
:: Telegram Query Bridge

echo 🔧 Configurando ambiente Telegram Query Bridge...
echo.

:: Cores (limitado no Windows)
set "INFO=[INFO]"
set "SUCCESS=[SUCCESS]"
set "WARNING=[WARNING]"
set "ERROR=[ERROR]"

:: Verificar se .env já existe
if exist .env (
    echo %WARNING% Arquivo .env já existe!
    set /p overwrite=Deseja sobrescrever? (s/N): 
    if /i not "!overwrite!"=="s" (
        echo %INFO% Mantendo configuração existente.
        pause
        exit /b 0
    )
)

:: Backup do .env existente
if exist .env (
    copy .env .env.backup.%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~-11,2%%time:~-9,2%%time:~-6,2% >nul
    echo %INFO% Backup criado
)

:: Coletar informações do usuário
echo 📋 Preencha as configurações do Telegram:
echo.

:: API Key
set /p api_key=🔑 API Key (deixe em branco para gerar automático): 
if "!api_key!"=="" (
    set api_key=tg_bridge_%random%_%random%
    echo %INFO% API Key gerada: !api_key!
)

:: API ID
:api_id_loop
set /p api_id=🆔 Telegram API ID (número): 
echo !api_id! | findstr /r "^[0-9][0-9]*$" >nul
if errorlevel 1 (
    echo %ERROR% API ID deve ser um número válido!
    goto api_id_loop
)

:: API Hash
:api_hash_loop
set /p api_hash=🔐 Telegram API Hash (32 caracteres): 
if not "!api_hash!"=="" (
    call :strlen api_hash api_hash_len
    if !api_hash_len! neq 32 (
        echo %ERROR% API Hash deve ter exatamente 32 caracteres!
        goto api_hash_loop
    )
)

:: Chat ID
:chat_id_loop
set /p chat_id=💬 Chat ID (use @userinfobot para obter): 
echo !chat_id! | findstr /r "^-?[0-9][0-9]*$" >nul
if errorlevel 1 (
    echo %ERROR% Chat ID deve ser um número (geralmente negativo para grupos)!
    goto chat_id_loop
)

:: Phone Number
:phone_loop
set /p phone_number=📱 Phone Number (ex: +5511912345678): 
echo !phone_number! | findstr /r "^\+[0-9][0-9]*$" >nul
if errorlevel 1 (
    echo %ERROR% Formato inválido! Use: +55DDNNNNNNNNN
    goto phone_loop
)

:: Ambiente
set /p environment=🌍 Ambiente (development/production) [development]: 
if "!environment!"=="" set environment=development

:: Criar arquivo .env
(
echo # API Configuration
echo API_KEY=!api_key!
echo PORT=3000
echo NODE_ENV=!environment!
echo.
echo # Telegram Configuration
echo API_ID=!api_id!
echo API_HASH=!api_hash!
echo CHAT_ID=!chat_id!
echo PHONE_NUMBER=!phone_number!
echo.
echo # Python Service URL
echo PYTHON_SERVICE_URL=http://localhost:8000
echo.
echo # Logging
echo LOG_LEVEL=!environment!
) > .env

echo %SUCCESS% Arquivo .env criado com sucesso!

:: Validar configuração
echo.
echo %INFO% Validando configuração...

:: Testar se Node.js pode ler
where node >nul 2>&1
if %errorlevel% equ 0 (
    node -e "require('dotenv').config({path: '.env'}); console.log('✅ API Key:', process.env.API_KEY ? 'OK' : 'MISSING'); console.log('✅ API ID:', process.env.API_ID ? 'OK' : 'MISSING'); console.log('✅ Chat ID:', process.env.CHAT_ID ? 'OK' : 'MISSING'); console.log('✅ Configuração Node.js validada!');" >nul 2>&1
    if %errorlevel% equ 0 (
        echo %SUCCESS% Validação Node.js concluída!
    )
) else (
    echo %WARNING% Node.js não encontrado para validação
)

:: Resumo
echo.
echo 🎉 Configuração concluída!
echo.
echo 📋 Resumo:
echo    📁 Arquivo criado: .env
echo    🔑 API Key: !api_key!
echo    🆔 API ID: !api_id!
echo    💬 Chat ID: !chat_id!
echo    📱 Phone: !phone_number!
echo    🌍 Ambiente: !environment!
echo.
echo 🚀 Para iniciar os serviços:
echo    npm start
echo.
echo 🌐 Para acessar a GUI:
echo    http://localhost:9000
echo.
echo ⚠️  IMPORTANTE:
echo    • Adicione .env ao seu .gitignore
echo    • Nunca compartilhe este arquivo
echo    • Mantenha suas credenciais seguras!
echo.

:: Adicionar ao .gitignore se não existir
if exist .gitignore (
    findstr /m "^\.env$" .gitignore >nul
    if errorlevel 1 (
        echo .env >> .gitignore
        echo %INFO% Adicionado .env ao .gitignore
    )
) else (
    echo .env > .gitignore
    echo %INFO% Criado .gitignore com .env
)

echo %SUCCESS% Setup completo! Execute 'npm start' para iniciar.
pause
goto :eof

:: Função para obter tamanho da string
:strlen
setlocal enabledelayedexpansion
set "str=!%~1!"
set "len=0"
if defined str (
    for /l %%i in (0,1,8192) do (
        if "!str:~%%i,1!" neq "" set /a len=%%i+1
    )
)
endlocal & set "%~2=%len%"
goto :eof

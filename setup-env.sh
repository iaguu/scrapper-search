#!/bin/bash

# Script Automático de Configuração do .env
# Telegram Query Bridge

echo "🔧 Configurando ambiente Telegram Query Bridge..."
echo

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Função de log
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar se .env já existe
if [[ -f ".env" ]]; then
    warning "Arquivo .env já existe!"
    read -p "Deseja sobrescrever? (s/N): " overwrite
    if [[ ! $overwrite =~ ^[Ss]$ ]]; then
        log "Mantendo configuração existente."
        exit 0
    fi
fi

# Backup do .env existente
if [[ -f ".env" ]]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    log "Backup criado: .env.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Coletar informações do usuário
echo "📋 Preencha as configurações do Telegram:"
echo

# API Key
read -p "🔑 API Key (deixe em branco para gerar automático): " api_key
if [[ -z "$api_key" ]]; then
    api_key="tg_bridge_$(date +%s)_$(openssl rand -hex 8)"
    log "API Key gerada: $api_key"
fi

# API ID
while true; do
    read -p "🆔 Telegram API ID (número): " api_id
    if [[ "$api_id" =~ ^[0-9]+$ ]]; then
        break
    else
        error "API ID deve ser um número válido!"
    fi
done

# API Hash
while true; do
    read -p "🔐 Telegram API Hash (32 caracteres): " api_hash
    if [[ ${#api_hash} -eq 32 ]]; then
        break
    else
        error "API Hash deve ter exatamente 32 caracteres!"
    fi
done

# Chat ID
while true; do
    read -p "💬 Chat ID (use @userinfobot para obter): " chat_id
    if [[ "$chat_id" =~ ^-?[0-9]+$ ]]; then
        break
    else
        error "Chat ID deve ser um número (geralmente negativo para grupos)!"
    fi
done

# Phone Number
while true; do
    read -p "📱 Phone Number (ex: +5511912345678): " phone_number
    if [[ "$phone_number" =~ ^\+[0-9]{10,15}$ ]]; then
        break
    else
        error "Formato inválido! Use: +55DDNNNNNNNNN"
    fi
done

# Ambiente
read -p "🌍 Ambiente (development/production) [development]: " environment
environment=${environment:-development}

# Criar arquivo .env
cat > .env << EOF
# API Configuration
API_KEY=$api_key
PORT=3000
NODE_ENV=$environment

# Telegram Configuration
API_ID=$api_id
API_HASH=$api_hash
CHAT_ID=$chat_id
PHONE_NUMBER=$phone_number

# Python Service URL
PYTHON_SERVICE_URL=http://localhost:8000

# Logging
LOG_LEVEL=${environment}
EOF

success "Arquivo .env criado com sucesso!"

# Validar configuração
echo
log "Validando configuração..."

# Testar se Python pode ler as variáveis
cd telegram_service
python3 -c "
import os
from dotenv import load_dotenv

try:
    load_dotenv('../.env')
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    phone = os.getenv('PHONE_NUMBER')
    
    print(f'✅ API ID: {api_id}')
    print(f'✅ API Hash: {api_hash[:10]}...')
    print(f'✅ Phone: {phone}')
    print('✅ Configuração carregada com sucesso!')
except Exception as e:
    print(f'❌ Erro: {e}')
    exit(1)
" 2>/dev/null

if [[ $? -eq 0 ]]; then
    success "Validação Python concluída!"
else
    warning "Python não encontrado ou sem dependências. Instale com: pip install python-dotenv"
fi

cd ..

# Testar se Node.js pode ler
if command -v node &> /dev/null; then
    node -e "
    require('dotenv').config({path: '.env'});
    console.log('✅ API Key:', process.env.API_KEY ? 'OK' : 'MISSING');
    console.log('✅ API ID:', process.env.API_ID ? 'OK' : 'MISSING');
    console.log('✅ Chat ID:', process.env.CHAT_ID ? 'OK' : 'MISSING');
    console.log('✅ Configuração Node.js validada!');
    " 2>/dev/null
    
    if [[ $? -eq 0 ]]; then
        success "Validação Node.js concluída!"
    fi
fi

# Resumo
echo
echo "🎉 Configuração concluída!"
echo
echo "📋 Resumo:"
echo "   📁 Arquivo criado: .env"
echo "   🔑 API Key: $api_key"
echo "   🆔 API ID: $api_id"
echo "   💬 Chat ID: $chat_id"
echo "   📱 Phone: $phone_number"
echo "   🌍 Ambiente: $environment"
echo
echo "🚀 Para iniciar os serviços:"
echo "   npm start"
echo
echo "🌐 Para acessar a GUI:"
echo "   http://localhost:9000"
echo
echo "⚠️  IMPORTANTE:"
echo "   • Adicione .env ao seu .gitignore"
echo "   • Nunca compartilhe este arquivo"
echo "   • Mantenha suas credenciais seguras!"
echo

# Adicionar ao .gitignore se não existir
if [[ -f ".gitignore" ]]; then
    if ! grep -q "^\.env$" .gitignore; then
        echo ".env" >> .gitignore
        log "Adicionado .env ao .gitignore"
    fi
else
    echo ".env" > .gitignore
    log "Criado .gitignore com .env"
fi

success "Setup completo! Execute 'npm start' para iniciar."

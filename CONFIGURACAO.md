# 📋 Guia de Configuração do .env

## 🔧 Como Configurar o Arquivo .env

### 1. Onde Obter as Credenciais do Telegram

#### **API_ID e API_HASH**
1. Acesse: https://my.telegram.org/apps
2. Faça login com seu número do Telegram
3. Clique em "Create application"
4. Preencha os dados:
   - **App title**: "Telegram Query Bridge"
   - **Short name**: "tg-bridge"
   - **Platform**: "Desktop"
   - **Description**: "Bridge API para consultas automatizadas"
5. Após criar, você receberá:
   - **API ID** (número)
   - **API Hash** (string longa)

#### **PHONE_NUMBER**
- Seu número completo com código do país
- Exemplo: `+5511912345678`

#### **CHAT_ID**
- ID numérico do grupo onde o bot de consultas está
- Como encontrar:
  1. Adicione o bot `@userinfobot` ao grupo
  2. Envie qualquer mensagem no grupo
  3. O bot responderá com o Chat ID
  4. Ou use `@get_id_bot` para obter IDs

### 2. Exemplo de .env Configurado

```bash
# API Configuration
API_KEY=sua_chave_secreta_aqui_12345
PORT=3000

# Telegram Configuration - CONFIGURADO
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890abcdef12
CHAT_ID=-1001234567890
PHONE_NUMBER=+5511912345678

# Python Service URL
PYTHON_SERVICE_URL=http://localhost:8000
```

### 3. Configuração Passo a Passo

#### Método 1: Editar Manualmente
1. Abra o arquivo `.env` no editor de código
2. Substitua os valores placeholder:
   ```bash
   # Mude de:
   API_KEY=demo_key_12345
   # Para:
   API_KEY=minha_chave_secreta_123
   
   # Mude de:
   API_ID=your_api_id_here
   # Para:
   API_ID=12345678
   
   # Mude de:
   API_HASH=your_api_hash_here
   # Para:
   API_HASH=abcdef1234567890abcdef1234567890abcdef12
   
   # Mude de:
   CHAT_ID=your_chat_id_here
   # Para:
   CHAT_ID=-1001234567890
   
   # Mude de:
   PHONE_NUMBER=your_phone_number_here
   # Para:
   PHONE_NUMBER=+5511912345678
   ```

#### Método 2: Via Interface Web
1. Acesse: http://localhost:9000
2. Vá para "Configuração de Produção"
3. Preencha os campos
4. Clique em "Salvar Configuração"

### 4. Validação da Configuração

#### Testar Conexão Python
```bash
cd telegram_service
python -c "
from telethon import TelegramClient
import os
from dotenv import load_dotenv

load_dotenv()
api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
phone = os.getenv('PHONE_NUMBER')

print(f'API ID: {api_id}')
print(f'API Hash: {api_hash[:10]}...')
print(f'Phone: {phone}')
print('Configuração carregada com sucesso!')
"
```

#### Testar API
```bash
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sua_api_key" \
  -d '{"type": "cpf", "query": "12345678901"}'
```

### 5. Configuração para Produção

#### Segurança Adicional
```bash
# Use chaves fortes
API_KEY=tg_bridge_prod_$(date +%s)_$(openssl rand -hex 16)

# Configure CORS se necessário
CORS_ORIGIN=https://seu-dominio.com

# Rate limiting
RATE_LIMIT_MAX=100
RATE_LIMIT_WINDOW=900000
```

#### Variáveis Opcionais
```bash
# Logging
LOG_LEVEL=info
LOG_FILE=logs/app.log

# Performance
WORKERS=4
MAX_CONNECTIONS=1000
TIMEOUT=30000

# Monitoramento
ENABLE_METRICS=true
METRICS_PORT=9090
```

### 6. Solução de Problemas

#### Erro Comum: Invalid API ID/Hash
- **Causa**: API ID ou Hash incorretos
- **Solução**: Verifique os valores em https://my.telegram.org/apps

#### Erro Comum: Chat ID inválido
- **Causa**: Chat ID incorreto ou sem o `-100`
- **Solução**: Use `@userinfobot` para obter o ID correto

#### Erro Comum: Phone number format
- **Causa**: Formato incorreto do número
- **Solução**: Use formato `+55DDNNNNNNNNN`

#### Erro Comum: Permissões negadas
- **Causa**: Bot não tem permissão no grupo
- **Solução**: Adicione o bot como administrador do grupo

### 7. Configuração Rápida (Template)

Copie e cole este template, substituindo os valores:

```bash
# API Configuration
API_KEY=telegram_bridge_prod_2024
PORT=3000

# Telegram Configuration
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890abcdef12
CHAT_ID=-1001234567890
PHONE_NUMBER=+5511912345678

# Python Service URL
PYTHON_SERVICE_URL=http://localhost:8000
```

### 8. Próximos Passos

1. ✅ Configure o `.env`
2. ✅ Teste a conexão Python
3. ✅ Teste a API Node.js
4. ✅ Use a GUI para testar consultas
5. 🚀 Deploy em produção com Docker

---

**💡 Dica**: Mantenha seu `.env` privado e nunca adicione ao Git! Adicione `.env` ao seu `.gitignore`.

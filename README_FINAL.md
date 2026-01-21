# 🚀 Telegram Query Bridge - Sistema Completo

## 📋 Visão Geral

Sistema completo de **Gateway de API** que conecta requisições HTTP a consultas automatizadas no Telegram, com interface moderna de gerenciamento.

### 🎯 Funcionalidades Principais
- 🔗 **API REST** para consultas automatizadas
- 🤖 **Integração Telegram** via Userbot
- 🎨 **GUI Moderna** para controle total
- 🐳 **Docker** para deploy em produção
- 📊 **Monitoramento** em tempo real
- 🔧 **Configuração** simplificada

---

## 🚀 Quick Start (3 minutos)

### 1️⃣ Configurar Credenciais
```bash
# Opção A: Automático (Windows)
npm run setup

# Opção B: Manual
cp .env.template .env
# Edite .env com suas credenciais
```

### 2️⃣ Obter Credenciais Telegram
- **API ID/Hash**: https://my.telegram.org/apps
- **Chat ID**: Use `@userinfobot` no grupo
- **Phone**: Formato `+55DDNNNNNNNNN`

### 3️⃣ Iniciar Sistema
```bash
# Inicia tudo (GUI + API + Python)
npm start

# Acesse: http://localhost:9000
```

---

## 🌐 Interface Web

Acesse **http://localhost:9000** para:

### 📊 Dashboard
- Status em tempo real dos serviços
- Monitoramento de saúde
- Logs em tempo real

### 🎛️ Controle de Serviços
- Iniciar/parar serviços individualmente
- Reiniciar com um clique
- Configurar timeouts

### 🧪 Testes de API
- Testar todos os tipos de consulta
- Simular cliques em botões
- Ver respostas em tempo real

### ⚙️ Configuração
- Formulários amigáveis para .env
- Salvar configurações
- Alternar ambientes

---

## 📋 Comandos Disponíveis

```bash
npm start          # Iniciar sistema completo
npm run setup      # Configurar .env automaticamente
npm run python     # Apenas serviço Python
npm run api        # Apenas API Node.js
npm run manager    # Apenas GUI Web
npm run stop       # Parar todos os serviços
npm run restart    # Reiniciar sistema
npm run dev        # Modo desenvolvimento
npm run prod       # Modo produção

# Docker
npm run docker:build    # Build containers
npm run docker:up        # Iniciar containers
npm run docker:down      # Parar containers
npm run docker:logs      # Ver logs

# Deploy
npm run deploy      # Deploy automatizado
```

---

## 🔗 Endpoints da API

### Consultas
```http
POST /query
Headers: X-API-Key: sua_api_key
Body: {
  "type": "cpf",
  "query": "12345678901"
}
```

### Botões Interativos
```http
POST /button
Headers: X-API-Key: sua_api_key
Body: {
  "button_text": "Ver Resumo",
  "original_command": "/cpf 12345678901"
}
```

### Health Check
```http
GET /health
GET /python/health
GET /manager/health
```

---

## 🎯 Tipos de Consulta Suportados

| Tipo | Comando | Descrição |
|------|---------|-----------|
| `cpf` | `/cpf {numero}` | Consulta CPF |
| `nome` | `/nome {nome}` | Consulta por nome |
| `telefone` | `/telefone {numero}` | Consulta telefone |
| `placa` | `/placa {placa}` | Consulta veículo |
| `email` | `/email {email}` | Consulta email |
| `cep` | `/cep {cep}` | Consulta CEP |
| `cnpj` | `/cnpj {cnpj}` | Consulta CNPJ |
| `foto` | `/foto {dados}` | Consulta foto |
| `titulo` | `/titulo {titulo}` | Consulta título |
| `mae` | `/mae {nome}` | Consulta mãe |

---

## 🤖 Botões Interativos

Após consulta, o sistema oferece 4 opções:

- **🔒 Ver no Privado**: Dados completos sensíveis
- **📋 Ver Resumo**: Resumo estruturado da consulta
- **📄 Baixar TXT**: Gerar arquivo para download
- **❌ Fechar**: Encerrar sessão

---

## 🐳 Deploy em Produção

### Docker Compose
```bash
# Build e iniciar todos os serviços
docker-compose up -d

# Ver status
docker-compose ps

# Ver logs
docker-compose logs -f
```

### Deploy Automatizado
```bash
# Script completo de deploy
./deploy.sh
```

### Variáveis de Produção
```bash
# Copie template de produção
cp .env.production .env
# Configure suas credenciais reais
```

---

## 📁 Estrutura do Projeto

```
scrapper-search/
├── 📄 api/index.js              # API Node.js principal
├── 🐍 telegram_service/
│   ├── main.py                  # Serviço Python real
│   ├── demo.py                  # Modo demonstração
│   └── Dockerfile               # Container Python
├── 🌐 web/index.html            # Interface web
├── 🐳 server.py                 # Backend da GUI
├── ⚙️ docker-compose.yml        # Orquestração
├── 🔧 deploy.sh                 # Script deploy
├── 📋 package.json              # Dependências Node
├── 📄 requirements.txt          # Dependências Python
├── 🔐 .env.template             # Template configuração
├── 📖 QUICK_START.md            # Guia rápido
├── 📖 CONFIGURACAO.md           # Configuração detalhada
└── 🚀 start-complete.bat        # Inicialização
```

---

## 🔧 Configuração Avançada

### Environment Variables
```bash
# API
API_KEY=sua_chave_secreta
PORT=3000
NODE_ENV=production

# Telegram
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890abcdef12
CHAT_ID=-1001234567890
PHONE_NUMBER=+5511912345678

# Services
PYTHON_SERVICE_URL=http://localhost:8000

# Performance
WORKERS=4
MAX_CONNECTIONS=1000
TIMEOUT=30000

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
```

### Security Best Practices
- ✅ Use chaves fortes e únicas
- ✅ Configure CORS em produção
- ✅ Use rate limiting
- ✅ Mantenha .env privado
- ✅ Use HTTPS em produção

---

## 🧪 Testes e Validação

### Testar Conexão Python
```bash
cd telegram_service
python -c "
from telethon import TelegramClient
import os
from dotenv import load_dotenv
load_dotenv()
print('✅ Configuração Python OK!')
"
```

### Testar API Node.js
```bash
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sua_api_key" \
  -d '{"type": "cpf", "query": "12345678901"}'
```

### Testar Interface
```bash
curl http://localhost:9000/health
```

---

## 🆘 Troubleshooting

### Problemas Comuns

#### "Porta em uso"
```bash
# Windows
netstat -ano | findstr :3000
taskkill /F /PID [PID]

# Linux/Mac
lsof -ti:3000 | xargs kill -9
```

#### "Invalid API credentials"
- Verifique https://my.telegram.org/apps
- Confirme API ID (número) e API Hash (32 chars)

#### "Chat ID inválido"
- Use `@userinfobot` para obter ID correto
- Grupos começam com `-100`

#### "Python service unavailable"
- Verifique se Python está instalado
- Instale dependências: `pip install -r requirements.txt`

---

## 📈 Monitoramento

### Health Checks
- **Python**: `GET /health` (porta 8000)
- **Node.js**: `GET /health` (porta 3000)
- **Manager**: `GET /health` (porta 9000)

### Logs
- **Aplicação**: `logs/app.log`
- **Docker**: `docker-compose logs -f`
- **GUI**: Console em tempo real

### Métricas
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001

---

## 🤝 Contribuição

1. Fork o projeto
2. Crie branch: `git checkout -b feature/nova-funcionalidade`
3. Commit: `git commit -m 'Add nova funcionalidade'`
4. Push: `git push origin feature/nova-funcionalidade`
5. Pull Request

---

## 📄 Licença

MIT License - Veja [LICENSE](LICENSE) para detalhes.

---

## 🎉 Suporte

- 📖 **Documentação**: Veja arquivos .md
- 🐛 **Issues**: Reporte no GitHub
- 💬 **Suporte**: Telegram community

---

## 🚀 Próximo Passos

1. ✅ Configure o `.env` com `npm run setup`
2. ✅ Inicie com `npm start`
3. ✅ Acesse http://localhost:9000
4. ✅ Teste as consultas
5. ✅ Configure para produção
6. 🚀 **Deploy com Docker!**

---

**🎯 Sistema completo e pronto para uso!**

*Acesse http://localhost:9000 para começar a usar.*

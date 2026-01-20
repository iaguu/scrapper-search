# 🚀 Quick Start - Telegram Query Bridge

## ⚡ Configuração Rápida (3 minutos)

### 🎯 Opção 1: Automático (Recomendado)

#### Windows:
```bash
# Execute o script automático
setup-env.bat
```

#### Linux/Mac:
```bash
# Dê permissão e execute
chmod +x setup-env.sh
./setup-env.sh
```

### 🎯 Opção 2: Manual Rápido

1. **Copie o template:**
   ```bash
   cp .env.template .env
   ```

2. **Edite apenas estas linhas:**
   ```bash
   API_ID=12345678                    # Seu API ID numérico
   API_HASH=abcdef1234567890abc...    # Seu API Hash (32 chars)
   CHAT_ID=-1001234567890             # ID do grupo
   PHONE_NUMBER=+5511912345678        # Seu número
   ```

### 🎯 Opção 3: Via Interface Web

1. Inicie os serviços: `npm start`
2. Acesse: http://localhost:9000
3. Vá em "Configuração de Produção"
4. Preencha e salve

---

## 🔑 Onde Obter Credenciais

### 1. Telegram API ID/Hash
- Acesse: https://my.telegram.org/apps
- Login → "Create application"
- Preencha: "Telegram Query Bridge"
- Copie **API ID** e **API Hash**

### 2. Chat ID do Grupo
- Adicione `@userinfobot` ao grupo
- Envie qualquer mensagem
- Bot responde com o Chat ID

### 3. Seu Número
- Formato: `+55DDNNNNNNNNN`
- Exemplo: `+5511912345678`

---

## 🚀 Iniciar Sistema

### Após configurar .env:

```bash
# Inicia tudo (GUI + API + Python)
npm start

# Ou individualmente:
npm run python     # Apenas Python
npm run api        # Apenas Node.js
npm run manager    # Apenas GUI
```

### Acessar Sistema:
- 🌐 **GUI Web**: http://localhost:9000
- 🔗 **API Node**: http://localhost:3000
- 🐍 **Python**: http://localhost:8000

---

## 🧪 Teste Rápido

```bash
# Testar API
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sua_api_key" \
  -d '{"type": "cpf", "query": "12345678901"}'

# Testar saúde dos serviços
curl http://localhost:9000/health
curl http://localhost:3000/health
curl http://localhost:8000/health
```

---

## 🛠️ Comandos Úteis

```bash
npm start         # Iniciar tudo
npm run stop      # Parar tudo
npm run restart   # Reiniciar tudo
npm run dev       # Modo dev
npm run prod      # Modo prod
```

---

## ⚠️ Importante

- **Nunca** compartilhe seu arquivo `.env`
- **Sempre** adicione `.env` ao `.gitignore`
- **Use** chaves fortes em produção
- **Teste** em desenvolvimento antes de produção

---

## 🆘 Problemas Comuns

### "Invalid API ID/Hash"
- Verifique os valores em https://my.telegram.org/apps
- API ID é número, API Hash é string de 32 chars

### "Chat ID inválido"
- Use `@userinfobot` para obter ID correto
- Grupos geralmente começam com `-100`

### "Phone format error"
- Use formato `+55DDNNNNNNNNN`
- Inclua o `+` e código do país

---

## 🎉 Pronto!

Após configurar, você terá:
- ✅ Sistema completo rodando
- ✅ GUI moderna para controle
- ✅ API funcionando
- ✅ Integração com Telegram

**Acesse http://localhost:9000 para começar!** 🚀

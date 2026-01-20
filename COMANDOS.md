# Comandos para Ativação do Projeto

## 🚀 Iniciar Serviços

### 1. Iniciar Serviço Python (Telegram Service)
```bash
# Opção 1: Direto no diretório
cd telegram_service
python -m uvicorn demo:app --host 127.0.0.1 --port 8000

# Opção 2: Via script (se existir)
python demo.py

# Opção 3: Via npm (configurado)
npm run py-service
```

### 2. Iniciar API Node.js (em outro terminal)
```bash
# Opção 1: Direto
npm start

# Opção 2: Via node
node api/index.js
```

## 🔄 Comandos em Segundo Plano (Background)

### Windows PowerShell
```powershell
# Python Service
Start-Job -ScriptBlock { cd telegram_service; python -m uvicorn demo:app --host 0.0.0.0 --port 8000 }

# Node.js API
Start-Job -ScriptBlock { npm start }
```

### Git Bash / WSL
```bash
# Python Service
cd telegram_service && python -m uvicorn demo:app --host 0.0.0.0 --port 8000 &

# Node.js API
npm start &
```

## 🛑 Parar Serviços

### Parar Processos Específicos
```bash
# Windows
taskkill /F /IM python.exe
taskkill /F /IM node.exe

# Linux/Mac
pkill -f python
pkill -f node
```

### Parar por Porta
```bash
# Windows
netstat -ano | findstr :8000
taskkill /F /PID [PID_DO_PROCESSO]

# Linux/Mac
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

## 🧪 Testes Rápidos

### Verificar Saúde dos Serviços
```bash
# Python Service
curl http://localhost:8000/health

# Node.js API
curl http://localhost:3000/health
```

### Testar Consulta
```bash
# PowerShell
Invoke-RestMethod -Uri http://localhost:3000/query -Method POST -ContentType "application/json" -Headers @{"X-API-Key"="demo_key_12345"} -Body '{"type": "cpf", "query": "12345678901"}'

# curl
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo_key_12345" \
  -d '{"type": "cpf", "query": "12345678901"}'
```

## 📝 Script de Inicialização Completa

### Windows (start_services.bat)
```batch
@echo off
echo Iniciando Telegram Query Bridge API...

echo Iniciando Python Service...
cd telegram_service
start "Python Service" cmd /k "python -m uvicorn demo:app --host 0.0.0.0 --port 8000"

echo Aguardando 3 segundos...
timeout /t 3 /nobreak

echo Iniciando Node.js API...
cd ..
start "Node.js API" cmd /k "npm start"

echo Serviços iniciados!
echo Python: http://localhost:8000
echo Node.js: http://localhost:3000
pause
```

### Linux/Mac (start_services.sh)
```bash
#!/bin/bash
echo "Iniciando Telegram Query Bridge API..."

echo "Iniciando Python Service..."
cd telegram_service
python -m uvicorn demo:app --host 0.0.0.0 --port 8000 &
PYTHON_PID=$!

echo "Aguardando 3 segundos..."
sleep 3

echo "Iniciando Node.js API..."
cd ..
npm start &
NODE_PID=$!

echo "Serviços iniciados!"
echo "Python: http://localhost:8000 (PID: $PYTHON_PID)"
echo "Node.js: http://localhost:3000 (PID: $NODE_PID)"
echo "Para parar: kill $PYTHON_PID $NODE_PID"
```

## 🔧 Configuração do Ambiente

### Instalar Dependências
```bash
# Node.js
npm install

# Python
pip install -r requirements.txt
```

### Variáveis de Ambiente
```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar .env com suas credenciais
notepad .env  # Windows
nano .env      # Linux/Mac
```

## 📊 Monitoramento

### Ver Logs em Tempo Real
```bash
# Python Service logs
tail -f telegram_service/logs/app.log

# Node.js API logs
tail -f logs/api.log
```

### Verificar Portas em Uso
```bash
# Windows
netstat -ano | findstr ":8000\|:3000"

# Linux/Mac
lsof -i :8000
lsof -i :3000
```

## ⚠️ Importante

1. **Sempre inicie o Python primeiro** (porta 8000)
2. **Aguarde 2-3 segundos** antes de iniciar o Node.js
3. **Configure o .env** antes de usar em produção
4. **Use portas diferentes** se houver conflitos

## 🆘 Solução de Problemas

### Porta Ocupada
```bash
# Mudar porta Python (8000 -> 8001)
python -m uvicorn demo:app --host 0.0.0.0 --port 8001

# Mudar porta Node.js (3000 -> 3001)
PORT=3001 npm start
```

### Conexão Recusada
```bash
# Verificar se serviços estão rodando
curl http://localhost:8000/health
curl http://localhost:3000/health

# Verificar firewalls/Antivírus
```

### Permissões (Linux/Mac)
```bash
chmod +x start_services.sh
./start_services.sh
```

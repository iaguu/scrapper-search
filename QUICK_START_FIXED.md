# Telegram Query Bridge - Guia Rápido

## Configuração Inicial

1. **Variáveis de Ambiente (.env)**
   ```
   API_ID=33254011
   API_HASH=10e6eca80277e0258a5b72b1de93b27a
   CHAT_ID=@ConsultasBuscasBot
   PHONE_NUMBER=+5511988045139
   ```

2. **Iniciar Serviços**
   ```bash
   # Iniciar todos os serviços
   python server.py
   ```

3. **Acessar Dashboard**
   - Abra: http://localhost:9000
   - Dashboard gerencia todos os serviços

## Autenticação Telegram

1. **Solicitar Autenticação**
   - Clique em "Solicitar Autenticação" no dashboard
   - Código será enviado para seu Telegram

2. **Verificar Código**
   - Digite o código recebido
   - Clique em verificar

## Funcionalidades

- ✅ Controle de serviços (Python/Node.js)
- ✅ Autenticação simplificada do Telegram
- ✅ Monitoramento em tempo real
- ✅ Logs e status detalhados

## Endpoints

- Manager: http://localhost:9000
- Python Service: http://localhost:8001
- Node.js API: http://localhost:3000

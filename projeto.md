# Project Initialization: Telegram Query Bridge API

## 1. Visão Geral do Projeto
Este projeto é um **Gateway de API** que conecta requisições HTTP externas a um grupo de consultas no Telegram. O sistema atua como um "Userbot" (usuário automatizado) que envia comandos pré-definidos para um grupo, aguarda a resposta do bot/sistema do grupo e retorna os dados via JSON para o solicitante original.

**Objetivo:** Automatizar consultas (/cpf, /nome, etc.) através de uma API REST simples.

## 2. Arquitetura do Sistema
O fluxo de dados segue o padrão **Síncrono via Queue**:

`Usuário (HTTP Request)` -> `Node.js API (Controller)` -> `Python Bridge (Telethon Client)` -> `Telegram Group` -> `Wait for Reply` -> `Python Bridge` -> `Node.js API` -> `Usuário (JSON Response)`

### Componentes:
1.  **Public API (Node.js/Express):**
    * Recebe requisições POST com o tipo de consulta e o dado.
    * Gerencia autenticação básica (API Key).
    * Repassa o pedido para o serviço Python.
2.  **Telegram Service (Python/Telethon + FastAPI):**
    * Roda um servidor HTTP interno leve.
    * Mantém uma sessão do Telegram aberta (Userbot).
    * Envia a mensagem para o `CHAT_ID` alvo.
    * Escuta eventos de `NewMessage` ou monitora respostas (reply) para capturar o resultado.
    * Faz o parse da resposta (texto/botões).

## 3. Especificações Técnicas

### Stack
* **Backend:** Node.js (v18+)
* **Telegram/Logic:** Python 3.9+
* **Libraries Python:** `telethon` (MTProto client), `fastapi` (Internal Server), `uvicorn`.
* **Libraries Node:** `express`, `axios`, `dotenv`.

### Comandos Suportados (Input Data)
O sistema deve aceitar um `type` e um `query`. Mapeamento:
* `cpf` -> `/cpf {query}`
* `telefone` -> `/telefone {query}`
* `foto` -> `/foto {query}`
* `placa` -> `/placa {query}`
* `nome` -> `/nome {query}`
* `email` -> `/email {query}`
* `cep` -> `/cep {query}`
* `cnpj` -> `/cnpj {query}`
* `titulo` -> `/titulo {query}`
* `mae` -> `/mae {query}`

## 4. Regras de Negócio e Tratamento de Erros
1.  **Timeout:** O Telegram pode demorar. Definir timeout de 30s. Se não houver resposta, retornar erro 504.
2.  **Concorrência:** O serviço Python deve ser capaz de lidar com múltiplas requisições, usando IDs únicos para associar a pergunta à resposta (se o grupo suportar "Reply"). Caso o grupo não use "Reply", implementar uma fila (FIFO) para garantir que a resposta lida pertence ao comando enviado.
3.  **Sanitização:** Remover caracteres especiais dos inputs antes de enviar ao Telegram.

## 5. Estrutura de Diretórios Sugerida
/
├── api/                  # Servidor Node.js
│   ├── index.js
│   └── routes.js
├── telegram_service/     # Servidor Python
│   ├── main.py           # FastAPI + Telethon logic
│   └── session/          # Arquivos de sessão do Telegram
├── package.json
├── requirements.txt
└── project_init.md

package:

{
  "name": "telegram-query-bridge",
  "version": "1.0.0",
  "description": "Bridge API Node to Telegram",
  "main": "api/index.js",
  "scripts": {
    "start": "node api/index.js",
    "py-service": "cd telegram_service && uvicorn main:app --port 8000 --reload"
  },
  "dependencies": {
    "axios": "^1.6.0",
    "body-parser": "^1.20.2",
    "dotenv": "^16.3.1",
    "express": "^4.18.2"
  }
}

requirements:

fastapi==0.104.1
uvicorn==0.24.0
telethon==1.32.1
python-dotenv==1.0.0
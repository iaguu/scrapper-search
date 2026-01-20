# Telegram Query Bridge API

Gateway de API que conecta requisições HTTP externas a um grupo de consultas no Telegram.

## Instalação

### Pré-requisitos
- Node.js 18+
- Python 3.9+

### Configuração

1. Copie o arquivo `.env.example` para `.env`:
```bash
cp .env.example .env
```

2. Configure as variáveis de ambiente no arquivo `.env`:
```
API_KEY=sua_chave_api_aqui
PORT=3000

API_ID=seu_api_id_telegram
API_HASH=seu_api_hash_telegram
CHAT_ID=id_do_grupo_telegram
PHONE_NUMBER=seu_numero_telefone

PYTHON_SERVICE_URL=http://localhost:8000
```

### Instalação das dependências

#### Node.js
```bash
npm install
```

#### Python
```bash
pip install -r requirements.txt
```

## Execução

### Iniciar o serviço Python (Telegram)
```bash
npm run py-service
```

### Iniciar a API Node.js (em outro terminal)
```bash
npm start
```

## Uso

### Endpoint principal
```
POST /query
Headers: X-API-Key: sua_chave_api
Body: {
  "type": "cpf",
  "query": "12345678901"
}
```

### Tipos de consulta suportados
- `cpf` -> `/cpf {query}`
- `telefone` -> `/telefone {query}`
- `foto` -> `/foto {query}`
- `placa` -> `/placa {query}`
- `nome` -> `/nome {query}`
- `email` -> `/email {query}`
- `cep` -> `/cep {query}`
- `cnpj` -> `/cnpj {query}`
- `titulo` -> `/titulo {query}`
- `mae` -> `/mae {query}`

### Health check
```
GET /health
```

## Exemplo de requisição
```bash
curl -X POST http://localhost:3000/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sua_chave_api" \
  -d '{"type": "cpf", "query": "12345678901"}'
```

## Arquitetura
- **Node.js API**: Recebe requisições HTTP e gerencia autenticação
- **Python Service**: Conecta-se ao Telegram via Telethon e processa comandos
- **Timeout**: 30 segundos para resposta do Telegram

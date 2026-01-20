const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;
const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL || 'http://localhost:8000';

// Middleware
app.use(bodyParser.json());

// Middleware de autenticação
const authenticateApiKey = (req, res, next) => {
  const apiKey = req.headers['x-api-key'];
  if (!apiKey || apiKey !== process.env.API_KEY) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
};

// Mapeamento de comandos
const commandMap = {
  'cpf': '/cpf',
  'telefone': '/telefone',
  'foto': '/foto',
  'placa': '/placa',
  'nome': '/nome',
  'email': '/email',
  'cep': '/cep',
  'cnpj': '/cnpj',
  'titulo': '/titulo',
  'mae': '/mae'
};

// Rota principal de consulta
app.post('/query', authenticateApiKey, async (req, res) => {
  try {
    const { type, query } = req.body;

    if (!type || !query) {
      return res.status(400).json({ error: 'Missing required fields: type and query' });
    }

    if (!commandMap[type]) {
      return res.status(400).json({ error: 'Invalid query type' });
    }

    const command = `${commandMap[type]} ${query}`;

    // Enviar requisição para o serviço Python
    const response = await axios.post(`${PYTHON_SERVICE_URL}/send-command`, {
      command: command,
      timeout: 30000 // 30 segundos timeout
    });

    res.json(response.data);

  } catch (error) {
    console.error('Error:', error.message);
    
    if (error.code === 'ECONNREFUSED') {
      return res.status(503).json({ error: 'Python service unavailable' });
    }
    
    if (error.response && error.response.status === 504) {
      return res.status(504).json({ error: 'Telegram timeout' });
    }

    res.status(500).json({ error: 'Internal server error' });
  }
});

// Rota para processar cliques em botões
app.post('/button', authenticateApiKey, async (req, res) => {
  try {
    const { button_text, original_command } = req.body;

    if (!button_text || !original_command) {
      return res.status(400).json({ error: 'Missing required fields: button_text and original_command' });
    }

    // Enviar requisição para o serviço Python
    const response = await axios.post(`${PYTHON_SERVICE_URL}/handle-button`, {
      button_text: button_text,
      original_command: original_command,
      timeout: 15000 // 15 segundos timeout
    });

    res.json(response.data);

  } catch (error) {
    console.error('Error:', error.message);
    
    if (error.code === 'ECONNREFUSED') {
      return res.status(503).json({ error: 'Python service unavailable' });
    }
    
    if (error.response && error.response.status === 504) {
      return res.status(504).json({ error: 'Button processing timeout' });
    }

    res.status(500).json({ error: 'Internal server error' });
  }
});

// Rota de health check
app.get('/health', (req, res) => {
  res.json({ status: 'OK', timestamp: new Date().toISOString() });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');
const cors = require('cors');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;
const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL || 'http://localhost:8001';

// Middleware
app.use(cors());
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

// Rota principal de consulta com retry e reconexão
app.post('/query', authenticateApiKey, async (req, res) => {
  let retries = 3;
  let lastError = null;
  
  while (retries > 0) {
    try {
      const { type, query } = req.body;

      if (!type || !query) {
        return res.status(400).json({ error: 'Missing required fields: type and query' });
      }

      if (!commandMap[type]) {
        return res.status(400).json({ error: 'Invalid query type' });
      }

      const command = `${commandMap[type]} ${query}`;

      // Verificar se o serviço Python está disponível antes de enviar
      const healthCheck = await axios.get(`${PYTHON_SERVICE_URL}/health`, { timeout: 5000 });
      
      if (!healthCheck.data.telegram_connected && !healthCheck.data.status === 'OK') {
        console.warn('Python service não está totalmente conectado ao Telegram, tentando mesmo assim...');
      }

      // Enviar requisição para o serviço Python com timeout aumentado
      const response = await axios.post(`${PYTHON_SERVICE_URL}/send-command`, {
        command: command,
        timeout: 45000 // 45 segundos timeout aumentado
      });

      return res.json(response.data);

    } catch (error) {
      lastError = error;
      retries--;
      
      console.error(`Tentativa ${4 - retries} falhou:`, error.message);
      
      if (error.code === 'ECONNREFUSED') {
        console.log('Serviço Python indisponível, tentando reconectar...');
        await new Promise(resolve => setTimeout(resolve, 3000)); // Esperar 3s
      } else if (error.code === 'ECONNRESET' || error.code === 'ETIMEDOUT') {
        console.log('Conexão perdida, tentando reconectar...');
        await new Promise(resolve => setTimeout(resolve, 2000)); // Esperar 2s
      } else {
        // Para outros erros, não tentar retry
        break;
      }
    }
  }

  // Todas as tentativas falharam
  console.error('Erro final após todas as tentativas:', lastError.message);
  
  if (lastError.code === 'ECONNREFUSED') {
    return res.status(503).json({ 
      error: 'Python service unavailable',
      details: 'Serviço Python não está respondendo. Verifique se o serviço está rodando na porta 8000.',
      retry_attempts: 3
    });
  }
  
  if (lastError.code === 'ETIMEDOUT') {
    return res.status(504).json({ 
      error: 'Telegram timeout',
      details: 'Timeout ao processar comando no Telegram. Tente novamente.',
      retry_attempts: 3
    });
  }

  return res.status(500).json({ 
    error: 'Internal server error',
    details: lastError.message,
    retry_attempts: 3
  });
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

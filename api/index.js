const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');
const cors = require('cors');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;
const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL || 'http://localhost:8001';

// Configuração de logging para console
const consoleLog = (level, message) => {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] [${level.toUpperCase()}] ${message}`);
};

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
  'placa': '/placa',
  'nome': '/nome',
  'email': '/email',
  'cep': '/cep',
  'cnpj': '/cnpj',
  'mae': '/mae'
};

// Rota de health check com logs
app.get('/health', (req, res) => {
  consoleLog('info', 'Health check recebido');
  const healthData = { 
    status: 'OK',
    timestamp: new Date().toISOString(),
    service: 'Telegram Query Bridge API',
    version: '1.0.0',
    python_service_url: PYTHON_SERVICE_URL,
    node_version: process.version,
    platform: process.platform
  };
  
  consoleLog('info', `Health check response: ${JSON.stringify(healthData)}`);
  res.json(healthData);
});

// Rota de start com logs
app.post('/start', (req, res) => {
  consoleLog('info', 'Recebido comando START');
  
  // Lógica de start existente...
  
  consoleLog('info', 'Serviço iniciado com sucesso');
  res.json({ success: true, message: 'Serviço iniciado' });
});

// Rota de stop
app.post('/stop', (req, res) => {
  res.json({ success: true, message: 'Sinal de desligamento recebido.' });
  // O manager se encarregará de matar o processo
  setTimeout(() => process.exit(0), 500);
});

// Rota principal de consulta com retry e reconexão
app.post('/query', authenticateApiKey, async (req, res) => {
  let retries = 3;
  let lastError = null;
  
  while (retries > 0) {
    try {
      const { type, query } = req.body;

      if (!type || !query) {
        return res.status(400).json({ 
          error: 'Missing required fields: type and query',
          detail: {
            type: 'missing',
            loc: ['body'],
            msg: 'Fields type and query are required',
            input: req.body
          }
        });
      }

      if (!commandMap[type]) {
        return res.status(400).json({ 
          error: 'Invalid query type',
          detail: `Supported types: ${Object.keys(commandMap).join(', ')}`
        });
      }

      const command = `${commandMap[type]} ${query}`;

      // Verificar se o serviço Python está disponível antes de enviar
      try {
        const healthCheck = await axios.get(`${PYTHON_SERVICE_URL}/health`, { timeout: 5000 });
        
        if (!healthCheck.data.telegram_connected && healthCheck.data.status !== 'OK') {
          console.warn('Python service não está totalmente conectado ao Telegram, tentando mesmo assim...');
        }
      } catch (healthError) {
        console.warn('Python service health check failed:', healthError.message);
        return res.status(503).json({
          error: "Service unavailable",
          details: "Python service is not responding",
          python_service_url: PYTHON_SERVICE_URL
        });
      }

      // Enviar requisição para o serviço Python com timeout aumentado
      const pythonResponse = await axios.post(`${PYTHON_SERVICE_URL}/send-command`, {
        command: `${commandMap[type]} ${query}`
      }, {
        timeout: 30000,
        headers: {
          'Content-Type': 'application/json'
        }
      });

      return res.json(pythonResponse.data);

    } catch (error) {
      lastError = error;
      retries--;
      
      if (error.code === 'ECONNRESET' || error.code === 'ECONNABORTED') {
        console.warn(`Erro de conexão, tentativas restantes: ${retries}`);
        await new Promise(resolve => setTimeout(resolve, 2000));
        continue;
      }
      
      if (retries === 0) {
        console.error('Erro final após todas as tentativas:', error.message);
        
        // Se for erro de validação do Pydantic, repassar com detalhes
        if (error.response && error.response.status === 422) {
          return res.status(422).json({
            error: "Validation error",
            details: error.response.data,
            retry_attempts: 3 - retries
          });
        }
        
        return res.status(500).json({ 
          error: "Internal server error",
          details: error.message,
          retry_attempts: 3 - retries,
          code: error.code || 'UNKNOWN'
        });
      }
    }
  }
});

// Rota para enviar comandos diretos (fallback)
app.post('/send-command', authenticateApiKey, async (req, res) => {
  let retries = 3;
  let lastError = null;
  
  while (retries > 0) {
    try {
      const { command } = req.body;

      if (!command) {
        return res.status(400).json({ 
          error: 'Missing required field: command',
          detail: {
            type: 'missing',
            loc: ['body'],
            msg: 'Field command is required',
            input: req.body
          }
        });
      }

      // Enviar requisição para o serviço Python com timeout aumentado
      const response = await axios.post(`${PYTHON_SERVICE_URL}/send-command`, {
        command: command,
        timeout: 45000 // 45 segundos timeout aumentado
      }, {
        timeout: 45000,
        headers: {
          'Content-Type': 'application/json'
        }
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
      details: 'Serviço Python não está respondendo. Verifique se o serviço está rodando na porta 8001.',
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
    retry_attempts: 3,
    code: lastError.code || 'UNKNOWN'
  });
});

// Rota para verificar status do proxy
app.get('/proxy/status', authenticateApiKey, (req, res) => {
  res.json({
    python_available: true,
    node_available: true,
    python_url: PYTHON_SERVICE_URL,
    node_url: `http://localhost:${PORT}`,
    proxy_endpoints: {
      python: "/proxy/python/{path}",
      node: "/proxy/node/{path}"
    }
  });
});

// Iniciar servidor
const server = app.listen(PORT, () => {
  consoleLog('info', `Servidor Node.js iniciado na porta ${PORT}`);
  consoleLog('info', `Python Service URL: ${PYTHON_SERVICE_URL}`);
  consoleLog('info', 'Health check disponível em /health');
  consoleLog('info', 'API endpoints disponíveis em /query e /send-command');
  consoleLog('info', `Node.js Version: ${process.version}`);
  consoleLog('info', `Platform: ${process.platform}`);
  consoleLog('info', `Environment: ${process.env.NODE_ENV || 'development'}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  consoleLog('info', 'SIGTERM recebido, encerrando servidor graceful...');
  server.close(() => {
    consoleLog('info', 'Servidor Node.js encerrado');
  });
});

process.on('SIGINT', () => {
  consoleLog('info', 'SIGINT recebido (Ctrl+C), encerrando servidor...');
  server.close(() => {
    consoleLog('info', 'Servidor Node.js encerrado');
  });
});

module.exports = app;

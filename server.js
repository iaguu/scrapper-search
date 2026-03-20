const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const fs = require('fs-extra');
const path = require('path');
const crypto = require('crypto');
const winston = require('winston');
const TelegramService = require('./services/TelegramService');
require('dotenv').config();

class TelegramBridgeServer {
    constructor() {
        this.app = express();
        this.port = process.env.PORT || 3000;
        this.telegramService = new TelegramService();
        this.apiKey = process.env.API_KEY || 'demo_key_12345';
        this.logger = this.setupLogger();
        this.pendingCodes = new Map();
        
        this.setupMiddleware();
        this.setupRoutes();
        this.setupErrorHandling();
    }

    setupLogger() {
        return winston.createLogger({
            level: 'info',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.colorize(),
                winston.format.printf(({ timestamp, level, message }) => {
                    return `[${timestamp}] [${level}] ${message}`;
                })
            ),
            transports: [
                new winston.transports.Console(),
                new winston.transports.File({ 
                    filename: path.join(__dirname, 'data', 'server.log') 
                })
            ]
        });
    }

    setupMiddleware() {
        this.app.use(cors({
            origin: '*',
            methods: ['GET', 'POST', 'PUT', 'DELETE'],
            allowedHeaders: ['Content-Type', 'X-API-Key']
        }));
        
        this.app.use(bodyParser.json({ limit: '10mb' }));
        this.app.use(bodyParser.urlencoded({ extended: true }));
        
        // Middleware de logging
        this.app.use((req, res, next) => {
            this.logger.info(`${req.method} ${req.path} - ${req.ip}`);
            next();
        });

        // Servir arquivos estáticos
        this.app.use(express.static(path.join(__dirname, 'web')));
    }

    setupRoutes() {
        // Rota principal - Dashboard
        this.app.get('/', (req, res) => {
            const dashboardPath = path.join(__dirname, 'web', 'index.html');
            if (fs.existsSync(dashboardPath)) {
                res.sendFile(dashboardPath);
            } else {
                res.json({ 
                    message: 'Telegram Bridge API v3.0',
                    status: 'running',
                    endpoints: this.getEndpoints()
                });
            }
        });

        // Health Check
        this.app.get('/health', (req, res) => {
            res.json({
                status: 'OK',
                version: '3.0.0',
                timestamp: new Date().toISOString(),
                uptime: process.uptime(),
                memory: process.memoryUsage(),
                telegram: this.telegramService.isConnected
            });
        });

        // Autenticação
        this.app.post('/auth/request', async (req, res) => {
            try {
                this.logger.info('🚀 Iniciando requisição de autenticação...');
                
                const result = await this.telegramService.initialize();
                
                if (result === 'PHONE_CODE_REQUIRED') {
                    res.json({
                        success: true,
                        message: 'Código de verificação enviado para o Telegram',
                        status: await this.telegramService.getStatus()
                    });
                } else if (result === true) {
                    res.json({
                        success: true,
                        message: 'Autenticação concluída com sucesso',
                        status: await this.telegramService.getStatus()
                    });
                } else {
                    res.json({
                        success: false,
                        message: 'Falha ao iniciar autenticação',
                        status: await this.telegramService.getStatus()
                    });
                }
            } catch (error) {
                this.logger.error('Erro na autenticação:', error);
                res.status(500).json({
                    success: false,
                    error: error.message
                });
            }
        });

        this.app.post('/auth/verify', async (req, res) => {
            try {
                const { code } = req.body;
                
                if (!code) {
                    return res.status(400).json({
                        success: false,
                        error: 'Código não fornecido'
                    });
                }

                const result = await this.telegramService.verifyCode(code);
                
                if (result) {
                    res.json({
                        success: true,
                        message: 'Código verificado com sucesso',
                        status: await this.telegramService.getStatus()
                    });
                } else {
                    res.json({
                        success: false,
                        error: 'Falha na verificação do código',
                        status: await this.telegramService.getStatus()
                    });
                }
            } catch (error) {
                this.logger.error('Erro na verificação:', error);
                res.status(500).json({
                    success: false,
                    error: error.message
                });
            }
        });

        this.app.get('/auth/status', async (req, res) => {
            try {
                const status = await this.telegramService.getStatus();
                res.json(status);
            } catch (error) {
                this.logger.error('Erro ao verificar status:', error);
                res.status(500).json({
                    success: false,
                    error: error.message
                });
            }
        });

        // Middleware de autenticação para APIs
        const authenticateApiKey = (req, res, next) => {
            const apiKey = req.headers['x-api-key'];
            if (!apiKey || apiKey !== this.apiKey) {
                return res.status(401).json({ 
                    error: 'Unauthorized',
                    message: 'API Key inválida ou não fornecida'
                });
            }
            next();
        };

        // Endpoints de consulta
        this.app.post('/query', authenticateApiKey, async (req, res) => {
            try {
                const { type, query } = req.body;

                if (!type || !query) {
                    return res.status(400).json({
                        error: 'Campos obrigatórios ausentes',
                        required: ['type', 'query']
                    });
                }

                // Validar tipo de consulta
                const validTypes = ['cpf', 'telefone', 'placa', 'nome', 'email', 'cep', 'cnpj', 'mae'];
                if (!validTypes.includes(type)) {
                    return res.status(400).json({
                        error: 'Tipo de consulta inválido',
                        validTypes
                    });
                }

                // Validar formato do query
                if (!this.validateQuery(type, query)) {
                    return res.status(400).json({
                        error: 'Formato de query inválido para o tipo especificado'
                    });
                }

                // Executar consulta
                const result = await this.executeQuery(type, query);
                
                res.json({
                    success: true,
                    type,
                    query: this.maskSensitiveData(type, query),
                    result,
                    timestamp: new Date().toISOString()
                });

            } catch (error) {
                this.logger.error('Erro na consulta:', error);
                res.status(500).json({
                    success: false,
                    error: error.message,
                    timestamp: new Date().toISOString()
                });
            }
        });

        // Endpoint genérico para consultas
        const validTypes = ['cpf', 'telefone', 'placa', 'nome', 'email', 'cep', 'cnpj', 'mae'];
        validTypes.forEach(type => {
            this.app.post(`/${type}`, authenticateApiKey, async (req, res) => {
                try {
                    const { query } = req.body;
                    
                    if (!query) {
                        return res.status(400).json({
                            error: 'Query não fornecida'
                        });
                    }

                    const result = await this.executeQuery(type, query);
                    
                    res.json({
                        success: true,
                        type,
                        query: this.maskSensitiveData(type, query),
                        result,
                        timestamp: new Date().toISOString()
                    });

                } catch (error) {
                    this.logger.error(`Erro em consulta ${type}:`, error);
                    res.status(500).json({
                        success: false,
                        error: error.message
                    });
                }
            });
        });

        // Configuração
        this.app.get('/config', (req, res) => {
            res.json({
                apiKey: this.apiKey,
                telegram: {
                    apiId: process.env.API_ID ? '***' : null,
                    apiHash: process.env.API_HASH ? '***' : null,
                    phoneNumber: process.env.PHONE_NUMBER ? this.maskPhone(process.env.PHONE_NUMBER) : null,
                    chatId: process.env.CHAT_ID
                }
            });
        });

        // Logs
        this.app.get('/logs', authenticateApiKey, (req, res) => {
            try {
                const logFile = path.join(__dirname, 'data', 'server.log');
                if (fs.existsSync(logFile)) {
                    const logs = fs.readFileSync(logFile, 'utf8');
                    const lines = logs.split('\n').filter(line => line.trim());
                    const recentLines = lines.slice(-100); // Últimas 100 linhas
                    
                    res.json({
                        logs: recentLines,
                        total: lines.length
                    });
                } else {
                    res.json({ logs: [], total: 0 });
                }
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });
    }

    setupErrorHandling() {
        // 404 Handler
        this.app.use((req, res) => {
            res.status(404).json({
                error: 'Endpoint não encontrado',
                path: req.path,
                method: req.method,
                availableEndpoints: this.getEndpoints()
            });
        });

        // Error Handler
        this.app.use((err, req, res, next) => {
            this.logger.error('Erro não tratado:', err);
            res.status(500).json({
                error: 'Erro interno do servidor',
                message: err.message,
                timestamp: new Date().toISOString()
            });
        });
    }

    validateQuery(type, query) {
        const validators = {
            cpf: (cpf) => /^\d{11}$/.test(cpf.replace(/\D/g, '')),
            telefone: (tel) => /^\d{10,11}$/.test(tel.replace(/\D/g, '')),
            placa: (placa) => /^[A-Z]{3}\d{4}$|^[A-Z]{3}\d{1}[A-Z]{1}\d{1}$/i.test(placa.replace(/[^A-Z0-9]/gi, '')),
            nome: (nome) => nome.length >= 3 && nome.length <= 100,
            email: (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email),
            cep: (cep) => /^\d{8}$/.test(cep.replace(/\D/g, '')),
            cnpj: (cnpj) => /^\d{14}$/.test(cnpj.replace(/\D/g, '')),
            mae: (mae) => mae.length >= 3 && mae.length <= 100
        };

        return validators[type] ? validators[type](query) : false;
    }

    maskSensitiveData(type, query) {
        const masks = {
            cpf: (cpf) => cpf.replace(/(\d{3})\d{6}(\d{2})/, '$1******$2'),
            telefone: (tel) => tel.replace(/(\d{2})\d{6,7}(\d{2})/, '$1******$2'),
            email: (email) => email.replace(/(.{2}).*(@.*)/, '$1***$2'),
            cnpj: (cnpj) => cnpj.replace(/(\d{2})\d{10}(\d{2})/, '$1**********$2')
        };

        return masks[type] ? masks[type](query) : query;
    }

    maskPhone(phone) {
        return phone.replace(/(\d{2})\d{6,7}(\d{2})/, '$1******$2');
    }

    async executeQuery(type, query) {
        const methods = {
            cpf: () => this.telegramService.queryCPF(query),
            telefone: () => this.telegramService.queryTelefone(query),
            placa: () => this.telegramService.queryPlaca(query),
            nome: () => this.telegramService.queryNome(query),
            email: () => this.telegramService.queryEmail(query),
            cep: () => this.telegramService.queryCEP(query),
            cnpj: () => this.telegramService.queryCNPJ(query),
            mae: () => this.telegramService.queryMae(query)
        };

        if (methods[type]) {
            return await methods[type]();
        }

        throw new Error(`Tipo de consulta não suportado: ${type}`);
    }

    getEndpoints() {
        return [
            'GET  /',
            'GET  /health',
            'POST /auth/request',
            'POST /auth/verify',
            'GET  /auth/status',
            'POST /query',
            'POST /cpf',
            'POST /telefone',
            'POST /placa',
            'POST /nome',
            'POST /email',
            'POST /cep',
            'POST /cnpj',
            'POST /mae',
            'GET  /config',
            'GET  /logs'
        ];
    }

    async start() {
        try {
            this.logger.info('🚀 Iniciando Telegram Bridge Server v3.0...');
            
            // Garantir diretório de dados
            const dataDir = path.join(__dirname, 'data');
            if (!fs.existsSync(dataDir)) {
                fs.mkdirSync(dataDir, { recursive: true });
            }

            // Inicializar serviço Telegram
            await this.telegramService.initialize();

            // Configurar callback para código de autenticação
            this.telegramService.onCodeRequested = () => {
                this.logger.info('📱 Código de verificação solicitado');
            };

            // Iniciar servidor
            this.server = this.app.listen(this.port, () => {
                this.logger.info(`✅ Servidor iniciado na porta ${this.port}`);
                this.logger.info(`🌐 Dashboard: http://localhost:${this.port}`);
                this.logger.info(`📊 Health: http://localhost:${this.port}/health`);
            });

            // Graceful shutdown
            process.on('SIGTERM', () => this.shutdown());
            process.on('SIGINT', () => this.shutdown());

        } catch (error) {
            this.logger.error('❌ Falha ao iniciar servidor:', error);
            process.exit(1);
        }
    }

    async shutdown() {
        this.logger.info('🔄 Desligando servidor...');
        
        if (this.server) {
            this.server.close();
        }
        
        await this.telegramService.disconnect();
        
        this.logger.info('✅ Servidor desligado com sucesso');
        process.exit(0);
    }
}

// Iniciar servidor
const server = new TelegramBridgeServer();
server.start();

module.exports = TelegramBridgeServer;

const { TelegramClient } = require('telegram');
const { StringSession } = require('telegram/sessions');
const fs = require('fs-extra');
const path = require('path');
const winston = require('winston');

class TelegramService {
    constructor() {
        this.client = null;
        this.isConnected = false;
        this.isAuthenticating = false;
        this.sessionPath = path.join(__dirname, '..', 'data', 'session.txt');
        this.logger = this.setupLogger();
        
        // Configurações do Bot
        this.apiId = process.env.API_ID;
        this.apiHash = process.env.API_HASH;
        this.phoneNumber = process.env.PHONE_NUMBER;
        this.botId = 8219237194;
        this.botUsername = '@consultas0_bot';
        this.chatId = process.env.CHAT_ID || '@consultas0_bot';
        
        this.ensureDataDirectory();
    }

    setupLogger() {
        return winston.createLogger({
            level: 'info',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.colorize(),
                winston.format.simple()
            ),
            transports: [
                new winston.transports.Console(),
                new winston.transports.File({ 
                    filename: path.join(__dirname, '..', 'data', 'telegram.log') 
                })
            ]
        });
    }

    ensureDataDirectory() {
        const dataDir = path.join(__dirname, '..', 'data');
        if (!fs.existsSync(dataDir)) {
            fs.mkdirSync(dataDir, { recursive: true });
        }
    }

    async initialize() {
        try {
            this.logger.info('🚀 Inicializando serviço Telegram com GramJS...');
            
            if (!this.apiId || !this.apiHash || !this.phoneNumber) {
                throw new Error('Credenciais do Telegram não configuradas');
            }

            // Ler sessão existente ou criar nova
            let sessionString = '';
            if (fs.existsSync(this.sessionPath)) {
                sessionString = fs.readFileSync(this.sessionPath, 'utf8');
                this.logger.info('📁 Sessão existente encontrada');
                
                // Tentar reconectar com sessão existente
                try {
                    this.client = new TelegramClient(
                        new StringSession(sessionString),
                        parseInt(this.apiId),
                        this.apiHash,
                        {
                            connectionRetries: 3,
                            retryDelay: 2000,
                            appVersion: 'Telegram Bridge v3.0',
                            langCode: 'pt-br'
                        }
                    );

                    await this.client.connect();
                    
                    // Verificar se está conectado
                    if (this.client.connected) {
                        this.isConnected = true;
                        this.logger.info('✅ Reconectado com sessão existente!');
                        return true;
                    }
                } catch (reconnectError) {
                    this.logger.warn('⚠️ Sessão inválida, criando nova...');
                }
            }

            // Criar novo cliente para autenticação
            this.client = new TelegramClient(
                new StringSession(''),
                parseInt(this.apiId),
                this.apiHash,
                {
                    connectionRetries: 3,
                    retryDelay: 2000,
                    appVersion: 'Telegram Bridge v3.0',
                    langCode: 'pt-br'
                }
            );

            // Apenas conectar, não tentar autenticar ainda
            await this.client.connect();
            
            // Iniciar fluxo de autenticação para solicitar código
            try {
                await this.client.start({
                    phoneNumber: this.phoneNumber,
                    password: async () => null,
                    phoneCode: async () => {
                        // Não retornar código aqui, apenas marcar que precisa
                        this.isAuthenticating = true;
                        throw new Error('PHONE_CODE_REQUIRED');
                    },
                    onError: (err) => {
                        this.logger.error('❌ Erro na autenticação:', err);
                    }
                });
            } catch (authError) {
                if (authError.message === 'PHONE_CODE_REQUIRED') {
                    this.logger.info('📱 Código de verificação necessário');
                    this.isAuthenticating = true;
                    return 'PHONE_CODE_REQUIRED';
                }
                throw authError;
            }
            
        } catch (error) {
            this.logger.error('❌ Falha ao inicializar Telegram:', error.message);
            this.isConnected = false;
            return false;
        }
    }

    async verifyCode(code) {
        try {
            if (!this.client) {
                throw new Error('Cliente não inicializado');
            }

            this.logger.info('🔐 Verificando código...');
            
            // Reiniciar o cliente com o código
            await this.client.start({
                phoneNumber: this.phoneNumber,
                password: async () => null,
                phoneCode: async () => code,
                onError: (err) => {
                    this.logger.error('❌ Erro na verificação:', err);
                }
            });

            // Salvar sessão
            const session = this.client.session.save();
            fs.writeFileSync(this.sessionPath, session);
            
            this.isConnected = true;
            this.isAuthenticating = false;
            this.logger.info('✅ Código verificado com sucesso!');
            
            return true;
        } catch (error) {
            this.logger.error('❌ Falha na verificação do código:', error.message);
            return false;
        }
    }

    async sendCommand(command) {
        try {
            if (!this.isConnected || !this.client) {
                throw new Error('Cliente Telegram não está conectado');
            }

            this.logger.info(`📤 Enviando comando para ${this.botUsername}: ${command}`);
            
            // Encontrar o bot real
            const bot = await this.client.getInputEntity(this.botUsername);
            
            // Enviar mensagem para o bot
            const message = await this.client.sendMessage(bot, { message: command });
            
            // Aguardar resposta real do bot (timeout de 30 segundos)
            const response = await this.waitForResponse(message.id, 30000);
            
            return {
                success: true,
                type: command.split(' ')[0].replace('/', ''),
                query: command.split(' ')[1],
                message: 'Comando enviado com sucesso',
                messageId: message.id,
                timestamp: new Date().toISOString(),
                result: response || 'Aguardando resposta do bot...'
            };

        } catch (error) {
            this.logger.error('❌ Erro ao enviar comando:', error.message);
            return {
                success: false,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }

    async waitForResponse(messageId, timeout = 30000) {
        return new Promise((resolve) => {
            let resolved = false;
            const timeoutId = setTimeout(() => {
                if (!resolved) {
                    resolved = true;
                    this.logger.warn('⏰ Timeout aguardando resposta do bot');
                    resolve(null);
                }
            }, timeout);

            // Adicionar listener para novas mensagens
            const eventHandler = async (event) => {
                if (resolved) return;
                
                if (event.className === 'UpdateNewMessage') {
                    const message = event.message;
                    
                    // Verificar se é resposta do nosso bot
                    if (message.fromId && 
                        (message.fromId.userId === this.botId || 
                         message.fromId.channelId === this.botId)) {
                        
                        if (!resolved) {
                            resolved = true;
                            clearTimeout(timeoutId);
                            this.client.removeEventHandler(eventHandler);
                            this.logger.info(`📥 Resposta recebida: ${message.message}`);
                            resolve(message.message);
                        }
                        return;
                    }
                }
            };

            this.client.addEventHandler(eventHandler, { func: (event) => event.className === 'UpdateNewMessage' });
        });
    }

    maskCPF(cpf) {
        return cpf.replace(/(\d{3})\d{6}(\d{2})/, '$1******$2');
    }

    maskPhone(phone) {
        return phone.replace(/(\d{2})\d{6,7}(\d{2})/, '$1******$2');
    }

    maskCNPJ(cnpj) {
        return cnpj.replace(/(\d{2})\d{10}(\d{2})/, '$1**********$2');
    }

    maskSensitiveData(type, query) {
        const masks = {
            cpf: (cpf) => this.maskCPF(cpf),
            telefone: (tel) => this.maskPhone(tel),
            email: (email) => email.replace(/(.{2}).*(@.*)/, '$1***$2'),
            cnpj: (cnpj) => this.maskCNPJ(cnpj)
        };

        return masks[type] ? masks[type](query) : query;
    }

    async getStatus() {
        return {
            connected: this.isConnected,
            authenticating: this.isAuthenticating,
            phoneNumber: this.phoneNumber,
            chatId: this.chatId,
            hasSession: fs.existsSync(this.sessionPath),
            timestamp: new Date().toISOString()
        };
    }

    async disconnect() {
        try {
            if (this.client && this.isConnected) {
                await this.client.disconnect();
                this.isConnected = false;
                this.client = null;
                this.logger.info('🔌 Cliente Telegram desconectado');
            }
        } catch (error) {
            this.logger.error('Erro ao desconectar:', error.message);
        }
    }

    // Métodos para consultas específicas
    async queryCPF(cpf) {
        return await this.sendCommand(`/cpf ${cpf}`);
    }

    async queryTelefone(telefone) {
        return await this.sendCommand(`/telefone ${telefone}`);
    }

    async queryPlaca(placa) {
        return await this.sendCommand(`/placa ${placa}`);
    }

    async queryNome(nome) {
        return await this.sendCommand(`/nome ${nome}`);
    }

    async queryEmail(email) {
        return await this.sendCommand(`/email ${email}`);
    }

    async queryCEP(cep) {
        return await this.sendCommand(`/cep ${cep}`);
    }

    async queryCNPJ(cnpj) {
        return await this.sendCommand(`/cnpj ${cnpj}`);
    }

    async queryMae(mae) {
        return await this.sendCommand(`/mae ${mae}`);
    }
}

module.exports = TelegramService;

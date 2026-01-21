#!/usr/bin/env python3
"""
Versão Limpa do Serviço Python com Processamento Inteligente
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json
import time
import uuid
from typing import Dict, Optional, List, Any
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Clean Telegram Query Bridge", version="3.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração do Telegram
try:
    API_ID = int(os.getenv('API_ID', '0'))
    API_HASH = os.getenv('API_HASH', '')
    CHAT_ID = int(os.getenv('CHAT_ID', '0'))
    PHONE_NUMBER = os.getenv('PHONE_NUMBER', '')
except (ValueError, TypeError):
    print("AVISO: Configurações do Telegram inválidas ou ausentes.")
    API_ID = 0
    API_HASH = ""
    CHAT_ID = 0
    PHONE_NUMBER = ""

# Variáveis globais
client = None
telegram_connected = False
connection_error = None
pending_requests: Dict[str, dict] = {}
button_responses: Dict[str, dict] = {}

# Padrões de scraping
SCRAPING_PATTERNS = {
    'cpf': {
        'nome': r'👤\s*Nome:\s*([^\n]+)',
        'cpf': r'🆔\s*CPF:\s*([^\n]+)',
        'nascimento': r'📅\s*Nasc:\s*([^\n]+)',
        'mae': r'👩\s*Mãe:\s*([^\n]+)',
        'telefones': r'📱\s*(\d+)\s*Telefones?',
        'emails': r'📧\s*(\d+)\s*Emails?',
        'enderecos': r'📍\s*(\d+)\s*Endereços?',
        'vazadas': r'🔐\s*(\d+)\s*Credenciais Vazadas?',
        'veiculos': r'🚗\s*(\d+)\s*Veículos?',
        'parentes': r'👨‍👩‍👧\s*(\d+)\s*Parentes?'
    },
    'telefone': {
        'numero': r'📱\s*Telefone:\s*([^\n]+)',
        'operadora': r'📡\s*Operadora:\s*([^\n]+)',
        'tipo': r'📋\s*Tipo:\s*([^\n]+)',
        'status': r'✅\s*Status:\s*([^\n]+)'
    },
    'placa': {
        'placa': r'🚗\s*Placa:\s*([^\n]+)',
        'modelo': r'🚙\s*Modelo:\s*([^\n]+)',
        'marca': r'🏭\s*Marca:\s*([^\n]+)',
        'cor': r'🎨\s*Cor:\s*([^\n]+)',
        'ano': r'📅\s*Ano:\s*([^\n]+)',
        'situacao': r'✅\s*Situação:\s*([^\n]+)'
    }
}

class CommandRequest(BaseModel):
    command: str
    timeout: int = 30
    auto_click_buttons: bool = True

class CommandResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None

def scrape_data(text: str, command_type: str) -> Dict[str, Any]:
    """Extrai dados estruturados do texto"""
    if command_type not in SCRAPING_PATTERNS:
        return {
            'raw_text': text,
            'command_type': command_type,
            'scraped_data': {}
        }
    
    patterns = SCRAPING_PATTERNS[command_type]
    scraped_data = {}
    
    try:
        import re
        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if field in ['telefones', 'emails', 'enderecos', 'vazadas', 'veiculos', 'parentes']:
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                scraped_data[field] = value
        
        return {
            'raw_text': text,
            'command_type': command_type,
            'scraped_data': scraped_data,
            'success': True
        }
        
    except Exception as e:
        return {
            'raw_text': text,
            'command_type': command_type,
            'scraped_data': {},
            'error': str(e),
            'success': False
        }

def get_command_type(command: str) -> str:
    """Identifica o tipo de comando"""
    if command.startswith('/cpf'):
        return 'cpf'
    elif command.startswith('/telefone'):
        return 'telefone'
    elif command.startswith('/placa'):
        return 'placa'
    elif command.startswith('/nome'):
        return 'nome'
    elif command.startswith('/email'):
        return 'email'
    elif command.startswith('/cep'):
        return 'cep'
    elif command.startswith('/cnpj'):
        return 'cnpj'
    else:
        return 'unknown'

@app.on_event("startup")
async def startup_event():
    """Inicia o cliente do Telegram"""
    global telegram_connected, connection_error, client
    
    if not API_ID or not API_HASH:
        print("ERRO CRÍTICO: API_ID ou API_HASH não configurados.")
        connection_error = "API_ID ou API_HASH não configurados"
        return

    try:
        from telethon import TelegramClient
        from telethon.events import NewMessage, CallbackQuery
        
        os.makedirs('session', exist_ok=True)
        client = TelegramClient('session/clean_session', API_ID, API_HASH)
        
        print(f"Iniciando cliente Telegram para: {PHONE_NUMBER}...")
        await client.start(phone=PHONE_NUMBER)
        telegram_connected = True
        print("✅ Telegram client started successfully!")
        
        @client.on(NewMessage(chats=CHAT_ID))
        async def handle_new_message(event):
            """Lida com novas mensagens"""
            if event.message.reply_to_msg_id:
                for req_id, req_data in pending_requests.items():
                    if not req_data['completed']:
                        req_data['response'] = event.message.text
                        req_data['completed'] = True
                        break
            else:
                for req_id, req_data in pending_requests.items():
                    if not req_data['completed']:
                        req_data['response'] = event.message.text
                        req_data['completed'] = True
                        break

        @client.on(CallbackQuery)
        async def handle_button_click(event):
            """Lida com cliques em botões"""
            try:
                for req_id, req_data in pending_requests.items():
                    if not req_data['completed']:
                        button_responses[req_id] = {
                            'button_text': event.data,
                            'message': event.message.message,
                            'timestamp': time.time()
                        }
                        
                        if "base_completa" in str(event.data):
                            await event.answer("✅ Solicitando base completa...")
                            await asyncio.sleep(2)
                        elif "ver_relatorio" in str(event.data) or "relatorio_completo" in str(event.data):
                            await event.answer("✅ Abrindo relatório completo...")
                        
                        req_data['response'] = f"BOTÃO CLICADO: {event.data}\\nMENSAGEM: {event.message.message}"
                        req_data['completed'] = True
                        break
            except Exception as e:
                print(f"Erro ao processar clique: {e}")
        
    except Exception as e:
        connection_error = str(e)
        print(f"❌ Erro ao iniciar cliente Telegram: {e}")

@app.post("/send-command", response_model=CommandResponse)
async def send_command(request: CommandRequest):
    """Envia comando com processamento inteligente"""
    start_time = time.time()
    
    if not client:
        raise HTTPException(status_code=503, detail="Cliente Telegram não está disponível")
    
    if not telegram_connected:
        raise HTTPException(status_code=503, detail=f"Cliente não conectado: {connection_error}")
    
    request_id = str(uuid.uuid4())
    command_type = get_command_type(request.command)
    
    try:
        pending_requests[request_id] = {
            'command': request.command,
            'timestamp': time.time(),
            'response': None,
            'completed': False
        }
        
        # Envia o comando
        message = await client.send_message(CHAT_ID, request.command)
        await asyncio.sleep(3)
        
        # Procura por botões e clica automaticamente
        buttons_found = []
        if request.auto_click_buttons:
            async for msg in client.iter_messages(CHAT_ID, limit=5):
                if msg.reply_to_msg_id == message.id and msg.buttons:
                    for row in msg.buttons:
                        for btn in row:
                            buttons_found.append(btn.text)
                            if "completa" in btn.text.lower():
                                print(f"🔘 Clicando em: {btn.text}")
                                await btn.click()
                                await asyncio.sleep(3)
                                
                                # Procura por botão de relatório completo
                                async for rel_msg in client.iter_messages(CHAT_ID, limit=3):
                                    if rel_msg.buttons:
                                        for rel_row in rel_msg.buttons:
                                            for rel_btn in rel_row:
                                                if "relatório" in rel_btn.text.lower() or "relatorio" in rel_btn.text.lower():
                                                    print(f"🔘 Clicando em: {rel_btn.text}")
                                                    await rel_btn.click()
                                                    await asyncio.sleep(3)
                                                    break
                                        break
                                break
                    break
        
        # Espera pela resposta final
        timeout = request.timeout
        start_wait = time.time()
        
        while time.time() - start_wait < timeout:
            if pending_requests[request_id]['completed']:
                response_data = pending_requests[request_id]['response']
                del pending_requests[request_id]
                
                # Faz scraping dos dados
                scraped_data = scrape_data(response_data, command_type)
                
                processing_time = time.time() - start_time
                
                return CommandResponse(
                    success=True,
                    data={
                        'response_text': response_data,
                        'command_type': command_type,
                        'scraped_data': scraped_data,
                        'buttons_found': buttons_found,
                        'processing_time': processing_time
                    },
                    processing_time=processing_time
                )
            
            await asyncio.sleep(0.5)
        
        # Timeout
        del pending_requests[request_id]
        raise HTTPException(status_code=504, detail="Timeout ao aguardar resposta")
        
    except Exception as e:
        if request_id in pending_requests:
            del pending_requests[request_id]
        processing_time = time.time() - start_time
        return CommandResponse(
            success=False,
            error=str(e),
            processing_time=processing_time
        )

@app.post("/test-all-commands")
async def test_all_commands():
    """Testa todos os comandos conhecidos"""
    test_commands = [
        "/cpf 123.456.789-00",
        "/telefone (11) 98765-4321",
        "/placa ABC1234",
        "/nome João Silva",
        "/email joao@email.com",
        "/cep 01310-100",
        "/cnpj 12.345.678/0001-90"
    ]
    
    results = {}
    for command in test_commands:
        try:
            request = CommandRequest(command=command, timeout=15, auto_click_buttons=True)
            result = await send_command(request)
            results[command] = result.dict()
        except Exception as e:
            results[command] = {"success": False, "error": str(e)}
        
        await asyncio.sleep(2)  # Pausa entre comandos
    
    return {
        "success": True,
        "message": f"Testados {len(test_commands)} comandos",
        "results": results,
        "summary": {
            "total": len(test_commands),
            "successful": sum(1 for r in results.values() if r.get("success", False)),
            "failed": sum(1 for r in results.values() if not r.get("success", False))
        }
    }

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "OK",
        "version": "3.1.0",
        "telegram_connected": telegram_connected,
        "pending_requests": len(pending_requests),
        "button_responses": len(button_responses),
        "features": {
            "smart_scraping": True,
            "auto_button_click": True,
            "multiple_commands": True,
            "structured_output": True
        }
    }

@app.get("/")
async def root():
    """Informações do serviço"""
    return {
        "service": "Clean Telegram Query Bridge v3.1.0",
        "description": "Sistema limpo e otimizado para processamento de comandos Telegram",
        "features": [
            "🧠 Processamento Inteligente",
            "🔘 Cliques Automáticos em Botões",
            "📊 Extração Estruturada de Dados",
            "🚀 Testes em Lote",
            "📋 Saída JSON Organizada"
        ],
        "endpoints": {
            "send_command": "POST /send-command",
            "test_all_commands": "POST /test-all-commands",
            "health": "GET /health"
        },
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

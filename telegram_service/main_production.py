#!/usr/bin/env python3
"""
Versão de Produção do Serviço Python com Tratamento de Autenticação
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from telethon import TelegramClient
from telethon.events import NewMessage, CallbackQuery
import os
from dotenv import load_dotenv
import uuid
from typing import Dict, Optional
import time
import re
import json

load_dotenv()

app = FastAPI()

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

# Mapeamento de comandos para o texto do botão do menu
COMMAND_TO_BUTTON = {
    'cpf': '🆔 CPF',
    'telefone': '📱 Telefone',
    'nome': '👤 Nome',
    'email': '📧 Email',
    'cep': '📍 CEP',
    'foto': '📸 Foto',
    'cnpj': '🏢 CNPJ',
    'titulo': '🗳️ Título',
    'mae': '👩‍👧‍👦 Mãe',
    'vip': '💎 VIP',
    'stats': '📊 Stats',
    'ajuda': '❓ Ajuda',
}

# Dicionário para armazenar requisições pendentes
pending_requests: Dict[str, dict] = {}

def scrape_relatorio_completo(text):
    """Extrai dados estruturados do relatório completo"""
    dados = {
        "nome": None,
        "cpf": None,
        "data_nascimento": None,
        "mae": None,
        "telefones": [],
        "emails": [],
        "enderecos": [],
        "credenciais_vazadas": 0,
        "veiculos": 0,
        "parentes": [],
        "resultado_texto": text
    }
    
    try:
        # Extrair nome
        nome_match = re.search(r'👤\s*Nome:\s*([^\n]+)', text)
        if nome_match:
            dados["nome"] = nome_match.group(1).strip()
        
        # Extrair CPF
        cpf_match = re.search(r'🆔\s*CPF:\s*([^\n]+)', text)
        if cpf_match:
            dados["cpf"] = cpf_match.group(1).strip()
        
        # Extrair data de nascimento
        nasc_match = re.search(r'📅\s*Nasc:\s*([^\n]+)', text)
        if nasc_match:
            dados["data_nascimento"] = nasc_match.group(1).strip()
        
        # Extrair nome da mãe
        mae_match = re.search(r'👩\s*Mãe:\s*([^\n]+)', text)
        if mae_match:
            dados["mae"] = mae_match.group(1).strip()
        
        # Extrair telefones
        telefone_match = re.search(r'📱\s*(\d+)\s*Telefones?', text)
        if telefone_match:
            dados["telefones"] = [f"Telefone {i+1}" for i in range(int(telefone_match.group(1)))]
        
        # Extrair emails
        email_match = re.search(r'📧\s*(\d+)\s*Emails?', text)
        if email_match:
            dados["emails"] = [f"Email {i+1}" for i in range(int(email_match.group(1)))]
        
        # Extrair endereços
        endereco_match = re.search(r'📍\s*(\d+)\s*Endereços?', text)
        if endereco_match:
            dados["enderecos"] = [f"Endereço {i+1}" for i in range(int(endereco_match.group(1)))]
        
        # Extrair credenciais vazadas
        vazadas_match = re.search(r'🔐\s*(\d+)\s*Credenciais Vazadas?', text)
        if vazadas_match:
            dados["credenciais_vazadas"] = int(vazadas_match.group(1))
        
        # Extrair veículos
        veiculos_match = re.search(r'🚗\s*(\d+)\s*Veículos?', text)
        if veiculos_match:
            dados["veiculos"] = int(veiculos_match.group(1))
        
        # Extrair parentes
        parentes_match = re.search(r'👨‍👩‍👧\s*(\d+)\s*Parentes?', text)
        if parentes_match:
            dados["parentes"] = [f"Parente {i+1}" for i in range(int(parentes_match.group(1)))]
        
    except Exception as e:
        print(f"Erro ao fazer scraping: {e}")
    
    return dados

# Dicionário para armazenar respostas de botões
button_responses: Dict[str, dict] = {}

# Cliente do Telegram com tratamento de erros
try:
    # Garante que o diretório session existe
    os.makedirs('session', exist_ok=True)
    client = TelegramClient('session/session_name', API_ID, API_HASH)
except Exception as e:
    print(f"ERRO ao inicializar cliente Telegram: {e}")
    connection_error = str(e)

class CommandRequest(BaseModel):
    command: str
    timeout: int = 30

class CommandResponse(BaseModel):
    success: bool
    data: Optional[str] = None
    error: Optional[str] = None

class AuthStatusResponse(BaseModel):
    connected: bool
    needs_code: bool = False
    error: Optional[str] = None
    message: str

@app.on_event("startup")
async def startup_event():
    """Inicia o cliente do Telegram quando o servidor sobe"""
    global telegram_connected, connection_error
    
    if not client:
        print("ERRO CRÍTICO: Cliente Telegram não foi inicializado.")
        return
        
    if not API_ID or not API_HASH:
        print("ERRO CRÍTICO: API_ID ou API_HASH não configurados.")
        connection_error = "API_ID ou API_HASH não configurados"
        return

    print(f"Iniciando cliente Telegram para: {PHONE_NUMBER}...")
    try:
        await client.start(phone=PHONE_NUMBER)
        telegram_connected = True
        print("✅ Telegram client started successfully!")
        
        # Registra o handler de mensagens após conexão
        @client.on(NewMessage(chats=CHAT_ID))
        async def handle_new_message(event):
            """Lida com novas mensagens no grupo"""
            # A lógica de tratamento de resposta foi movida para a rota send_command para evitar concorrência
            pass

        @client.on(CallbackQuery)
        async def handle_button_click(event):
            """Lida com cliques em botões inline"""
            # Este handler não é adequado para um user-bot que automatiza outro bot. A lógica foi centralizada.
            pass
        
    except Exception as e:
        connection_error = str(e)
        print(f"❌ Erro ao iniciar cliente Telegram: {e}")
        print("Verifique suas credenciais e conexão com a internet.")

@app.on_event("shutdown")
async def shutdown_event():
    """Finaliza o cliente do Telegram quando o servidor desliga"""
    try:
        if client and telegram_connected:
            await client.disconnect()
            print("Telegram client disconnected!")
    except Exception as e:
        print(f"Erro ao desconectar cliente Telegram: {e}")

@app.post("/send-command", response_model=CommandResponse)
async def send_command(request: CommandRequest):
    """Envia um comando para o Telegram e espera a resposta"""
    if not client:
        raise HTTPException(status_code=503, detail="Cliente Telegram não está disponível")
    
    if not telegram_connected:
        raise HTTPException(status_code=503, detail=f"Cliente Telegram não está conectado: {connection_error or 'Desconhecido'}")

    try:
        # 1. Parse do comando
        parts = request.command.strip().split(maxsplit=1)
        command_type = parts[0].lower().replace('/', '')
        query_value = parts[1] if len(parts) > 1 else ''

        if not query_value:
            raise HTTPException(status_code=400, detail="O valor da consulta não foi fornecido.")

        if command_type not in COMMAND_TO_BUTTON:
            raise HTTPException(status_code=400, detail=f"Comando '{command_type}' não é suportado.")

        button_text_to_click = COMMAND_TO_BUTTON[command_type]

        # 2. Encontrar o menu e clicar no botão correspondente
        print(f"▶️  Iniciando fluxo para comando: {command_type}")
        menu_message_found = False
        async for message in client.iter_messages(CHAT_ID, limit=20):
            if message.buttons:
                for row in message.buttons:
                    for button in row:
                        if button.text == button_text_to_click:
                            print(f"🗺️  Menu encontrado. Clicando em '{button.text}'...")
                            await button.click()
                            menu_message_found = True
                            break
                    if menu_message_found:
                        break
            if menu_message_found:
                break
        
        if not menu_message_found:
            raise HTTPException(status_code=500, detail=f"Não foi possível encontrar o botão '{button_text_to_click}' no menu do chat.")

        # 3. Aguardar o bot pedir o valor e enviá-lo
        await asyncio.sleep(2)  # Espera por "Por favor, envie o CPF" ou similar
        print(f"➡️  Enviando valor da consulta: '{query_value}'")
        query_message = await client.send_message(CHAT_ID, query_value)

        # 4. Aguardar resposta com botões "Simples" / "Completa"
        await asyncio.sleep(5)  # Espera o processamento
        response_with_buttons = None
        async for msg in client.iter_messages(CHAT_ID, limit=5):
            if msg.reply_to_msg_id == query_message.id and msg.buttons:
                response_with_buttons = msg
                break
        
        if not response_with_buttons:
            raise HTTPException(status_code=504, detail="Não foi recebida uma resposta com botões 'Completa'/'Simples'.")

        # 5. Clicar em "Completa"
        completa_button_clicked = False
        for row in response_with_buttons.buttons:
            for btn in row:
                if "completa" in btn.text.lower():
                    print(f"🔘 Clicando em '{btn.text}'...")
                    await btn.click()
                    completa_button_clicked = True
                    break
            if completa_button_clicked:
                break
        
        if not completa_button_clicked:
            raise HTTPException(status_code=500, detail="Botão 'Completa' não encontrado na resposta.")

        # 6. Aguardar a mensagem com o botão de relatório final
        await asyncio.sleep(3)
        report_button_message = None
        async for msg in client.iter_messages(CHAT_ID, limit=5):
            if msg.id > response_with_buttons.id and msg.buttons:
                report_button_message = msg
                break
        
        if not report_button_message:
             raise HTTPException(status_code=504, detail="Não foi recebida a mensagem com o botão de relatório final.")

        # 7. Clicar no botão de relatório final
        report_button_clicked = False
        for row in report_button_message.buttons:
            for btn in row:
                if any(keyword in btn.text.lower() for keyword in ["relatório", "detalhes", "histórico", "endereços"]):
                    print(f"🔘 Clicando em '{btn.text}' para obter o relatório final...")
                    await btn.click()
                    report_button_clicked = True
                    break
            if report_button_clicked:
                break
        
        if not report_button_clicked:
            raise HTTPException(status_code=500, detail="Botão de relatório final não encontrado.")

        # 8. Aguardar a resposta final em texto
        await asyncio.sleep(8)
        final_response_text = None
        async for msg in client.iter_messages(CHAT_ID, limit=5):
            if msg.id > report_button_message.id and not msg.buttons and ("RESULTADO DA CONSULTA" in msg.text or "Nome:" in msg.text):
                final_response_text = msg.text
                break
        
        if not final_response_text:
            raise HTTPException(status_code=504, detail="Timeout: Resposta final do Telegram não recebida.")

        print("✅ Resposta final recebida e processada.")
        structured_data = scrape_relatorio_completo(final_response_text)
        return CommandResponse(success=True, data=json.dumps(structured_data, indent=2, ensure_ascii=False))

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth-status", response_model=AuthStatusResponse)
async def auth_status():
    """Verifica o status da autenticação Telegram"""
    return AuthStatusResponse(
        connected=telegram_connected,
        needs_code=not telegram_connected and client is not None,
        error=connection_error,
        message="Conectado ao Telegram" if telegram_connected else 
               ("Aguardando código de verificação" if not telegram_connected and client is not None else 
                f"Erro de conexão: {connection_error}" if connection_error else "Cliente não inicializado")
    )

@app.get("/health")
async def health_check():
    """Verifica se o serviço está saudável"""
    try:
        # Limpa requisições pendentes antigas (mais de 5 minutos)
        current_time = time.time()
        expired_requests = [
            req_id for req_id, req_data in pending_requests.items()
            if current_time - req_data['timestamp'] > 300
        ]
        for req_id in expired_requests:
            del pending_requests[req_id]
        
        # Limpa respostas de botões antigas
        expired_buttons = [
            req_id for req_id, btn_data in button_responses.items()
            if current_time - btn_data['timestamp'] > 300
        ]
        for req_id in expired_buttons:
            del button_responses[req_id]
        
        return {
            "status": "OK",
            "mode": "production",
            "telegram_connected": telegram_connected,
            "telegram_client_available": client is not None,
            "pending_requests": len(pending_requests),
            "button_responses": len(button_responses),
            "api_id_configured": bool(API_ID),
            "api_hash_configured": bool(API_HASH),
            "chat_id_configured": bool(CHAT_ID),
            "phone_configured": bool(PHONE_NUMBER),
            "connection_error": connection_error,
            "features": {
                "real_telegram": True,
                "auth_status_check": True,
                "button_interaction": True,
                "all_endpoints": True
            }
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "telegram_connected": False,
            "telegram_client_available": False,
            "pending_requests": len(pending_requests)
        }

@app.post("/auth-status", response_model=AuthStatusResponse)
async def auth_status():
        """Verifica o status da autenticação Telegram"""
        return AuthStatusResponse(
            connected=telegram_connected,
            needs_code=not telegram_connected and client is not None,
            error=connection_error,
            message="Conectado ao Telegram" if telegram_connected else 
                   ("Aguardando código de verificação" if not telegram_connected and client is not None else 
                    f"Erro de conexão: {connection_error}" if connection_error else "Cliente não inicializado")
        )

    @app.get("/health")
async def health_check():
        """Verifica se o serviço está saudável"""
        try:
            # Limpa requisições pendentes antigas (mais de 5 minutos)
            current_time = time.time()
            expired_requests = [
                req_id for req_id, req_data in pending_requests.items()
                if current_time - req_data['timestamp'] > 300
            ]
            for req_id in expired_requests:
                del pending_requests[req_id]
            
            # Limpa respostas de botões antigas
            expired_buttons = [
                req_id for req_id, btn_data in button_responses.items()
                if current_time - btn_data['timestamp'] > 300
            ]
            for req_id in expired_buttons:
                del button_responses[req_id]
            
            return {
                "status": "OK",
                "mode": "production",
                "telegram_connected": telegram_connected,
                "telegram_client_available": client is not None,
                "pending_requests": len(pending_requests),
                "button_responses": len(button_responses),
                "api_id_configured": bool(API_ID),
                "api_hash_configured": bool(API_HASH),
                "chat_id_configured": bool(CHAT_ID),
                "phone_configured": bool(PHONE_NUMBER),
                "connection_error": connection_error,
                "features": {
                    "real_telegram": True,
                    "auth_status_check": True,
                    "button_interaction": True,
                    "all_endpoints": True
                }
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "error": str(e),
                "telegram_connected": False,
                "telegram_client_available": False,
                "pending_requests": len(pending_requests)
            }

    @app.get("/")
    async def root():
        """Rota raiz com informações do serviço"""
        return {
                "service": "Telegram Query Bridge - Python Service (Production)",
                "mode": "production",
                "version": "2.1.0",
                "telegram_connected": telegram_connected,
                "endpoints": {
                    "health": "/health",
                    "send_command": "/send-command (POST)",
                    "auth_status": "/auth-status (GET)",
                    "button_interaction": "✅ Botões inline suportados",
                    "process_relatorio_completo": "/process-relatorio-completo (POST)"
                },
                "status": "running"
            }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

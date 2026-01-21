#!/usr/bin/env python3
"""
Versão de Desenvolvimento do Serviço Python
Modo mock para testes sem autenticação Telegram
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import os
from dotenv import load_dotenv
import uuid
from typing import Dict, Optional
import time
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

# Dicionário para armazenar requisições pendentes
pending_requests: Dict[str, dict] = {}

# Modo de desenvolvimento
DEV_MODE = os.getenv('DEV_MODE', 'true').lower() == 'true'

class CommandRequest(BaseModel):
    command: str
    timeout: int = 30

class CommandResponse(BaseModel):
    success: bool
    data: Optional[str] = None
    error: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Inicia o cliente do Telegram quando o servidor sobe"""
    if DEV_MODE:
        print("🔧 MODO DESENVOLVIMENTO ATIVADO")
        print("✅ Serviço Python iniciado em modo mock (sem Telegram)")
        print("📝 Comandos serão simulados com respostas de teste")
        return
    
    # Código original do Telegram (comentado em modo dev)
    print("MODO PRODUÇÃO: Requer autenticação Telegram")
    print("Para usar modo desenvolvimento, defina DEV_MODE=true no .env")

@app.on_event("shutdown")
async def shutdown_event():
    """Finaliza o cliente do Telegram quando o servidor desliga"""
    print("Python service shutting down...")

@app.post("/send-command", response_model=CommandResponse)
async def send_command(request: CommandRequest):
    """Envia um comando para o Telegram e espera a resposta"""
    
    if DEV_MODE:
        # Modo desenvolvimento - simula respostas
        await asyncio.sleep(1)  # Simula tempo de processamento
        
        command = request.command.lower()
        
        # Simula diferentes tipos de respostas
        if '/cpf' in command:
            mock_response = {
                "status": "found",
                "data": {
                    "cpf": command.split()[-1] if len(command.split()) > 1 else "123.456.789-00",
                    "nome": "JOÃO DA SILVA",
                    "situacao": "REGULAR",
                    "data_nascimento": "15/03/1985"
                }
            }
        elif '/telefone' in command:
            mock_response = {
                "status": "found",
                "data": {
                    "telefone": command.split()[-1] if len(command.split()) > 1 else "(11) 98765-4321",
                    "operadora": "VIVO",
                    "tipo": "MOVEL"
                }
            }
        elif '/placa' in command:
            mock_response = {
                "status": "found",
                "data": {
                    "placa": command.split()[-1] if len(command.split()) > 1 else "ABC1234",
                    "marca": "VOLKSWAGEN",
                    "modelo": "GOL",
                    "cor": "BRANCO",
                    "ano": "2020"
                }
            }
        elif '/nome' in command:
            mock_response = {
                "status": "found",
                "data": {
                    "nome": command.split()[-1] if len(command.split()) > 1 else "JOÃO DA SILVA",
                    "cpf": "123.456.789-00",
                    "idade": "38 anos"
                }
            }
        else:
            mock_response = {
                "status": "error",
                "message": f"Comando não reconhecido: {command}",
                "available_commands": ["/cpf", "/telefone", "/placa", "/nome"]
            }
        
        return CommandResponse(success=True, data=json.dumps(mock_response, indent=2))
    
    # Código original do Telegram (não executado em modo dev)
    raise HTTPException(status_code=503, detail="Modo Telegram desativado. Use DEV_MODE=false para ativar")

@app.post("/handle-button")
async def handle_button(request: dict):
    """Lida com cliques em botões (modo mock)"""
    if DEV_MODE:
        await asyncio.sleep(0.5)
        return CommandResponse(
            success=True,
            data=json.dumps({
                "button_clicked": request.get('button_text', 'unknown'),
                "original_command": request.get('original_command', 'unknown'),
                "status": "processed"
            })
        )
    
    raise HTTPException(status_code=503, detail="Modo Telegram desativado")

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
        
        return {
            "status": "OK",
            "mode": "development" if DEV_MODE else "production",
            "telegram_connected": DEV_MODE,  # Em modo dev, simula como conectado
            "telegram_client_available": DEV_MODE,
            "pending_requests": len(pending_requests),
            "api_id_configured": bool(API_ID),
            "api_hash_configured": bool(API_HASH),
            "chat_id_configured": bool(CHAT_ID),
            "phone_configured": bool(PHONE_NUMBER),
            "features": {
                "mock_responses": DEV_MODE,
                "button_handling": DEV_MODE,
                "all_endpoints": DEV_MODE
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
        "service": "Telegram Query Bridge - Python Service",
        "mode": "development" if DEV_MODE else "production",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "send_command": "/send-command (POST)",
            "handle_button": "/handle-button (POST)"
        },
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

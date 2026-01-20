from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from telethon import TelegramClient
from telethon.events import NewMessage
import os
from dotenv import load_dotenv
import uuid
from typing import Dict, Optional
import time

load_dotenv()

app = FastAPI()

# Configuração do Telegram
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
CHAT_ID = int(os.getenv('CHAT_ID'))
PHONE_NUMBER = os.getenv('PHONE_NUMBER')

# Dicionário para armazenar requisições pendentes
pending_requests: Dict[str, dict] = {}

# Cliente do Telegram
client = TelegramClient('telegram_service/session/session_name', API_ID, API_HASH)

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
    await client.start(phone=PHONE_NUMBER)
    print("Telegram client started successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    """Finaliza o cliente do Telegram quando o servidor desliga"""
    await client.disconnect()
    print("Telegram client disconnected!")

@app.post("/send-command", response_model=CommandResponse)
async def send_command(request: CommandRequest):
    """Envia um comando para o Telegram e espera a resposta"""
    request_id = str(uuid.uuid4())
    
    try:
        # Adiciona à lista de requisições pendentes
        pending_requests[request_id] = {
            'command': request.command,
            'timestamp': time.time(),
            'response': None,
            'completed': False
        }
        
        # Envia o comando para o grupo
        message = await client.send_message(CHAT_ID, request.command)
        
        # Espera pela resposta
        timeout = request.timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if pending_requests[request_id]['completed']:
                response_data = pending_requests[request_id]['response']
                del pending_requests[request_id]
                return CommandResponse(success=True, data=response_data)
            
            await asyncio.sleep(0.5)
        
        # Timeout
        del pending_requests[request_id]
        raise HTTPException(status_code=504, detail="Telegram response timeout")
        
    except Exception as e:
        if request_id in pending_requests:
            del pending_requests[request_id]
        raise HTTPException(status_code=500, detail=str(e))

@client.on(NewMessage(chats=CHAT_ID))
async def handle_new_message(event):
    """Lida com novas mensagens no grupo"""
    # Verifica se é uma resposta a algum comando pendente
    if event.message.reply_to_msg_id:
        # Procura pela requisição correspondente
        for req_id, req_data in pending_requests.items():
            if not req_data['completed']:
                # Marca como completada e armazena a resposta
                req_data['response'] = event.message.text
                req_data['completed'] = True
                break
    else:
        # Se não for reply, assume que é a primeira resposta disponível
        for req_id, req_data in pending_requests.items():
            if not req_data['completed']:
                req_data['response'] = event.message.text
                req_data['completed'] = True
                break

@app.get("/health")
async def health_check():
    """Verifica se o serviço está saudável"""
    return {
        "status": "OK",
        "telegram_connected": client.is_connected(),
        "pending_requests": len(pending_requests)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import time
import uuid
from typing import Dict, Optional
import random

app = FastAPI()

# Dicionário para armazenar requisições pendentes
pending_requests: Dict[str, dict] = {}

class CommandRequest(BaseModel):
    command: str
    timeout: int = 30

class ButtonRequest(BaseModel):
    button_text: str
    original_command: str
    timeout: int = 30

class CommandResponse(BaseModel):
    success: bool
    data: Optional[str] = None
    error: Optional[str] = None

# Simulações de respostas para diferentes comandos
def simulate_response(command: str) -> str:
    """Simula respostas do Telegram baseado no comando"""
    if '/cpf' in command:
        return f"✅ CPF encontrado: {command.split()[-1]}\nNome: João Silva\nStatus: Regular\nData Nasc: 15/03/1985\n\nSelecione uma opção abaixo:\n[Ver no Privado] [Ver Resumo]\n[Baixar TXT] [Fechar]"
    elif '/telefone' in command:
        return f"📱 Telefone: {command.split()[-1]}\nOperadora: Vivo\nTipo: Móvel\nRegistro: Ativo\n\nSelecione uma opção abaixo:\n[Ver no Privado] [Ver Resumo]\n[Baixar TXT] [Fechar]"
    elif '/placa' in command:
        return f"🚗 Placa: {command.split()[-1].upper()}\nModelo: VW Gol 2020\nCor: Branco\nSituação: Regular\n\nSelecione uma opção abaixo:\n[Ver no Privado] [Ver Resumo]\n[Baixar TXT] [Fechar]"
    elif '/nome' in command:
        return f"👤 Nome: {command.split()[-1]}\nCPF: 123.456.789-00\nIdade: 38 anos\nCidade: São Paulo\n\nSelecione uma opção abaixo:\n[Ver no Privado] [Ver Resumo]\n[Baixar TXT] [Fechar]"
    elif '/email' in command:
        return f"📧 Email: {command.split()[-1]}\nValidação: Válido\nProvedor: Gmail\nRisco: Baixo\n\nSelecione uma opção abaixo:\n[Ver no Privado] [Ver Resumo]\n[Baixar TXT] [Fechar]"
    elif '/cep' in command:
        return f"📍 CEP: {command.split()[-1]}\nEndereço: Rua das Flores, 123\nBairro: Centro\nCidade: São Paulo/SP\n\nSelecione uma opção abaixo:\n[Ver no Privado] [Ver Resumo]\n[Baixar TXT] [Fechar]"
    elif '/cnpj' in command:
        return f"🏢 CNPJ: {command.split()[-1]}\nRazão Social: Empresa ABC Ltda\nSituação: Ativa\nCapital: R$ 100.000,00\n\nSelecione uma opção abaixo:\n[Ver no Privado] [Ver Resumo]\n[Baixar TXT] [Fechar]"
    elif '/foto' in command:
        return f"📸 Foto localizada para: {command.split()[-1]}\nQualidade: Alta\nFonte: Banco de Dados\nData: 15/01/2026\n\nSelecione uma opção abaixo:\n[Ver no Privado] [Ver Resumo]\n[Baixar TXT] [Fechar]"
    elif '/titulo' in command:
        return f"📋 Título: {command.split()[-1]}\nSituação: Regular\nZona: 015\nSeção: 023\n\nSelecione uma opção abaixo:\n[Ver no Privado] [Ver Resumo]\n[Baixar TXT] [Fechar]"
    elif '/mae' in command:
        return f"👩 Mãe localizada: {command.split()[-1]}\nFilhos: 2\nIdade: 65 anos\nCPF: 987.654.321-00\n\nSelecione uma opção abaixo:\n[Ver no Privado] [Ver Resumo]\n[Baixar TXT] [Fechar]"
    else:
        return f"❓ Comando não reconhecido: {command}"

def simulate_button_response(button_text: str, original_command: str) -> str:
    """Simula respostas baseadas nos botões clicados"""
    if "Ver no Privado" in button_text:
        return f"🔒 Dados completos enviados no privado (simulado)\n\nComando original: {original_command}\nDados sensíveis: [REDACTED]\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    elif "Ver Resumo" in button_text:
        return f"📋 **RESUMO DA CONSULTA**\n\nComando: {original_command}\nStatus: Concluído ✓\nDados encontrados: Sim\nFonte: Banco de dados oficial\nValidade: Atualizado\n\nResumo gerado em: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    elif "Baixar TXT" in button_text:
        return f"📄 **ARQUIVO GERADO**\n\nFormato: TXT\nConteúdo: Resultado da consulta\nNome: consulta_{int(time.time())}.txt\n\nLink para download: https://example.com/download/consulta_{int(time.time())}.txt\n\n⚠️ Link válido por 24 horas"
    elif "Fechar" in button_text:
        return "❌ Consulta encerrada. Para nova consulta, envie um novo comando."
    else:
        return f"Botão não reconhecido: {button_text}"

@app.post("/send-command", response_model=CommandResponse)
async def send_command(request: CommandRequest):
    """Simula envio de comando para o Telegram e retorna resposta"""
    request_id = str(uuid.uuid4())
    
    try:
        # Simula tempo de processamento
        await asyncio.sleep(random.uniform(1, 3))
        
        # Gera resposta simulada
        response_data = simulate_response(request.command)
        
        return CommandResponse(success=True, data=response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/handle-button", response_model=CommandResponse)
async def handle_button(request: ButtonRequest):
    """Processa cliques nos botões do Telegram"""
    try:
        # Simula tempo de processamento
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # Gera resposta baseada no botão clicado
        response_data = simulate_button_response(request.button_text, request.original_command)
        
        return CommandResponse(success=True, data=response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Verifica se o serviço está saudável"""
    return {
        "status": "OK",
        "mode": "demo",
        "pending_requests": len(pending_requests),
        "message": "Running in demo mode - no real Telegram connection"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

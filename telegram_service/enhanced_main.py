#!/usr/bin/env python3
"""
Versão Principal Aprimorada com Descoberta Inteligente
Integra descoberta de padrões e processamento inteligente
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

# Importa nossos módulos inteligentes
from smart_processor import SmartTelegramProcessor
from test_discovery import TelegramDiscovery

load_dotenv()

app = FastAPI(title="Enhanced Telegram Query Bridge", version="3.0.0")

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

# Processadores inteligentes
smart_processor = SmartTelegramProcessor()
discovery_system = TelegramDiscovery()

# Estado do sistema
system_status = {
    "discovery_completed": False,
    "smart_processor_ready": False,
    "last_discovery": None,
    "patterns_loaded": False
}

class CommandRequest(BaseModel):
    command: str
    timeout: int = 30
    use_smart_processing: bool = True

class BatchRequest(BaseModel):
    commands: List[str]
    timeout: int = 30
    use_smart_processing: bool = True

class DiscoveryRequest(BaseModel):
    run_discovery: bool = True
    test_all_commands: bool = True

class CommandResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None

class StatusResponse(BaseModel):
    system_ready: bool
    discovery_completed: bool
    smart_processor_ready: bool
    patterns_loaded: bool
    last_discovery: Optional[str] = None
    available_features: List[str]

@app.on_event("startup")
async def startup_event():
    """Inicializa o sistema aprimorado"""
    global system_status
    
    print("🚀 INICIANDO SISTEMA APRIMORADO v3.0")
    print("=" * 50)
    
    # Tenta carregar configuração existente
    try:
        smart_processor.load_discovery_config()
        system_status["patterns_loaded"] = True
        print("✅ Padrões de descoberta carregados")
    except:
        print("⚠️ Nenhum padrão de descoberta encontrado")
    
    # Inicializa processador inteligente
    if await smart_processor.connect():
        system_status["smart_processor_ready"] = True
        print("✅ Processador inteligente conectado")
    else:
        print("❌ Falha na conexão do processador inteligente")
    
    print("🎯 Sistema pronto para operações!")

@app.post("/discover-commands")
async def run_discovery(request: DiscoveryRequest):
    """Executa descoberta de comandos e padrões"""
    try:
        print("🔍 INICIANDO DESCOBERTA DE COMANDOS")
        
        if request.run_discovery:
            # Conecta ao sistema de descoberta
            if await discovery_system.connect():
                # Executa descoberta
                await discovery_system.run_discovery()
                
                # Recarrega configuração
                smart_processor.load_discovery_config()
                
                system_status["discovery_completed"] = True
                system_status["last_discovery"] = time.strftime('%Y-%m-%d %H:%M:%S')
                
                return {
                    "success": True,
                    "message": "Descoberta concluída com sucesso",
                    "timestamp": system_status["last_discovery"],
                    "patterns_loaded": True
                }
            else:
                raise HTTPException(status_code=503, detail="Falha na conexão para descoberta")
        
        return {"success": True, "message": "Descoberta não solicitada"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-command", response_model=CommandResponse)
async def send_command(request: CommandRequest):
    """Envia comando com processamento inteligente"""
    start_time = time.time()
    
    try:
        if not system_status["smart_processor_ready"]:
            raise HTTPException(status_code=503, detail="Processador inteligente não está pronto")
        
        # Usa processamento inteligente se solicitado
        if request.use_smart_processing:
            result = await smart_processor.process_command(request.command, request.timeout)
            
            processing_time = time.time() - start_time
            
            return CommandResponse(
                success=result['success'],
                data=result,
                processing_time=processing_time
            )
        else:
            # Processamento básico (fallback)
            # Implementar lógica básica aqui se necessário
            raise HTTPException(status_code=501, detail="Processamento básico não implementado")
            
    except Exception as e:
        processing_time = time.time() - start_time
        return CommandResponse(
            success=False,
            error=str(e),
            processing_time=processing_time
        )

@app.post("/batch-process", response_model=CommandResponse)
async def batch_process(request: BatchRequest):
    """Processa múltiplos comandos em lote"""
    start_time = time.time()
    
    try:
        if not system_status["smart_processor_ready"]:
            raise HTTPException(status_code=503, detail="Processador inteligente não está pronto")
        
        results = await smart_processor.batch_process_commands(request.commands)
        
        processing_time = time.time() - start_time
        
        return CommandResponse(
            success=True,
            data=results,
            processing_time=processing_time
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        return CommandResponse(
            success=False,
            error=str(e),
            processing_time=processing_time
        )

@app.post("/test-all-commands")
async def test_all_commands():
    """Testa todos os comandos conhecidos"""
    try:
        test_commands = [
            "/cpf 123.456.789-00",
            "/telefone (11) 98765-4321",
            "/placa ABC1234",
            "/nome João Silva",
            "/email joao@email.com",
            "/cep 01310-100",
            "/cnpj 12.345.678/0001-90",
            "/foto João Silva",
            "/titulo 123456789012",
            "/mae Maria Silva"
        ]
        
        results = await smart_processor.batch_process_commands(test_commands)
        
        return {
            "success": True,
            "message": f"Testados {len(test_commands)} comandos",
            "results": results,
            "summary": {
                "total_commands": len(test_commands),
                "successful": results.get('success_count', 0),
                "failed": results.get('error_count', 0)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Retorna status completo do sistema"""
    return StatusResponse(
        system_ready=system_status["smart_processor_ready"],
        discovery_completed=system_status["discovery_completed"],
        smart_processor_ready=system_status["smart_processor_ready"],
        patterns_loaded=system_status["patterns_loaded"],
        last_discovery=system_status["last_discovery"],
        available_features=[
            "Intelligent Command Processing",
            "Pattern Discovery",
            "Batch Processing",
            "Smart Data Scraping",
            "Automatic Button Handling",
            "Structured JSON Output"
        ]
    )

@app.get("/health")
async def health_check():
    """Health check básico"""
    return {
        "status": "OK",
        "version": "3.0.0",
        "system_ready": system_status["smart_processor_ready"],
        "features": {
            "discovery": system_status["discovery_completed"],
            "smart_processing": system_status["smart_processor_ready"],
            "patterns_loaded": system_status["patterns_loaded"]
        },
        "endpoints": {
            "send_command": "/send-command (POST)",
            "batch_process": "/batch-process (POST)",
            "discover_commands": "/discover-commands (POST)",
            "test_all_commands": "/test-all-commands (POST)",
            "status": "/status (GET)",
            "health": "/health (GET)"
        }
    }

@app.get("/")
async def root():
    """Informações do serviço"""
    return {
        "service": "Enhanced Telegram Query Bridge v3.0",
        "description": "Sistema inteligente de processamento de comandos Telegram com descoberta automática de padrões",
        "features": [
            "🧠 Processamento Inteligente de Comandos",
            "🔍 Descoberta Automática de Padrões",
            "📊 Extração Estruturada de Dados",
            "🔘 Manipulação Automática de Botões",
            "🚀 Processamento em Lote",
            "📋 Saída JSON Estruturada"
        ],
        "status": system_status,
        "endpoints": {
            "send_command": "POST /send-command - Processa comando individual",
            "batch_process": "POST /batch-process - Processa múltiplos comandos",
            "discover_commands": "POST /discover-commands - Descobre padrões",
            "test_all_commands": "POST /test-all-commands - Testa todos os comandos",
            "status": "GET /status - Status do sistema",
            "health": "GET /health - Health check"
        }
    }

@app.post("/force-discovery")
async def force_discovery():
    """Força nova descoberta de padrões"""
    try:
        print("🔄 FORÇANDO NOVA DESCOBERTA")
        
        # Remove arquivo de descoberta antigo
        if os.path.exists('discovery_results.json'):
            os.remove('discovery_results.json')
        
        # Executa nova descoberta
        if await discovery_system.connect():
            await discovery_system.run_discovery()
            
            # Recarrega configuração
            smart_processor.load_discovery_config()
            
            system_status["discovery_completed"] = True
            system_status["last_discovery"] = time.strftime('%Y-%m-%d %H:%M:%S')
            
            return {
                "success": True,
                "message": "Descoberta forçada concluída",
                "timestamp": system_status["last_discovery"]
            }
        else:
            raise HTTPException(status_code=503, detail="Falha na conexão para descoberta")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

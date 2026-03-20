#!/usr/bin/env python3
"""
Servidor de Gerenciamento para Telegram Query Bridge - Versão 2.0
Sistema robusto de gerenciamento de serviços com detecção precisa
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import psutil
import asyncio
import os
import signal
import shutil
import json
import httpx
import time
import traceback
import socket
import threading
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import logging
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('manager.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Configurações
PYTHON_SERVICE_PORT = 8001
NODE_SERVICE_PORT = 3000
MANAGER_PORT = 9000
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_TIMEOUT = 30
HEALTH_CHECK_INTERVAL = 5

app = FastAPI(title="Telegram Query Bridge Manager v2.0", version="2.0.0")

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estado dos serviços
services_state = {
    'python': {
        'process': None,
        'pid': None,
        'status': 'stopped',
        'last_check': None,
        'startup_time': None
    },
    'node': {
        'process': None,
        'pid': None,
        'status': 'stopped',
        'last_check': None,
        'startup_time': None
    }
}

class ServiceRequest(BaseModel):
    service: str
    action: str

class ServiceStatus(BaseModel):
    service: str
    status: str
    pid: Optional[int] = None
    port: int
    uptime: Optional[str] = None

def is_port_available(port: int) -> bool:
    """Verifica se porta está disponível"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            return result != 0
    except Exception:
        return False

def get_process_pid_by_port(port: int) -> Optional[int]:
    """Obtém PID do processo usando a porta"""
    try:
        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.pid:
                return conn.pid
    except Exception as e:
        logger.error(f"Erro ao buscar PID pela porta {port}: {e}")
    return None

def get_process_details(pid: int) -> dict:
    """Obtém detalhes do processo"""
    try:
        process = psutil.Process(pid)
        return {
            "pid": pid,
            "name": process.name(),
            "status": process.status(),
            "cpu_percent": process.cpu_percent(),
            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "create_time": process.create_time()
        }
    except Exception as e:
        logger.error(f"Erro ao obter detalhes do processo {pid}: {e}")
        return {"pid": pid, "error": str(e)}

def kill_process_by_port(port: int) -> bool:
    """Mata processo usando porta específica"""
    pid = get_process_pid_by_port(port)
    if pid:
        try:
            process = psutil.Process(pid)
            process.terminate()
            time.sleep(2)
            if process.is_running():
                process.kill()
            logger.info(f"Processo PID {pid} na porta {port} finalizado")
            return True
        except Exception as e:
            logger.error(f"Erro ao matar processo {pid}: {e}")
    return False

async def check_service_health(port: int, timeout: int = 5) -> bool:
    """Verifica health do serviço via HTTP"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"http://localhost:{port}/health")
            return response.status_code == 200
    except Exception:
        return False

async def start_python_service() -> bool:
    """Inicia serviço Python"""
    try:
        logger.info("Iniciando serviço Python...")
        
        # Verificar se já está rodando
        if await check_service_health(PYTHON_SERVICE_PORT):
            logger.info("Serviço Python já está rodando")
            return True
        
        # Limpar porta se necessário
        if not is_port_available(PYTHON_SERVICE_PORT):
            logger.warning(f"Limpando porta {PYTHON_SERVICE_PORT}")
            kill_process_by_port(PYTHON_SERVICE_PORT)
            await asyncio.sleep(2)
        
        # Copiar .env
        env_src = os.path.join(PROJECT_DIR, ".env")
        env_dst = os.path.join(PROJECT_DIR, "telegram_service", ".env")
        if os.path.exists(env_src):
            shutil.copy2(env_src, env_dst)
        
        # Iniciar processo
        cmd = [
            "python", "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", str(PYTHON_SERVICE_PORT),
            "--log-level", "info"
        ]
        
        working_dir = os.path.join(PROJECT_DIR, "telegram_service")
        
        process = subprocess.Popen(
            cmd,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Atualizar estado
        services_state['python']['process'] = process
        services_state['python']['pid'] = process.pid
        services_state['python']['status'] = 'starting'
        services_state['python']['startup_time'] = datetime.now()
        
        # Aguardar serviço ficar disponível
        for i in range(SERVICE_TIMEOUT):
            await asyncio.sleep(1)
            if await check_service_health(PYTHON_SERVICE_PORT):
                services_state['python']['status'] = 'running'
                logger.info(f"✅ Serviço Python iniciado (PID {process.pid})")
                return True
        
        # Se não iniciou
        services_state['python']['status'] = 'failed'
        logger.error(f"❌ Falha ao iniciar serviço Python")
        return False
        
    except Exception as e:
        services_state['python']['status'] = 'failed'
        logger.error(f"Erro ao iniciar serviço Python: {e}")
        return False

async def start_node_service() -> bool:
    """Inicia serviço Node.js"""
    try:
        logger.info("Iniciando serviço Node.js...")
        
        # Verificar se já está rodando
        if await check_service_health(NODE_SERVICE_PORT):
            logger.info("Serviço Node.js já está rodando")
            return True
        
        # Limpar porta se necessário
        if not is_port_available(NODE_SERVICE_PORT):
            logger.warning(f"Limpando porta {NODE_SERVICE_PORT}")
            kill_process_by_port(NODE_SERVICE_PORT)
            await asyncio.sleep(2)
        
        # Iniciar processo
        cmd = ["node", "api/index.js"]
        working_dir = PROJECT_DIR
        
        process = subprocess.Popen(
            cmd,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Atualizar estado
        services_state['node']['process'] = process
        services_state['node']['pid'] = process.pid
        services_state['node']['status'] = 'starting'
        services_state['node']['startup_time'] = datetime.now()
        
        # Aguardar serviço ficar disponível
        for i in range(SERVICE_TIMEOUT):
            await asyncio.sleep(1)
            if await check_service_health(NODE_SERVICE_PORT):
                services_state['node']['status'] = 'running'
                logger.info(f"✅ Serviço Node.js iniciado (PID {process.pid})")
                return True
        
        # Se não iniciou
        services_state['node']['status'] = 'failed'
        logger.error(f"❌ Falha ao iniciar serviço Node.js")
        return False
        
    except Exception as e:
        services_state['node']['status'] = 'failed'
        logger.error(f"Erro ao iniciar serviço Node.js: {e}")
        return False

async def stop_python_service() -> bool:
    """Para serviço Python"""
    try:
        logger.info("Parando serviço Python...")
        
        if services_state['python']['process']:
            process = services_state['python']['process']
            process.terminate()
            await asyncio.sleep(2)
            if process.poll() is None:
                process.kill()
            
            services_state['python']['process'] = None
            services_state['python']['pid'] = None
            services_state['python']['status'] = 'stopped'
            logger.info("✅ Serviço Python parado")
            return True
        
        # Tentar por porta
        kill_process_by_port(PYTHON_SERVICE_PORT)
        services_state['python']['status'] = 'stopped'
        return True
        
    except Exception as e:
        logger.error(f"Erro ao parar serviço Python: {e}")
        return False

async def stop_node_service() -> bool:
    """Para serviço Node.js"""
    try:
        logger.info("Parando serviço Node.js...")
        
        if services_state['node']['process']:
            process = services_state['node']['process']
            process.terminate()
            await asyncio.sleep(2)
            if process.poll() is None:
                process.kill()
            
            services_state['node']['process'] = None
            services_state['node']['pid'] = None
            services_state['node']['status'] = 'stopped'
            logger.info("✅ Serviço Node.js parado")
            return True
        
        # Tentar por porta
        kill_process_by_port(NODE_SERVICE_PORT)
        services_state['node']['status'] = 'stopped'
        return True
        
    except Exception as e:
        logger.error(f"Erro ao parar serviço Node.js: {e}")
        return False

async def update_service_status():
    """Atualiza status de todos os serviços"""
    for service_name in ['python', 'node']:
        port = PYTHON_SERVICE_PORT if service_name == 'python' else NODE_SERVICE_PORT
        
        # Verificar se processo ainda existe
        if services_state[service_name]['process']:
            if services_state[service_name]['process'].poll() is not None:
                services_state[service_name]['status'] = 'stopped'
                services_state[service_name]['process'] = None
                services_state[service_name]['pid'] = None
            else:
                # Verificar health check
                is_healthy = await check_service_health(port)
                if is_healthy and services_state[service_name]['status'] != 'running':
                    services_state[service_name]['status'] = 'running'
                elif not is_healthy and services_state[service_name]['status'] == 'running':
                    services_state[service_name]['status'] = 'unhealthy'
        else:
            # Verificar se tem processo na porta
            if await check_service_health(port):
                pid = get_process_pid_by_port(port)
                services_state[service_name]['pid'] = pid
                services_state[service_name]['status'] = 'running'
            else:
                services_state[service_name]['status'] = 'stopped'
        
        services_state[service_name]['last_check'] = datetime.now()

# Endpoints
@app.get("/")
async def root():
    """Serve dashboard"""
    dashboard_path = os.path.join(PROJECT_DIR, "web", "index.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    raise HTTPException(status_code=404, detail="Dashboard não encontrado")

@app.get("/health")
async def health_check():
    """Health check do manager"""
    return {"status": "OK", "version": "2.0.0"}

@app.get("/services/status")
async def get_services_status():
    """Retorna status atualizado dos serviços"""
    await update_service_status()
    
    services = []
    for service_name, state in services_state.items():
        port = PYTHON_SERVICE_PORT if service_name == 'python' else NODE_SERVICE_PORT
        uptime = None
        
        if state['startup_time'] and state['status'] in ['running', 'starting']:
            uptime = str(datetime.now() - state['startup_time'])
        
        services.append({
            "service": service_name,
            "status": state['status'],
            "pid": state['pid'],
            "port": port,
            "uptime": uptime,
            "last_check": state['last_check'].isoformat() if state['last_check'] else None
        })
    
    return {"services": services}

@app.post("/services/control")
async def control_service(request: ServiceRequest):
    """Controla serviços"""
    service = request.service.lower()
    action = request.action.lower()
    
    if service not in ['python', 'node']:
        raise HTTPException(status_code=400, detail="Serviço inválido")
    
    if action not in ['start', 'stop', 'restart']:
        raise HTTPException(status_code=400, detail="Ação inválida")
    
    try:
        if action == 'start':
            if service == 'python':
                success = await start_python_service()
            else:
                success = await start_node_service()
            return {"success": success, "message": f"Serviço {service} {'iniciado' if success else 'falha ao iniciar'}"}
        
        elif action == 'stop':
            if service == 'python':
                success = await stop_python_service()
            else:
                success = await stop_node_service()
            return {"success": success, "message": f"Serviço {service} {'parado' if success else 'falha ao parar'}"}
        
        elif action == 'restart':
            # Parar
            if service == 'python':
                await stop_python_service()
                await asyncio.sleep(2)
                success = await start_python_service()
            else:
                await stop_node_service()
                await asyncio.sleep(2)
                success = await start_node_service()
            return {"success": success, "message": f"Serviço {service} {'reiniciado' if success else 'falha ao reiniciar'}"}
    
    except Exception as e:
        logger.error(f"Erro no controle do serviço {service}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/telegram/auth")
async def authenticate_telegram():
    """Inicia autenticação do Telegram"""
    try:
        # Verificar credenciais
        api_id = os.getenv('API_ID')
        api_hash = os.getenv('API_HASH')
        phone_number = os.getenv('PHONE_NUMBER')
        
        if not all([api_id, api_hash, phone_number]):
            return {
                "success": False,
                "message": "Credenciais do Telegram não configuradas",
                "missing": [k for k in ['API_ID', 'API_HASH', 'PHONE_NUMBER'] if not os.getenv(k)]
            }
        
        # Verificar se serviço Python está rodando
        if services_state['python']['status'] not in ['running']:
            success = await start_python_service()
            if not success:
                return {"success": False, "message": "Falha ao iniciar serviço Python"}
        
        # Tentar autenticação
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post("http://localhost:8001/auth")
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "message": f"Erro na autenticação: {response.status_code}"}
    
    except Exception as e:
        logger.error(f"Erro na autenticação: {e}")
        return {"success": False, "message": f"Erro: {str(e)}"}

@app.get("/telegram/status")
async def get_telegram_status():
    """Verifica status da autenticação"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get("http://localhost:8001/status")
            if response.status_code == 200:
                return response.json()
            else:
                return {"authenticated": False, "status": "service_offline"}
    except Exception:
        return {"authenticated": False, "status": "service_unavailable"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando Telegram Query Bridge Manager v2.0")
    logger.info(f"Python Service Port: {PYTHON_SERVICE_PORT}")
    logger.info(f"Node.js Service Port: {NODE_SERVICE_PORT}")
    logger.info(f"Manager Port: {MANAGER_PORT}")
    
    uvicorn.run(app, host="127.0.0.1", port=MANAGER_PORT)

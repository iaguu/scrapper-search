#!/usr/bin/env python3
"""
Servidor de Gerenciamento para Telegram Query Bridge
API backend para controle dos serviços via interface web
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import subprocess
import psutil
import asyncio
import os
import signal
import json
from typing import Dict, Optional
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Telegram Query Bridge Manager", version="1.0.0")

# Configurações
PYTHON_SERVICE_PORT = 8000
NODE_SERVICE_PORT = 3000
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Processos em execução
running_processes: Dict[str, subprocess.Popen] = {}

class ServiceRequest(BaseModel):
    service: str  # 'python' ou 'node'
    action: str   # 'start' ou 'stop'

class ServiceStatus(BaseModel):
    service: str
    status: str
    pid: Optional[int] = None
    port: int
    uptime: Optional[str] = None

def is_port_in_use(port: int) -> bool:
    """Verifica se uma porta está em uso"""
    for conn in psutil.net_connections():
        if conn.laddr.port == port:
            return True
    return False

def get_process_pid_by_port(port: int) -> Optional[int]:
    """Retorna o PID do processo usando a porta especificada"""
    for conn in psutil.net_connections():
        if conn.laddr.port == port and conn.pid:
            return conn.pid
    return None

def kill_process_by_port(port: int) -> bool:
    """Mata processo usando a porta especificada"""
    pid = get_process_pid_by_port(port)
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Processo {pid} na porta {port} finalizado")
            return True
        except ProcessLookupError:
            logger.warning(f"Processo {pid} não encontrado")
        except Exception as e:
            logger.error(f"Erro ao finalizar processo {pid}: {e}")
    return False

async def start_python_service():
    """Inicia o serviço Python"""
    if is_port_in_use(PYTHON_SERVICE_PORT):
        logger.warning("Serviço Python já está rodando")
        return False
    
    try:
        cmd = [
            "python", "-m", "uvicorn", 
            "demo:app", 
            "--host", "127.0.0.1", 
            "--port", str(PYTHON_SERVICE_PORT)
        ]
        
        process = subprocess.Popen(
            cmd,
            cwd=os.path.join(PROJECT_DIR, "telegram_service"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        running_processes['python'] = process
        logger.info(f"Serviço Python iniciado com PID {process.pid}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao iniciar serviço Python: {e}")
        return False

async def start_node_service():
    """Inicia o serviço Node.js"""
    if is_port_in_use(NODE_SERVICE_PORT):
        logger.warning("Serviço Node.js já está rodando")
        return False
    
    try:
        cmd = ["npm", "start"]
        
        process = subprocess.Popen(
            cmd,
            cwd=PROJECT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        running_processes['node'] = process
        logger.info(f"Serviço Node.js iniciado com PID {process.pid}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao iniciar serviço Node.js: {e}")
        return False

def stop_python_service():
    """Para o serviço Python"""
    return kill_process_by_port(PYTHON_SERVICE_PORT)

def stop_node_service():
    """Para o serviço Node.js"""
    return kill_process_by_port(NODE_SERVICE_PORT)

@app.get("/")
async def root():
    """Serve a interface web"""
    return FileResponse("web/index.html")

@app.get("/health")
async def health_check():
    """Health check do manager"""
    return {
        "status": "OK",
        "services": {
            "python": is_port_in_use(PYTHON_SERVICE_PORT),
            "node": is_port_in_use(NODE_SERVICE_PORT)
        },
        "running_processes": len(running_processes)
    }

@app.get("/services/status")
async def get_services_status():
    """Retorna status de todos os serviços"""
    services = []
    
    # Python Service
    python_pid = get_process_pid_by_port(PYTHON_SERVICE_PORT)
    services.append(ServiceStatus(
        service="python",
        status="running" if python_pid else "stopped",
        pid=python_pid,
        port=PYTHON_SERVICE_PORT
    ))
    
    # Node.js Service
    node_pid = get_process_pid_by_port(NODE_SERVICE_PORT)
    services.append(ServiceStatus(
        service="node",
        status="running" if node_pid else "stopped",
        pid=node_pid,
        port=NODE_SERVICE_PORT
    ))
    
    return {"services": services}

@app.post("/services/control")
async def control_service(request: ServiceRequest):
    """Controla serviços (start/stop)"""
    service = request.service.lower()
    action = request.action.lower()
    
    if service not in ['python', 'node']:
        raise HTTPException(status_code=400, detail="Serviço inválido")
    
    if action not in ['start', 'stop']:
        raise HTTPException(status_code=400, detail="Ação inválida")
    
    result = False
    
    if service == 'python':
        if action == 'start':
            result = await start_python_service()
        else:
            result = stop_python_service()
    
    elif service == 'node':
        if action == 'start':
            result = await start_node_service()
        else:
            result = stop_node_service()
    
    return {
        "service": service,
        "action": action,
        "success": result,
        "message": f"Serviço {service} {'iniciado' if action == 'start' else 'parado'} com {'sucesso' if result else 'falha'}"
    }

@app.post("/services/start-all")
async def start_all_services():
    """Inicia todos os serviços"""
    python_result = await start_python_service()
    await asyncio.sleep(3)  # Aguarda Python iniciar
    node_result = await start_node_service()
    
    return {
        "python": python_result,
        "node": node_result,
        "success": python_result and node_result
    }

@app.post("/services/stop-all")
async def stop_all_services():
    """Para todos os serviços"""
    python_result = stop_python_service()
    node_result = stop_node_service()
    
    return {
        "python": python_result,
        "node": node_result,
        "success": python_result and node_result
    }

@app.get("/logs")
async def get_logs():
    """Retorna logs do sistema"""
    try:
        # Em produção, isso leria arquivos de log reais
        # Por agora, retorna logs simulados
        logs = [
            {"timestamp": "2026-01-20 20:15:00", "level": "INFO", "message": "Sistema inicializado"},
            {"timestamp": "2026-01-20 20:15:01", "level": "INFO", "message": "Verificando serviços..."},
        ]
        
        python_running = is_port_in_use(PYTHON_SERVICE_PORT)
        node_running = is_port_in_use(NODE_SERVICE_PORT)
        
        logs.append({
            "timestamp": "2026-01-20 20:15:02", 
            "level": "INFO", 
            "message": f"Python: {'Online' if python_running else 'Offline'} | Node.js: {'Online' if node_running else 'Offline'}"
        })
        
        return {"logs": logs}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config/save")
async def save_config(config: dict):
    """Salva configurações"""
    try:
        config_file = os.path.join(PROJECT_DIR, ".env")
        
        # Lê configuração atual
        env_vars = {}
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env_vars[key] = value
        
        # Atualiza com novos valores
        env_vars.update(config)
        
        # Salva arquivo
        with open(config_file, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        logger.info("Configurações salvas com sucesso")
        return {"success": True, "message": "Configurações salvas"}
        
    except Exception as e:
        logger.error(f"Erro ao salvar configurações: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config/load")
async def load_config():
    """Carrega configurações"""
    try:
        config_file = os.path.join(PROJECT_DIR, ".env")
        config = {}
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        config[key] = value
        
        return {"config": config}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9000)

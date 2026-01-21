#!/usr/bin/env python3
"""
Servidor de Gerenciamento para Telegram Query Bridge
API backend para controle dos serviços via interface web
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
from typing import Dict, Optional
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Telegram Query Bridge Manager", version="1.0.0")

# Configurar CORS para permitir conexões da dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurações
PYTHON_SERVICE_PORT = 8001
NODE_SERVICE_PORT = 3000
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Processos em execução
# Usaremos um dicionário para armazenar os PIDs dos serviços que este manager iniciou
managed_service_pids: Dict[str, int] = {}

class ServiceRequest(BaseModel):
    service: str  # 'python' ou 'node'
    action: str   # 'start', 'stop' ou 'restart'

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
    try:
        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.pid:
                return conn.pid
    except Exception as e:
        logger.error(f"Erro ao buscar PID pela porta {port}: {e}")
    return None

def get_process_details(pid: int) -> dict:
    """Retorna detalhes do processo"""
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
    """Mata processo usando a porta especificada, incluindo seus filhos."""
    pid = get_process_pid_by_port(port)
    if pid:
        try:
            process = psutil.Process(pid)
            # Terminar processos filhos primeiro para evitar órfãos
            for child in process.children(recursive=True):
                logger.info(f"Terminando processo filho {child.pid} de {pid}")
                child.terminate()
            
            logger.info(f"Terminando processo {pid} na porta {port}")
            process.terminate()
            # Aguardar a terminação, e matar se ainda estiverem vivos
            psutil.wait_procs(process.children(recursive=True) + [process], timeout=5)
            
            # Remover do rastreamento se for um serviço gerenciado
            for service_name, tracked_pid in list(managed_service_pids.items()):
                if tracked_pid == pid:
                    del managed_service_pids[service_name]
                    logger.info(f"Processo {pid} removido do rastreamento do serviço '{service_name}'.")
            return True
        except ProcessLookupError:
            logger.warning(f"Processo {pid} não encontrado")
        except Exception as e:
            logger.error(f"Erro ao finalizar processo {pid}: {e}")
    return False

async def start_python_service():
    """Inicia o serviço Python com tratamento de erros melhorado"""
    logger.info(f"Iniciando serviço Python na porta {PYTHON_SERVICE_PORT}...")
    
    # 1. Verificar se já estamos gerenciando este serviço e se ele ainda está ativo
    if 'python' in managed_service_pids and psutil.pid_exists(managed_service_pids['python']):
        current_pid = managed_service_pids['python']
        logger.warning(f"Serviço Python já está sendo gerenciado com PID {current_pid}.")
        
        # Verificar se ele está realmente escutando na porta
        if get_process_pid_by_port(PYTHON_SERVICE_PORT) == current_pid:
            logger.info("Serviço Python gerenciado está ativo e escutando na porta.")
            return True
        else:
            logger.warning(f"Serviço Python gerenciado (PID {current_pid}) está ativo, mas não escutando na porta {PYTHON_SERVICE_PORT}.")
            details = get_process_details(current_pid)
            logger.info(f"Detalhes do processo: {details}")
            
            # Tentar finalizar o processo antigo
            logger.info("Tentando finalizar processo antigo para reiniciar...")
            stop_python_service()
            await asyncio.sleep(2)

    # 2. Verificar se a porta está em uso por qualquer processo
    pid_on_port = get_process_pid_by_port(PYTHON_SERVICE_PORT)
    if pid_on_port:
        logger.warning(f"Porta {PYTHON_SERVICE_PORT} já está em uso por PID {pid_on_port}.")
        details = get_process_details(pid_on_port)
        logger.info(f"Detalhes do processo na porta: {details}")
        
        logger.info("Tentando finalizar processo...")
        if kill_process_by_port(PYTHON_SERVICE_PORT):
            await asyncio.sleep(3)
            if is_port_in_use(PYTHON_SERVICE_PORT):
                logger.error(f"Porta {PYTHON_SERVICE_PORT} ainda está em uso após tentativa de finalização.")
                return False
        else:
            logger.error("Falha ao finalizar processo na porta.")
            return False
    
    # 3. Garantir que .env existe no subdiretório
    env_src = os.path.join(PROJECT_DIR, ".env")
    env_dst = os.path.join(PROJECT_DIR, "telegram_service", ".env")
    if os.path.exists(env_src):
        try:
            logger.info(f"Copiando {env_src} para {env_dst}")
            shutil.copy2(env_src, env_dst)
        except Exception as e:
            logger.warning(f"Não foi possível copiar .env: {e}")

    # 4. Iniciar o serviço
    try:
        cmd = [
            "python", "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", str(PYTHON_SERVICE_PORT)
        ]
        
        logger.info(f"Executando comando: {' '.join(cmd)}")
        logger.info(f"Diretório de trabalho: {os.path.join(PROJECT_DIR, 'telegram_service')}")
        
        if os.name == 'nt':
            process = subprocess.Popen(
                cmd,
                cwd=os.path.join(PROJECT_DIR, "telegram_service"),
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            process = subprocess.Popen(
                cmd,
                cwd=os.path.join(PROJECT_DIR, "telegram_service"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        
        managed_service_pids['python'] = process.pid
        logger.info(f"Serviço Python iniciado com PID {process.pid}")

        # 5. Aguardar e verificar se a porta está realmente vinculada
        logger.info("Aguardando inicialização do serviço...")
        await asyncio.sleep(5)  # Aumentado para 5 segundos
        
        # Verificar se o processo ainda está vivo
        if not psutil.pid_exists(process.pid):
            logger.error(f"Processo Python {process.pid} morreu durante a inicialização.")
            return False
        
        # Verificar se a porta está em uso
        if not is_port_in_use(PYTHON_SERVICE_PORT):
            logger.error(f"Serviço Python (PID {process.pid}) está vivo, mas a porta {PYTHON_SERVICE_PORT} não está em uso.")
            
            # Tentar obter detalhes do erro
            details = get_process_details(process.pid)
            logger.error(f"Detalhes do processo: {details}")
            
            # Matar o processo falho
            kill_process_by_port(PYTHON_SERVICE_PORT)
            return False
        else:
            # Verificar se o PID na porta corresponde ao nosso processo
            pid_on_port = get_process_pid_by_port(PYTHON_SERVICE_PORT)
            if pid_on_port != process.pid:
                logger.warning(f"PID na porta ({pid_on_port}) difere do PID iniciado ({process.pid})")
            
            logger.info(f"✅ Serviço Python iniciado com sucesso na porta {PYTHON_SERVICE_PORT}")
            return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar serviço Python: {e}")
        logger.error(f"Tipo do erro: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def start_node_service():
    """Inicia o serviço Node.js"""
    # 1. Verificar se já estamos gerenciando este serviço e se ele ainda está ativo
    if 'node' in managed_service_pids and psutil.pid_exists(managed_service_pids['node']):
        current_pid = managed_service_pids['node']
        logger.warning(f"Serviço Node.js já está sendo gerenciado com PID {current_pid}.")
        if get_process_pid_by_port(NODE_SERVICE_PORT) == current_pid:
            logger.info("Serviço Node.js gerenciado está ativo e escutando na porta.")
            return True
        else:
            logger.warning(f"Serviço Node.js gerenciado (PID {current_pid}) está ativo, mas não escutando na porta {NODE_SERVICE_PORT}. Tentando finalizar para reiniciar.")
            stop_node_service()
            await asyncio.sleep(1)

    # 2. Verificar se a porta está em uso por qualquer processo
    pid_on_port = get_process_pid_by_port(NODE_SERVICE_PORT)
    if pid_on_port:
        logger.warning(f"Porta {NODE_SERVICE_PORT} do serviço Node.js já está em uso por PID {pid_on_port}. Tentando finalizar.")
        kill_process_by_port(NODE_SERVICE_PORT)
        await asyncio.sleep(2)
        if is_port_in_use(NODE_SERVICE_PORT):
            logger.error(f"Porta {NODE_SERVICE_PORT} do serviço Node.js ainda está em uso após tentativa de finalização. Não é possível iniciar.")
        return False
    
    try:
        # Executa node diretamente para evitar loop do npm start e problemas de PID no Windows
        cmd = ["node", "api/index.js"]
        
        if os.name == 'nt':
            process = subprocess.Popen(
                cmd,
                cwd=PROJECT_DIR,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            process = subprocess.Popen(
                cmd,
                cwd=PROJECT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        
        managed_service_pids['node'] = process.pid
        logger.info(f"Serviço Node.js iniciado com PID {process.pid}")

        await asyncio.sleep(3) # Dar tempo para o Node.js iniciar e vincular a porta
        if not is_port_in_use(NODE_SERVICE_PORT):
            logger.error(f"Serviço Node.js (PID {process.pid}) iniciado, mas a porta {NODE_SERVICE_PORT} não está em uso. Pode ter falhado ao iniciar.")
            kill_process_by_port(NODE_SERVICE_PORT)
            return False

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
    dashboard_path = os.path.join(PROJECT_DIR, "web", "index.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    else:
        raise HTTPException(status_code=404, detail="Dashboard não encontrado")

@app.get("/health")
async def health_check():
    """Health check do manager"""
    return {
        "status": "OK",
        "services": {
            "python": is_port_in_use(PYTHON_SERVICE_PORT),
            "node": is_port_in_use(NODE_SERVICE_PORT)
        },
        "managed_services_count": len(managed_service_pids)
    }

@app.get("/services/status")
async def get_services_status():
    """Retorna status de todos os serviços com detalhes melhorados"""
    services = []
    
    # Python Service
    python_pid_on_port = get_process_pid_by_port(PYTHON_SERVICE_PORT)
    python_status = "stopped"
    python_pid = None
    python_details = None
    
    if python_pid_on_port:
        python_status = "running"
        python_pid = python_pid_on_port
        python_details = get_process_details(python_pid_on_port)
    elif 'python' in managed_service_pids and psutil.pid_exists(managed_service_pids['python']):
        # Se não está na porta, mas estamos rastreando e está vivo, pode estar em um estado estranho
        python_status = "running (port not bound)"
        python_pid = managed_service_pids['python']
        python_details = get_process_details(managed_service_pids['python'])
    elif any("python" in p.info["name"].lower() for p in psutil.process_iter(['pid', 'name'])):
        python_status = "process_found (port_not_bound)"
        python_details = {"error": "Python process found but not listening on port"}

    services.append({
        "service": "python",
        "status": python_status,
        "pid": python_pid,
        "port": PYTHON_SERVICE_PORT,
        "details": python_details,
        "managed": 'python' in managed_service_pids
    })
    
    # Node.js Service
    node_pid_on_port = get_process_pid_by_port(NODE_SERVICE_PORT)
    node_status = "stopped"
    node_pid = None
    node_details = None
    
    if node_pid_on_port:
        node_status = "running"
        node_pid = node_pid_on_port
        node_details = get_process_details(node_pid_on_port)
    elif 'node' in managed_service_pids and psutil.pid_exists(managed_service_pids['node']):
        node_status = "running (port not bound)"
        node_pid = managed_service_pids['node']
        node_details = get_process_details(managed_service_pids['node'])
    elif any("node" in p.info["name"].lower() for p in psutil.process_iter(['pid', 'name'])):
        node_status = "process_found (port_not_bound)"
        node_details = {"error": "Node process found but not listening on port"}

    services.append({
        "service": "node",
        "status": node_status,
        "pid": node_pid,
        "port": NODE_SERVICE_PORT,
        "details": node_details,
        "managed": 'node' in managed_service_pids
    })
    
    return {"services": services}

@app.post("/services/control")
async def control_service(request: ServiceRequest):
    """Controla serviços (start/stop)"""
    service = request.service.lower()
    action = request.action.lower()
    
    if service not in ['python', 'node']:
        raise HTTPException(status_code=400, detail="Serviço inválido")
    
    if action not in ['start', 'stop', 'restart']:
        raise HTTPException(status_code=400, detail="Ação inválida")
    
    result = False
    message = ""
    
    if action == 'restart':
        if service == 'python':
            stop_python_service()
            await asyncio.sleep(2)
            result = await start_python_service()
        elif service == 'node':
            stop_node_service()
            await asyncio.sleep(2)
            result = await start_node_service()
        message = f"Serviço {service} reiniciado com {'sucesso' if result else 'falha'}"
    else:
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
        message = f"Serviço {service} {'iniciado' if action == 'start' else 'parado'} com {'sucesso' if result else 'falha'}"
    
    return {
        "service": service,
        "action": action,
        "success": result,
        "message": message
    }

@app.post("/services/restart-all")
async def restart_all_services():
    """Reinicia todos os serviços com retry"""
    logger.info("Iniciando reinicialização completa de todos os serviços...")
    
    # Parar todos os serviços
    python_stopped = stop_python_service()
    node_stopped = stop_node_service()
    
    if python_stopped:
        logger.info("Serviço Python parado com sucesso")
    else:
        logger.warning("Falha ao parar serviço Python")
        
    if node_stopped:
        logger.info("Serviço Node.js parado com sucesso")
    else:
        logger.warning("Falha ao parar serviço Node.js")
    
    # Aguardar para liberar portas
    await asyncio.sleep(3)
    
    # Iniciar serviços com retry
    max_retries = 3
    python_success = False
    node_success = False
    
    for attempt in range(max_retries):
        logger.info(f"Tentativa {attempt + 1}/{max_retries} para iniciar serviços...")
        
        if not python_success:
            python_success = await start_python_service()
            
        await asyncio.sleep(2)  # Aguardar entre serviços
        
        if not node_success:
            node_success = await start_node_service()
            
        if python_success and node_success:
            logger.info("Todos os serviços iniciados com sucesso!")
            break
            
        if attempt < max_retries - 1:
            logger.warning(f"Tentativa {attempt + 1} falhou, aguardando antes de retry...")
            await asyncio.sleep(5)
    
    return {
        "python": python_success,
        "node": node_success,
        "success": python_success and node_success,
        "attempts": attempt + 1
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

# Endpoints de Proxy para Port Forwarding
@app.api_route("/proxy/python/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_python(request, path: str):
    """Proxy para o serviço Python - usado quando o serviço está busy"""
    python_url = f"http://localhost:{PYTHON_SERVICE_PORT}/{path}"
    
    if not is_port_in_use(PYTHON_SERVICE_PORT):
        raise HTTPException(status_code=503, detail="Serviço Python não está disponível")
    
    try:
        async with httpx.AsyncClient() as client:
            if request.method == "GET":
                response = await client.get(python_url, params=request.query_params)
            elif request.method == "POST":
                body = await request.body()
                response = await client.post(python_url, content=body, headers=dict(request.headers))
            elif request.method == "PUT":
                body = await request.body()
                response = await client.put(python_url, content=body, headers=dict(request.headers))
            elif request.method == "DELETE":
                response = await client.delete(python_url, headers=dict(request.headers))
            
            return response.json()
    except Exception as e:
        logger.error(f"Erro no proxy Python: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no proxy: {str(e)}")

@app.api_route("/proxy/node/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_node(request, path: str):
    """Proxy para o serviço Node.js - usado quando o serviço está busy"""
    node_url = f"http://localhost:{NODE_SERVICE_PORT}/{path}"
    
    if not is_port_in_use(NODE_SERVICE_PORT):
        raise HTTPException(status_code=503, detail="Serviço Node.js não está disponível")
    
    try:
        async with httpx.AsyncClient() as client:
            if request.method == "GET":
                response = await client.get(node_url, params=request.query_params)
            elif request.method == "POST":
                body = await request.body()
                response = await client.post(node_url, content=body, headers=dict(request.headers))
            elif request.method == "PUT":
                body = await request.body()
                response = await client.put(node_url, content=body, headers=dict(request.headers))
            elif request.method == "DELETE":
                response = await client.delete(node_url, headers=dict(request.headers))
            
            return response.json()
    except Exception as e:
        logger.error(f"Erro no proxy Node: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no proxy: {str(e)}")

@app.get("/proxy/status")
async def proxy_status():
    """Verifica status dos serviços para proxy"""
    return {
        "python_available": is_port_in_use(PYTHON_SERVICE_PORT),
        "node_available": is_port_in_use(NODE_SERVICE_PORT),
        "python_url": f"http://localhost:{PYTHON_SERVICE_PORT}",
        "node_url": f"http://localhost:{NODE_SERVICE_PORT}",
        "proxy_endpoints": {
            "python": "/proxy/python/{path}",
            "node": "/proxy/node/{path}"
        }
    }

@app.get("/debug/processes")
async def debug_processes():
    """Endpoint de debug para verificar processos e portas"""
    try:
        all_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_info']):
            try:
                all_processes.append({
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "status": proc.info['status'],
                    "cpu_percent": proc.info['cpu_percent'],
                    "memory_mb": round(proc.info['memory_info'].rss / 1024 / 1024, 2) if proc.info['memory_info'] else 0
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        port_info = {}
        for port in [PYTHON_SERVICE_PORT, NODE_SERVICE_PORT, 9000]:
            port_info[port] = {
                "in_use": is_port_in_use(port),
                "pid": get_process_pid_by_port(port),
                "process_details": get_process_details(get_process_pid_by_port(port)) if get_process_pid_by_port(port) else None
            }
        
        connections = []
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port in [PYTHON_SERVICE_PORT, NODE_SERVICE_PORT, 9000]:
                    connections.append({
                        "local_address": f"{conn.laddr.ip}:{conn.laddr.port}",
                        "remote_address": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                        "status": conn.status,
                        "pid": conn.pid
                    })
        except Exception as e:
            logger.error(f"Erro ao obter conexões: {e}")
        
        return {
            "timestamp": time.time(),
            "managed_services": managed_service_pids,
            "port_info": port_info,
            "connections": connections,
            "python_processes": [p for p in all_processes if 'python' in p['name'].lower()],
            "node_processes": [p for p in all_processes if 'node' in p['name'].lower()]
        }
    except Exception as e:
        logger.error(f"Erro no endpoint debug/processes: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e), "traceback": traceback.format_exc()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9000)

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
import socket
import threading
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import logging
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração de logging com console e arquivo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('manager.log', encoding='utf-8')  # File output
    ]
)
logger = logging.getLogger(__name__)

# Configurações avançadas
PYTHON_SERVICE_PORT = 8001
NODE_SERVICE_PORT = 3000
MANAGER_PORT = 9000
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_RETRIES = 3
RETRY_DELAY = 2
HEALTH_CHECK_INTERVAL = 30
SERVICE_TIMEOUT = 10

app = FastAPI(title="Telegram Query Bridge Manager", version="1.0.0")

# Adicionar middleware CORS para permitir requisições do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.info("Iniciando Telegram Query Bridge Manager...")
logging.info(f"Python Service Port: {PYTHON_SERVICE_PORT}")
logging.info(f"Node.js Service Port: {NODE_SERVICE_PORT}")
logging.info(f"Manager Port: {MANAGER_PORT}")
logging.info(f"Project Directory: {PROJECT_DIR}")

# Processos em execução e estado
managed_service_pids: Dict[str, int] = {}
service_health_cache: Dict[str, Tuple[bool, datetime]] = {}
service_startup_times: Dict[str, datetime] = {}
last_error_log: Dict[str, str] = {}
performance_metrics: Dict[str, Dict] = {}

class ServiceRequest(BaseModel):
    service: str  # 'python' ou 'node'
    action: str   # 'start', 'stop' ou 'restart'

class ServiceStatus(BaseModel):
    service: str
    status: str
    pid: Optional[int] = None
    port: int
    uptime: Optional[str] = None

def is_port_available(port: int) -> bool:
    """Verifica se uma porta está disponível para uso"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            return result != 0
    except Exception:
        return False

async def wait_for_port(port: int, timeout: int = 30) -> bool:
    """Aguarda uma porta ficar disponível"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_available(port):
            return True
        await asyncio.sleep(1)
    return False

async def wait_for_service(port: int, timeout: int = 30) -> bool:
    """Aguarda um serviço ficar disponível na porta"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"http://localhost:{port}/health")
                if response.status_code == 200:
                    return True
        except Exception:
            pass
        await asyncio.sleep(1)
    return False

async def retry_with_backoff(func, *args, max_retries: int = MAX_RETRIES, **kwargs):
    """Executa função com retry e backoff exponencial"""
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            delay = RETRY_DELAY * (2 ** attempt)
            logger.warning(f"Tentativa {attempt + 1} falhou, retry em {delay}s: {e}")
            await asyncio.sleep(delay)

def update_service_health(service: str, healthy: bool):
    """Atualiza cache de health do serviço"""
    service_health_cache[service] = (healthy, datetime.now())

def get_service_health(service: str) -> bool:
    """Obtém health do serviço do cache"""
    if service not in service_health_cache:
        return False
    
    healthy, timestamp = service_health_cache[service]
    # Cache válido por 30 segundos
    if datetime.now() - timestamp > timedelta(seconds=HEALTH_CHECK_INTERVAL):
        return False
    
    return healthy

def log_error(service: str, error: str):
    """Registra erro do serviço"""
    last_error_log[service] = f"{datetime.now().isoformat()}: {error}"
    logger.error(f"Erro no serviço {service}: {error}")

def update_performance_metrics(service: str, metrics: Dict):
    """Atualiza métricas de performance"""
    if service not in performance_metrics:
        performance_metrics[service] = {}
    performance_metrics[service].update(metrics)
    performance_metrics[service]['last_updated'] = datetime.now().isoformat()

def is_port_in_use(port: int) -> bool:
    """Verifica se uma porta está em uso"""
    return not is_port_available(port)

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
    """Inicia o serviço Python com retry e tratamento robusto"""
    return await retry_with_backoff(_start_python_service_internal)

async def _start_python_service_internal():
    """Implementação interna de inicialização do serviço Python"""
    service_name = 'python'
    port = PYTHON_SERVICE_PORT
    
    logger.info(f"Iniciando serviço Python na porta {port}...")
    service_startup_times[service_name] = datetime.now()
    
    # 1. Verificar se já está rodando e saudável
    if service_name in managed_service_pids:
        current_pid = managed_service_pids[service_name]
        if psutil.pid_exists(current_pid) and get_process_pid_by_port(port) == current_pid:
            if await wait_for_service(port, timeout=5):
                logger.info(f"Serviço Python já está rodando e saudável (PID {current_pid})")
                update_service_health(service_name, True)
                return True
            else:
                logger.warning(f"Serviço Python rodando mas não respondendo (PID {current_pid})")
    
    # 2. Limpar porta se necessário
    if not await wait_for_port(port, timeout=10):
        logger.warning(f"Porta {port} está em uso, tentando liberar...")
        if not kill_process_by_port(port):
            raise Exception(f"Não foi possível liberar porta {port}")
        
        if not await wait_for_port(port, timeout=10):
            raise Exception(f"Porta {port} não foi liberada após tentativas")
    
    # 3. Validar ambiente
    if not await _validate_python_environment():
        raise Exception("Validação do ambiente Python falhou")
    
    # 4. Iniciar serviço
    process = await _start_python_process()
    managed_service_pids[service_name] = process.pid
    
    # 5. Aguardar e validar
    if not await wait_for_service(port, timeout=30):
        logger.error(f"Serviço Python não ficou disponível em {port} após 30s")
        details = get_process_details(process.pid)
        logger.error(f"Detalhes do processo: {details}")
        await stop_python_service()
        raise Exception(f"Serviço Python não respondeu na porta {port}")
    
    # 6. Sucesso
    update_service_health(service_name, True)
    update_performance_metrics(service_name, {
        'startup_time': (datetime.now() - service_startup_times[service_name]).total_seconds(),
        'pid': process.pid,
        'port': port
    })
    logger.info(f"✅ Serviço Python iniciado com sucesso (PID {process.pid}, porta {port})")
    return True

async def _validate_python_environment() -> bool:
    """Valida ambiente Python"""
    try:
        # Verificar .env
        env_src = os.path.join(PROJECT_DIR, ".env")
        env_dst = os.path.join(PROJECT_DIR, "telegram_service", ".env")
        
        if os.path.exists(env_src):
            shutil.copy2(env_src, env_dst)
            logger.info("Arquivo .env copiado para telegram_service")
        
        # Verificar dependências
        telegram_service_dir = os.path.join(PROJECT_DIR, "telegram_service")
        main_file = os.path.join(telegram_service_dir, "main.py")
        
        if not os.path.exists(main_file):
            logger.error(f"Arquivo {main_file} não encontrado")
            return False
        
        return True
    except Exception as e:
        log_error('python', f"Validação de ambiente falhou: {e}")
        return False

async def _start_python_process():
    """Inicia processo Python"""
    cmd = [
        "python", "-m", "uvicorn", 
        "main:app", 
        "--host", "0.0.0.0", 
        "--port", str(PYTHON_SERVICE_PORT),
        "--log-level", "info"
    ]
    
    working_dir = os.path.join(PROJECT_DIR, "telegram_service")
    
    try:
        if os.name == 'nt':
            process = subprocess.Popen(
                cmd,
                cwd=working_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        else:
            process = subprocess.Popen(
                cmd,
                cwd=working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        
        logger.info(f"Processo Python iniciado com PID {process.pid}")
        return process
        
    except Exception as e:
        log_error('python', f"Falha ao iniciar processo: {e}")
        raise

async def start_node_service():
    """Inicia o serviço Node.js com retry e tratamento robusto"""
    return await retry_with_backoff(_start_node_service_internal)

async def _start_node_service_internal():
    """Implementação interna de inicialização do serviço Node.js"""
    service_name = 'node'
    port = NODE_SERVICE_PORT
    
    logger.info(f"Iniciando serviço Node.js na porta {port}...")
    service_startup_times[service_name] = datetime.now()
    
    # 1. Verificar se já está rodando e saudável
    if service_name in managed_service_pids:
        current_pid = managed_service_pids[service_name]
        if psutil.pid_exists(current_pid) and get_process_pid_by_port(port) == current_pid:
            if await wait_for_service(port, timeout=5):
                logger.info(f"Serviço Node.js já está rodando e saudável (PID {current_pid})")
                update_service_health(service_name, True)
                return True
            else:
                logger.warning(f"Serviço Node.js rodando mas não respondendo (PID {current_pid})")
    
    # 2. Limpar porta se necessário
    if not await wait_for_port(port, timeout=10):
        logger.warning(f"Porta {port} está em uso, tentando liberar...")
        if not kill_process_by_port(port):
            raise Exception(f"Não foi possível liberar porta {port}")
        
        if not await wait_for_port(port, timeout=10):
            raise Exception(f"Porta {port} não foi liberada após tentativas")
    
    # 3. Validar ambiente
    if not await _validate_node_environment():
        raise Exception("Validação do ambiente Node.js falhou")
    
    # 4. Iniciar serviço
    process = await _start_node_process()
    managed_service_pids[service_name] = process.pid
    
    # 5. Aguardar e validar
    if not await wait_for_service(port, timeout=30):
        logger.error(f"Serviço Node.js não ficou disponível em {port} após 30s")
        details = get_process_details(process.pid)
        logger.error(f"Detalhes do processo: {details}")
        await stop_node_service()
        raise Exception(f"Serviço Node.js não respondeu na porta {port}")
    
    # 6. Sucesso
    update_service_health(service_name, True)
    update_performance_metrics(service_name, {
        'startup_time': (datetime.now() - service_startup_times[service_name]).total_seconds(),
        'pid': process.pid,
        'port': port
    })
    logger.info(f"✅ Serviço Node.js iniciado com sucesso (PID {process.pid}, porta {port})")
    return True

async def _validate_node_environment() -> bool:
    """Valida ambiente Node.js"""
    try:
        # Verificar package.json
        package_json = os.path.join(PROJECT_DIR, "package.json")
        api_file = os.path.join(PROJECT_DIR, "api", "index.js")
        
        if not os.path.exists(package_json):
            logger.error(f"Arquivo {package_json} não encontrado")
            return False
        
        if not os.path.exists(api_file):
            logger.error(f"Arquivo {api_file} não encontrado")
            return False
        
        return True
    except Exception as e:
        log_error('node', f"Validação de ambiente falhou: {e}")
        return False

async def _start_node_process():
    """Inicia processo Node.js"""
    cmd = ["node", "api/index.js"]
    
    try:
        if os.name == 'nt':
            process = subprocess.Popen(
                cmd,
                cwd=PROJECT_DIR,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        else:
            process = subprocess.Popen(
                cmd,
                cwd=PROJECT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        
        logger.info(f"Processo Node.js iniciado com PID {process.pid}")
        return process
        
    except Exception as e:
        log_error('node', f"Falha ao iniciar processo: {e}")
        raise

async def stop_python_service():
    """Para o serviço Python"""
    service_name = 'python'
    port = PYTHON_SERVICE_PORT
    
    try:
        # Remover do registro de processos gerenciados
        if service_name in managed_service_pids:
            pid = managed_service_pids[service_name]
            del managed_service_pids[service_name]
            
            # Matar processo pelo PID
            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                process.terminate()
                
                # Aguardar e forçar se necessário
                await asyncio.sleep(2)
                if psutil.pid_exists(pid):
                    process.kill()
                    
                logger.info(f"Serviço Python parado (PID {pid})")
        
        # Limpar porta se necessário
        kill_process_by_port(port)
        update_service_health(service_name, False)
        return True
        
    except Exception as e:
        logger.error(f"Erro ao parar serviço Python: {e}")
        return False

async def stop_node_service():
    """Para o serviço Node.js"""
    service_name = 'node'
    port = NODE_SERVICE_PORT
    
    try:
        # Remover do registro de processos gerenciados
        if service_name in managed_service_pids:
            pid = managed_service_pids[service_name]
            del managed_service_pids[service_name]
            
            # Matar processo pelo PID
            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                process.terminate()
                
                # Aguardar e forçar se necessário
                await asyncio.sleep(2)
                if psutil.pid_exists(pid):
                    process.kill()
                    
                logger.info(f"Serviço Node.js parado (PID {pid})")
        
        # Limpar porta se necessário
        kill_process_by_port(port)
        update_service_health(service_name, False)
        return True
        
    except Exception as e:
        logger.error(f"Erro ao parar serviço Node.js: {e}")
        return False

async def is_service_running(service: str) -> bool:
    """Verifica se um serviço está rodando e respondendo"""
    port = PYTHON_SERVICE_PORT if service == 'python' else NODE_SERVICE_PORT
    return await wait_for_service(port, timeout=5)

async def _start_node_process():
    """Inicia processo Node.js"""
    cmd = ["node", "api/index.js"]
    
    try:
        # Verificar se a porta está em uso por qualquer processo
        pid_on_port = get_process_pid_by_port(NODE_SERVICE_PORT)
        if pid_on_port:
            logger.warning(f"Porta {NODE_SERVICE_PORT} do serviço Node.js já está em uso por PID {pid_on_port}. Tentando finalizar.")
            kill_process_by_port(NODE_SERVICE_PORT)
            await asyncio.sleep(2)
            if is_port_in_use(NODE_SERVICE_PORT):
                logger.error(f"Porta {NODE_SERVICE_PORT} do serviço Node.js ainda está em uso após tentativa de finalização. Não é possível iniciar.")
                return False
        
        # Executa node diretamente para evitar loop do npm start e problemas de PID no Windows
        if os.name == 'nt':
            process = subprocess.Popen(
                cmd,
                cwd=PROJECT_DIR,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        else:
            process = subprocess.Popen(
                cmd,
                cwd=PROJECT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        
        logger.info(f"Processo Node.js iniciado com PID {process.pid}")
        return process
        
    except Exception as e:
        log_error('node', f"Falha ao iniciar processo: {e}")
        raise

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
    logging.info('Health check recebido')
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
    
    # Verificar se serviço está realmente respondendo
    python_responding = await wait_for_service(PYTHON_SERVICE_PORT, timeout=3)
    
    if python_pid_on_port and python_responding:
        python_status = "running"
        python_pid = python_pid_on_port
        python_details = get_process_details(python_pid_on_port)
    elif python_pid_on_port and not python_responding:
        python_status = "process_found (not_responding)"
        python_pid = python_pid_on_port
        python_details = {"error": "Python process found but not responding to health checks"}
    elif 'python' in managed_service_pids and psutil.pid_exists(managed_service_pids['python']):
        python_status = "managed_process (not_responding)"
        python_pid = managed_service_pids['python']
        python_details = get_process_details(managed_service_pids['python'])
    else:
        # Verificar se existe algum processo python
        python_processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'python' in proc.info['name'].lower():
                        python_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
            
        if python_processes:
            python_status = "python_processes_found (not_on_port)"
            python_details = {"error": f"Found {len(python_processes)} Python process(es) but none listening on port {PYTHON_SERVICE_PORT}"}

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
    
    # Verificar se serviço está realmente respondendo
    node_responding = await wait_for_service(NODE_SERVICE_PORT, timeout=3)
    
    if node_pid_on_port and node_responding:
        node_status = "running"
        node_pid = node_pid_on_port
        node_details = get_process_details(node_pid_on_port)
    elif node_pid_on_port and not node_responding:
        node_status = "process_found (not_responding)"
        node_pid = node_pid_on_port
        node_details = {"error": "Node process found but not responding to health checks"}
    elif 'node' in managed_service_pids and psutil.pid_exists(managed_service_pids['node']):
        node_status = "managed_process (not_responding)"
        node_pid = managed_service_pids['node']
        node_details = get_process_details(managed_service_pids['node'])
    else:
        # Verificar se existe algum processo node
        node_processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'node' in proc.info['name'].lower():
                        node_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
            
        if node_processes:
            node_status = "node_processes_found (not_on_port)"
            node_details = {"error": f"Found {len(node_processes)} Node process(es) but none listening on port {NODE_SERVICE_PORT}"}

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
    """Controla o ciclo de vida completo dos serviços."""
    service = request.service.lower()
    action = request.action.lower()
    
    if service not in ['python', 'node']:
        raise HTTPException(status_code=400, detail="Serviço inválido")
    
    if action not in ['start', 'stop', 'restart']:
        raise HTTPException(status_code=400, detail="Ação inválida")
        
    port = PYTHON_SERVICE_PORT if service == 'python' else NODE_SERVICE_PORT
    
    if action == 'start':
        # 1. Garante que o processo está de pé
        pid = get_process_pid_by_port(port)
        if not pid or not psutil.pid_exists(pid):
            logging.info(f"Processo '{service}' não encontrado, iniciando...")
            try:
                if service == 'python':
                    success = await start_python_service()
                else:
                    success = await start_node_service()
                    
                if not success:
                    raise Exception(f"Falha ao iniciar serviço {service}")
                await asyncio.sleep(3) # Reduzido para 3 segundos
            except Exception as e:
                logging.error(f"Erro ao iniciar serviço {service}: {e}")
                raise HTTPException(status_code=500, detail=f"Falha ao iniciar serviço {service}: {e}")
        
        # 2. Verifica se o serviço está respondendo antes de chamar /start
        if not await wait_for_service(port, timeout=10):
            logging.warning(f"Serviço {service} não está respondendo em {port}")
        
        # 3. Tenta ativar o serviço chamando seu endpoint /start (se existir)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(f"http://localhost:{port}/start")
                # Se o endpoint não existir (404), considera que o serviço já está ativo
                if response.status_code not in [200, 404]:
                    response.raise_for_status()
            message = f"Serviço {service} ativado com sucesso."
            return {"success": True, "message": message}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                message = f"Serviço {service} iniciado (endpoint /start não encontrado)."
                return {"success": True, "message": message}
            else:
                logging.error(f"Falha ao ativar o serviço {service}: {e}")
                raise HTTPException(status_code=500, detail=f"Falha ao ativar o serviço: {e}")
        except Exception as e:
            logging.error(f"Falha ao ativar o serviço {service}: {e}")
            # Não falha completamente se o /start não funcionar
            message = f"Serviço {service} iniciado, mas não foi possível ativar via endpoint."
            return {"success": True, "message": message, "warning": str(e)}

    elif action == 'stop':
        # 1. Desativa o serviço chamando seu endpoint /stop
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"http://localhost:{port}/stop", timeout=10)
        except Exception as e:
            logging.warning(f"Não foi possível desativar o serviço {service} (pode já estar parado): {e}")

        # 2. Para o processo
        if service == 'python':
            result = await stop_python_service()
        else:
            result = await stop_node_service()
            
        message = f"Serviço {service} parado com {'sucesso' if result else 'falha'}."
        return {"success": result, "message": message}

    elif action == 'restart':
        # Stop
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"http://localhost:{port}/stop", timeout=10)
        except Exception:
            pass
            
        if service == 'python':
            await stop_python_service()
        else:
            await stop_node_service()
            
        await asyncio.sleep(3)

        # Start
        if service == 'python':
            await start_python_service()
        else:
            await start_node_service()
            
        await asyncio.sleep(5)
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"http://localhost:{port}/start", timeout=20)
            message = f"Serviço {service} reiniciado e ativado com sucesso."
            return {"success": True, "message": message}
        except Exception as e:
            logging.error(f"Falha ao reativar o serviço {service} após reiniciar: {e}")
            raise HTTPException(status_code=500, detail=f"Falha ao reativar após reiniciar: {e}")
    
    return {"success": False, "message": "Ação não implementada"}

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

# Endpoints avançados de monitoramento
@app.get("/metrics")
async def get_metrics():
    """Retorna métricas detalhadas do sistema"""
    return {
        "timestamp": datetime.now().isoformat(),
        "uptime": {
            service: (datetime.now() - startup_time).total_seconds()
            for service, startup_time in service_startup_times.items()
        },
        "performance_metrics": performance_metrics,
        "health_cache": {
            service: {
                "healthy": healthy,
                "last_check": timestamp.isoformat(),
                "cache_age_seconds": (datetime.now() - timestamp).total_seconds()
            }
            for service, (healthy, timestamp) in service_health_cache.items()
        },
        "error_log": last_error_log,
        "system_resources": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent
        }
    }

@app.get("/logs")
async def get_logs(service: Optional[str] = None, lines: int = 50):
    """Retorna logs do sistema"""
    try:
        log_file = os.path.join(PROJECT_DIR, 'manager.log')
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                
            if service:
                # Filtrar por serviço
                filtered_lines = [line for line in all_lines if service.lower() in line.lower()]
                return {"logs": filtered_lines[-lines:], "total": len(filtered_lines)}
            
            return {"logs": all_lines[-lines:], "total": len(all_lines)}
        else:
            return {"logs": [], "total": 0, "message": "Arquivo de log não encontrado"}
    except Exception as e:
        logger.error(f"Erro ao ler logs: {e}")
        return {"logs": [], "error": str(e)}

@app.post("/telegram/auth")
async def authenticate_telegram():
    """Inicia processo de autenticação do Telegram"""
    try:
        # Verificar se as credenciais estão configuradas
        api_id = os.getenv('API_ID')
        api_hash = os.getenv('API_HASH')
        phone_number = os.getenv('PHONE_NUMBER')
        
        if not all([api_id, api_hash, phone_number]):
            return {
                "success": False,
                "message": "Credenciais do Telegram não configuradas no .env",
                "missing": [k for k in ['API_ID', 'API_HASH', 'PHONE_NUMBER'] 
                           if not os.getenv(k)]
            }
        
        # Iniciar serviço do Telegram se não estiver ativo
        python_running = await is_service_running('python')
        if not python_running:
            success = await start_service('python')
            if not success:
                return {"success": False, "message": "Falha ao iniciar serviço Python"}
        
        # Chamar endpoint de autenticação no serviço Telegram
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post("http://localhost:8001/auth")
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "message": f"Erro na autenticação: {response.status_code}"
                }
                
    except Exception as e:
        logger.error(f"Erro na autenticação do Telegram: {e}")
        return {"success": False, "message": f"Erro: {str(e)}"}

@app.get("/telegram/status")
async def get_telegram_status():
    """Verifica status da autenticação do Telegram"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get("http://localhost:8001/status")
            if response.status_code == 200:
                return response.json()
            else:
                return {"authenticated": False, "status": "service_offline"}
    except Exception:
        return {"authenticated": False, "status": "service_unavailable"}

@app.post("/services/restart-all")
async def restart_all_services():
    """Reinicia todos os serviços"""
    results = {}
    
    for service in ['python', 'node']:
        try:
            if service == 'python':
                stop_python_service()
                await asyncio.sleep(2)
                success = await start_python_service()
            elif service == 'node':
                stop_node_service()
                await asyncio.sleep(2)
                success = await start_node_service()
            results[service] = success
        except Exception as e:
            results[service] = False
            log_error(service, f"Falha ao reiniciar: {e}")
    
    return {
        "success": all(results.values()),
        "results": results,
        "message": "Todos os serviços reiniciados" if all(results.values()) else "Alguns serviços falharam"
    }

@app.get("/system/info")
async def get_system_info():
    """Retorna informações detalhadas do sistema"""
    return {
        "system": {
            "platform": os.name,
            "python_version": os.sys.version,
            "working_directory": PROJECT_DIR,
            "timestamp": datetime.now().isoformat()
        },
        "services": {
            "python": {
                "port": PYTHON_SERVICE_PORT,
                "managed": 'python' in managed_service_pids,
                "pid": managed_service_pids.get('python'),
                "health": get_service_health('python')
            },
            "node": {
                "port": NODE_SERVICE_PORT,
                "managed": 'node' in managed_service_pids,
                "pid": managed_service_pids.get('node'),
                "health": get_service_health('node')
            },
            "manager": {
                "port": MANAGER_PORT,
                "pid": os.getpid()
            }
        },
        "network": {
            "ports_in_use": [conn.laddr.port for conn in psutil.net_connections()],
            "python_available": is_port_in_use(PYTHON_SERVICE_PORT),
            "node_available": is_port_in_use(NODE_SERVICE_PORT)
        }
    }
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

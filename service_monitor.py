#!/usr/bin/env python3
"""
Sistema de Monitoramento e Restart Automático para Serviços
"""

import asyncio
import logging
import requests
import subprocess
import time
import os
import signal
import sys
from typing import Dict, Optional
import psutil

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('service_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ServiceMonitor:
    def __init__(self):
        self.services = {
            'python': {
                'url': 'http://localhost:8000/health',
                'port': 8000,
                'command': ['python', 'telegram_service/main.py'],
                'process': None,
                'restart_delay': 5,
                'max_restarts': 5,
                'restart_count': 0
            },
            'node': {
                'url': 'http://localhost:3000/health',
                'port': 3000,
                'command': ['node', 'api/index.js'],
                'process': None,
                'restart_delay': 5,
                'max_restarts': 5,
                'restart_count': 0
            },
            'manager': {
                'url': 'http://localhost:9000/health',
                'port': 9000,
                'command': ['python', 'server.py'],
                'process': None,
                'restart_delay': 5,
                'max_restarts': 5,
                'restart_count': 0
            }
        }
        self.running = True
        self.check_interval = 10  # segundos

    def is_port_in_use(self, port: int) -> bool:
        """Verifica se uma porta está em uso"""
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port:
                    return True
            return False
        except Exception:
            return False

    def check_service_health(self, service_name: str) -> bool:
        """Verifica se um serviço está saudável via HTTP"""
        service = self.services[service_name]
        
        try:
            response = requests.get(service['url'], timeout=5)
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            logger.warning(f"Serviço {service_name} não responde em {service['url']}")
            return False
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout ao verificar serviço {service_name}")
            return False
        except Exception as e:
            logger.error(f"Erro ao verificar serviço {service_name}: {e}")
            return False

    def is_process_running(self, service_name: str) -> bool:
        """Verifica se o processo de um serviço está rodando"""
        service = self.services[service_name]
        process = service['process']
        
        if process is None:
            return False
        
        try:
            # Verifica se o processo ainda existe e está rodando
            return process.poll() is None
        except Exception:
            return False

    def start_service(self, service_name: str) -> bool:
        """Inicia um serviço"""
        service = self.services[service_name]
        
        if service['restart_count'] >= service['max_restarts']:
            logger.error(f"Número máximo de restarts atingido para {service_name}")
            return False
        
        try:
            # Verifica se a porta está em uso antes de iniciar
            if self.is_port_in_use(service['port']):
                logger.warning(f"Porta {service['port']} já está em uso para {service_name}")
                # Tenta matar o processo usando a porta
                self.kill_process_on_port(service['port'])
                time.sleep(2)
            
            logger.info(f"Iniciando serviço {service_name}...")
            process = subprocess.Popen(
                service['command'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd(),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            service['process'] = process
            service['restart_count'] += 1
            
            # Aguarda um pouco para o serviço iniciar
            time.sleep(service['restart_delay'])
            
            # Verifica se o processo está rodando
            if self.is_process_running(service_name):
                logger.info(f"✅ Serviço {service_name} iniciado com PID {process.pid}")
                return True
            else:
                logger.error(f"❌ Falha ao iniciar serviço {service_name}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao iniciar serviço {service_name}: {e}")
            return False

    def stop_service(self, service_name: str) -> bool:
        """Para um serviço"""
        service = self.services[service_name]
        process = service['process']
        
        if process is None:
            return True
        
        try:
            logger.info(f"Parando serviço {service_name} (PID {process.pid})...")
            
            # Tenta parar gentilmente primeiro
            process.terminate()
            
            # Aguarda um pouco
            time.sleep(3)
            
            # Se ainda estiver rodando, força
            if process.poll() is None:
                process.kill()
                time.sleep(1)
            
            service['process'] = None
            logger.info(f"✅ Serviço {service_name} parado")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao parar serviço {service_name}: {e}")
            return False

    def kill_process_on_port(self, port: int):
        """Mata processo usando uma porta específica"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'connections']):
                try:
                    for conn in proc.info['connections'] or []:
                        if conn.laddr.port == port:
                            logger.info(f"Matar processo PID {proc.info['pid']} usando porta {port}")
                            proc.kill()
                            time.sleep(1)
                            return
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Erro ao matar processo na porta {port}: {e}")

    def restart_service(self, service_name: str) -> bool:
        """Reinicia um serviço"""
        logger.info(f"Reiniciando serviço {service_name}...")
        
        # Para o serviço
        self.stop_service(service_name)
        
        # Aguarda um pouco
        time.sleep(2)
        
        # Inicia o serviço
        return self.start_service(service_name)

    def monitor_service(self, service_name: str):
        """Monitora e gerencia um serviço específico"""
        service = self.services[service_name]
        
        # Verifica saúde do serviço
        if not self.check_service_health(service_name):
            logger.warning(f"❌ Serviço {service_name} está offline!")
            
            # Tenta reiniciar
            if self.restart_service(service_name):
                logger.info(f"✅ Serviço {service_name} reiniciado com sucesso")
                # Reseta contador de restarts após sucesso
                service['restart_count'] = 0
            else:
                logger.error(f"❌ Falha ao reiniciar serviço {service_name}")
        else:
            logger.info(f"✅ Serviço {service_name} está online")

    async def monitor_all_services(self):
        """Monitora todos os serviços"""
        logger.info("🔍 Iniciando monitoramento dos serviços...")
        
        while self.running:
            try:
                for service_name in self.services.keys():
                    if not self.running:
                        break
                    
                    self.monitor_service(service_name)
                    time.sleep(2)  # Pequena pausa entre verificações
                
                # Aguarda próximo ciclo
                await asyncio.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("Monitoramento interrompido pelo usuário")
                break
            except Exception as e:
                logger.error(f"Erro no monitoramento: {e}")
                await asyncio.sleep(5)

    def stop_all_services(self):
        """Para todos os serviços"""
        logger.info("Parando todos os serviços...")
        self.running = False
        
        for service_name in self.services.keys():
            self.stop_service(service_name)

    def signal_handler(self, signum, frame):
        """Manipulador de sinais para shutdown gracioso"""
        logger.info("Recebido sinal de shutdown...")
        self.stop_all_services()
        sys.exit(0)

async def main():
    """Função principal"""
    monitor = ServiceMonitor()
    
    # Configura handlers de sinais
    signal.signal(signal.SIGINT, monitor.signal_handler)
    signal.signal(signal.SIGTERM, monitor.signal_handler)
    
    try:
        # Inicia todos os serviços se não estiverem rodando
        for service_name in monitor.services.keys():
            if not monitor.check_service_health(service_name):
                monitor.start_service(service_name)
            else:
                logger.info(f"✅ Serviço {service_name} já está rodando")
        
        # Inicia monitoramento
        await monitor.monitor_all_services()
        
    except KeyboardInterrupt:
        logger.info("Programa interrompido")
    finally:
        monitor.stop_all_services()

if __name__ == "__main__":
    asyncio.run(main())

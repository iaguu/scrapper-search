#!/usr/bin/env python3
"""
Script de teste para iniciar serviços individualmente e diagnosticar problemas
"""

import subprocess
import sys
import os
import time
import requests
from pathlib import Path

def test_service(port, name, url_path="/health"):
    """Testa se serviço está respondendo na porta"""
    try:
        response = requests.get(f"http://localhost:{port}{url_path}", timeout=5)
        if response.status_code == 200:
            print(f"✅ {name} está respondendo na porta {port}")
            return True
        else:
            print(f"❌ {name} respondeu com status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {name} não está respondendo: {e}")
        return False

def start_python_service():
    """Inicia serviço Python"""
    print("\n🐍 Iniciando serviço Python...")
    
    # Verificar se já está rodando
    if test_service(8001, "Python"):
        print("Serviço Python já está rodando")
        return True
    
    # Iniciar serviço
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "main:app", 
        "--host", "0.0.0.0", 
        "--port", "8001",
        "--log-level", "info"
    ]
    
    working_dir = Path(__file__).parent / "telegram_service"
    
    try:
        process = subprocess.Popen(
            cmd,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print(f"Processo Python iniciado com PID: {process.pid}")
        
        # Aguardar serviço iniciar
        for i in range(30):
            time.sleep(1)
            if test_service(8001, "Python"):
                print(f"✅ Serviço Python iniciado com sucesso após {i+1}s")
                return True
            print(f"Aguardando serviço Python... ({i+1}/30)")
        
        print("❌ Serviço Python não iniciou após 30 segundos")
        return False
        
    except Exception as e:
        print(f"❌ Erro ao iniciar serviço Python: {e}")
        return False

def start_node_service():
    """Inicia serviço Node.js"""
    print("\n🟢 Iniciando serviço Node.js...")
    
    # Verificar se já está rodando
    if test_service(3000, "Node.js"):
        print("Serviço Node.js já está rodando")
        return True
    
    # Iniciar serviço
    cmd = ["node", "index.js"]
    working_dir = Path(__file__).parent / "api"
    
    try:
        process = subprocess.Popen(
            cmd,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print(f"Processo Node.js iniciado com PID: {process.pid}")
        
        # Aguardar serviço iniciar
        for i in range(30):
            time.sleep(1)
            if test_service(3000, "Node.js"):
                print(f"✅ Serviço Node.js iniciado com sucesso após {i+1}s")
                return True
            print(f"Aguardando serviço Node.js... ({i+1}/30)")
        
        print("❌ Serviço Node.js não iniciou após 30 segundos")
        return False
        
    except Exception as e:
        print(f"❌ Erro ao iniciar serviço Node.js: {e}")
        return False

def main():
    """Função principal"""
    print("🔧 Telegram Bridge - Diagnóstico e Inicialização")
    print("=" * 50)
    
    # Verificar arquivos necessários
    python_main = Path(__file__).parent / "telegram_service" / "main.py"
    node_index = Path(__file__).parent / "api" / "index.js"
    
    if not python_main.exists():
        print(f"❌ Arquivo não encontrado: {python_main}")
        return False
    
    if not node_index.exists():
        print(f"❌ Arquivo não encontrado: {node_index}")
        return False
    
    # Iniciar serviços
    python_ok = start_python_service()
    node_ok = start_node_service()
    
    print("\n📊 Resumo:")
    print(f"Python Service: {'✅ OK' if python_ok else '❌ Falha'}")
    print(f"Node.js Service: {'✅ OK' if node_ok else '❌ Falha'}")
    
    if python_ok and node_ok:
        print("\n🎉 Todos os serviços estão funcionando!")
        print("Acesse o dashboard em: http://localhost:9000")
        return True
    else:
        print("\n⚠️ Alguns serviços não estão funcionando corretamente")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Demo de Descoberta de Comandos e Fluxos
Simula o comportamento do Telegram para testar o sistema
"""

import asyncio
import json
import time
import random
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
from typing import Dict, List, Optional, Any

app = FastAPI(title="Demo Discovery System", version="1.0.0")

# Simulações de respostas baseadas em comandos reais
COMMAND_RESPONSES = {
    "/cpf": {
        "initial": "🔍 CONSULTA CPF - @Kurt\\n\\n🆔 CPF: `{cpf}`\\n\\n👇 Selecione a base de dados:\\n\\n📊 Simples: Dados básicos e essenciais.\\n💎 Completa: Relatório detalhado com fotos, vazamentos e vínculos.",
        "buttons": ["📊 Simples", "💎 Completa"],
        "complete_response": "💎 RESULTADO DATAFLOW VIP\\n━━━━━━━━━━━━━━━━━━━━━━\\n👤 Nome: {nome}\\n🆔 CPF: {cpf}\\n📅 Nasc: {nascimento}\\n👩 Mãe: {mae}\\n\\n📊 DADOS ENCONTRADOS:\\n📱 {telefones} Telefones\\n📧 {emails} Emails\\n📍 {enderecos} Endereços\\n🔐 {vazadas} Credenciais Vazadas\\n🚗 {veiculos} Veículos\\n👨‍👩‍👧 {parentes} Parentes\\n\\n⚠️ Resultado muito extenso!\\nClique abaixo para ver o relatório completo.\\n\\n\\n✅ Relatório enviado para o privado de [.](tg://user?id=7707215591)!",
        "final_buttons": ["VER RELATÓRIO COMPLETO"],
        "full_report": "📋 **RELATÓRIO COMPLETO**\\n\\n**DADOS PESSOAIS**\\n👤 Nome: {nome}\\n🆔 CPF: {cpf}\\n📅 Nascimento: {nascimento}\\n👩 Mãe: {mae}\\n\\n**CONTATOS**\\n📱 Telefones: {telefones}\\n📧 Emails: {emails}\\n\\n**ENDEREÇOS**\\n📍 Endereços: {enderecos}\\n\\n**OUTROS DADOS**\\n🔐 Credenciais Vazadas: {vazadas}\\n🚗 Veículos: {veiculos}\\n👨‍👩‍👧 Parentes: {parentes}"
    },
    "/telefone": {
        "initial": "📱 CONSULTA TELEFONE - @Kurt\\n\\n📞 Telefone: `{telefone}`\\n\\n👇 Selecione a base de dados:\\n\\n📊 Simples: Dados básicos.\\n💎 Completa: Dados completos com vínculos.",
        "buttons": ["📊 Simples", "💎 Completa"],
        "complete_response": "💎 RESULTADO TELEFONE DATAFLOW\\n━━━━━━━━━━━━━━━━━━━━━━\\n📱 Telefone: {telefone}\\n📡 Operadora: {operadora}\\n📋 Tipo: {tipo}\\n✅ Status: {status}\\n\\n👤 Nome: {nome}\\n🆔 CPF: {cpf}",
        "final_buttons": ["VER DETALHES COMPLETOS"],
        "full_report": "📋 **RELATÓRIO TELEFÔNICO COMPLETO**\\n\\n**DADOS DA LINHA**\\n📱 Telefone: {telefone}\\n📡 Operadora: {operadora}\\n📋 Tipo: {tipo}\\n✅ Status: {status}\\n\\n**DADOS DO PROPRIETÁRIO**\\n👤 Nome: {nome}\\n🆔 CPF: {cpf}"
    },
    "/placa": {
        "initial": "🚗 CONSULTA PLACA - @Kurt\\n\\n🚙 Placa: `{placa}`\\n\\n👇 Selecione a base de dados:\\n\\n📊 Simples: Dados básicos.\\n💎 Completa: Dados completos com multas.",
        "buttons": ["📊 Simples", "💎 Completa"],
        "complete_response": "💎 RESULTADO VEÍCULO DATAFLOW\\n━━━━━━━━━━━━━━━━━━━━━━\\n🚗 Placa: {placa}\\n🏭 Marca: {marca}\\n🚙 Modelo: {modelo}\\n🎨 Cor: {cor}\\n📅 Ano: {ano}\\n✅ Situação: {situacao}",
        "final_buttons": ["VER HISTÓRICO COMPLETO"],
        "full_report": "📋 **RELATÓRIO VEICULAR COMPLETO**\\n\\n**DADOS DO VEÍCULO**\\n🚗 Placa: {placa}\\n🏭 Marca: {marca}\\n🚙 Modelo: {modelo}\\n🎨 Cor: {cor}\\n📅 Ano: {ano}\\n✅ Situação: {situacao}"
    },
    "/nome": {
        "initial": "👤 CONSULTA NOME - @Kurt\\n\\n🔍 Nome: `{nome}`\\n\\n👇 Selecione a base de dados:\\n\\n📊 Simples: Dados básicos.\\n💎 Completa: Dados completos com endereços.",
        "buttons": ["📊 Simples", "💎 Completa"],
        "complete_response": "💎 RESULTADO NOME DATAFLOW\\n━━━━━━━━━━━━━━━━━━━━━━\\n👤 Nome: {nome}\\n🆔 CPF: {cpf}\\n📅 Idade: {idade}\\n📍 Cidade: {cidade}",
        "final_buttons": ["VER ENDEREÇOS COMPLETOS"],
        "full_report": "📋 **RELATÓRIO PESSOAL COMPLETO**\\n\\n**DADOS PESSOAIS**\\n👤 Nome: {nome}\\n🆔 CPF: {cpf}\\n📅 Idade: {idade}\\n📍 Cidade: {cidade}"
    }
}

# Dados mock para preenchimento
MOCK_DATA = {
    "cpf": ["123.456.789-00", "987.654.321-00", "456.789.123-00"],
    "nome": ["João Silva", "Maria Santos", "Pedro Oliveira"],
    "nascimento": ["15/03/1985", "22/07/1990", "08/12/1978"],
    "mae": ["Ana Silva", "Maria Santos", "Pedro Oliveira"],
    "telefones": [2, 3, 4],
    "emails": [1, 2, 3],
    "enderecos": [1, 2, 3],
    "vazadas": [0, 2, 5],
    "veiculos": [0, 1, 2],
    "parentes": [5, 12, 19],
    "telefone": ["(11) 98765-4321", "(21) 12345-6789", "(31) 55555-4444"],
    "operadora": ["Vivo", "Claro", "TIM"],
    "tipo": ["Móvel", "Fixo"],
    "status": ["Ativo", "Suspenso", "Cancelado"],
    "placa": ["ABC1234", "XYZ5678", "DEF9012"],
    "marca": ["Volkswagen", "Chevrolet", "Ford"],
    "modelo": ["Gol", "Onix", "Ka"],
    "cor": ["Branco", "Preto", "Prata"],
    "ano": ["2020", "2021", "2022"],
    "situacao": ["Regular", "Irregular", "Licenciado"],
    "idade": ["38 anos", "32 anos", "45 anos"],
    "cidade": ["São Paulo", "Rio de Janeiro", "Belo Horizonte"]
}

class CommandRequest(BaseModel):
    command: str
    timeout: int = 30
    auto_click_buttons: bool = True

class DiscoveryRequest(BaseModel):
    discover_all: bool = True

class CommandResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None

def get_command_type(command: str) -> str:
    """Identifica o tipo de comando"""
    for cmd_type in COMMAND_RESPONSES.keys():
        if command.startswith(cmd_type):
            return cmd_type
    return "unknown"

def get_mock_value(key: str) -> str:
    """Retorna um valor mock aleatório"""
    values = MOCK_DATA.get(key, ["N/A"])
    return random.choice(values)

def format_response(template: str, command_type: str) -> str:
    """Formata a resposta com dados mock"""
    if command_type == "/cpf":
        return template.format(
            cpf=get_mock_value("cpf"),
            nome=get_mock_value("nome"),
            nascimento=get_mock_value("nascimento"),
            mae=get_mock_value("mae"),
            telefones=get_mock_value("telefones"),
            emails=get_mock_value("emails"),
            enderecos=get_mock_value("enderecos"),
            vazadas=get_mock_value("vazadas"),
            veiculos=get_mock_value("veiculos"),
            parentes=get_mock_value("parentes")
        )
    elif command_type == "/telefone":
        return template.format(
            telefone=get_mock_value("telefone"),
            operadora=get_mock_value("operadora"),
            tipo=get_mock_value("tipo"),
            status=get_mock_value("status"),
            nome=get_mock_value("nome"),
            cpf=get_mock_value("cpf")
        )
    elif command_type == "/placa":
        return template.format(
            placa=get_mock_value("placa"),
            marca=get_mock_value("marca"),
            modelo=get_mock_value("modelo"),
            cor=get_mock_value("cor"),
            ano=get_mock_value("ano"),
            situacao=get_mock_value("situacao")
        )
    elif command_type == "/nome":
        return template.format(
            nome=get_mock_value("nome"),
            cpf=get_mock_value("cpf"),
            idade=get_mock_value("idade"),
            cidade=get_mock_value("cidade")
        )
    return template

def scrape_data(text: str, command_type: str) -> Dict[str, Any]:
    """Extrai dados estruturados do texto"""
    import re
    
    patterns = {
        "/cpf": {
            'nome': r'👤\s*Nome:\s*([^\n]+)',
            'cpf': r'🆔\s*CPF:\s*([^\n]+)',
            'nascimento': r'📅\s*Nasc:\s*([^\n]+)',
            'mae': r'👩\s*Mãe:\s*([^\n]+)',
            'telefones': r'📱\s*(\d+)\s*Telefones?',
            'emails': r'📧\s*(\d+)\s*Emails?',
            'enderecos': r'📍\s*(\d+)\s*Endereços?',
            'vazadas': r'🔐\s*(\d+)\s*Credenciais Vazadas?',
            'veiculos': r'🚗\s*(\d+)\s*Veículos?',
            'parentes': r'👨‍👩‍👧\s*(\d+)\s*Parentes?'
        },
        "/telefone": {
            'telefone': r'📱\s*Telefone:\s*([^\n]+)',
            'operadora': r'📡\s*Operadora:\s*([^\n]+)',
            'tipo': r'📋\s*Tipo:\s*([^\n]+)',
            'status': r'✅\s*Status:\s*([^\n]+)',
            'nome': r'👤\s*Nome:\s*([^\n]+)',
            'cpf': r'🆔\s*CPF:\s*([^\n]+)'
        },
        "/placa": {
            'placa': r'🚗\s*Placa:\s*([^\n]+)',
            'marca': r'🏭\s*Marca:\s*([^\n]+)',
            'modelo': r'🚙\s*Modelo:\s*([^\n]+)',
            'cor': r'🎨\s*Cor:\s*([^\n]+)',
            'ano': r'📅\s*Ano:\s*([^\n]+)',
            'situacao': r'✅\s*Situação:\s*([^\n]+)'
        }
    }
    
    if command_type not in patterns:
        return {
            'raw_text': text,
            'command_type': command_type,
            'scraped_data': {}
        }
    
    command_patterns = patterns[command_type]
    scraped_data = {}
    
    try:
        for field, pattern in command_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if field in ['telefones', 'emails', 'enderecos', 'vazadas', 'veiculos', 'parentes']:
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                scraped_data[field] = value
        
        return {
            'raw_text': text,
            'command_type': command_type,
            'scraped_data': scraped_data,
            'success': True
        }
        
    except Exception as e:
        return {
            'raw_text': text,
            'command_type': command_type,
            'scraped_data': {},
            'error': str(e),
            'success': False
        }

async def simulate_command_flow(command: str, auto_click_buttons: bool = True) -> Dict[str, Any]:
    """Simula o fluxo completo de um comando"""
    start_time = time.time()
    command_type = get_command_type(command)
    
    result = {
        'command': command,
        'command_type': command_type,
        'success': False,
        'steps': [],
        'final_data': None,
        'error': None
    }
    
    try:
        if command_type == "unknown":
            result['error'] = f"Comando não reconhecido: {command}"
            return result
        
        # Passo 1: Envia comando e recebe resposta inicial
        await asyncio.sleep(random.uniform(1, 2))
        initial_response = COMMAND_RESPONSES[command_type]["initial"]
        
        # Substitui placeholders na resposta inicial
        if command_type == "/cpf":
            cpf = command.split()[-1] if len(command.split()) > 1 else get_mock_value("cpf")
            initial_response = initial_response.replace("{cpf}", cpf)
        elif command_type == "/telefone":
            telefone = command.split()[-1] if len(command.split()) > 1 else get_mock_value("telefone")
            initial_response = initial_response.replace("{telefone}", telefone)
        elif command_type == "/placa":
            placa = command.split()[-1] if len(command.split()) > 1 else get_mock_value("placa")
            initial_response = initial_response.replace("{placa}", placa)
        elif command_type == "/nome":
            nome = " ".join(command.split()[1:]) if len(command.split()) > 1 else get_mock_value("nome")
            initial_response = initial_response.replace("{nome}", nome)
        
        result['steps'].append({
            'action': 'send_command',
            'status': 'success',
            'message': 'Comando enviado',
            'response': initial_response,
            'buttons': COMMAND_RESPONSES[command_type]["buttons"]
        })
        
        if not auto_click_buttons:
            result['success'] = True
            result['final_data'] = {
                'response_text': initial_response,
                'buttons_found': COMMAND_RESPONSES[command_type]["buttons"]
            }
            return result
        
        # Passo 2: Clica no botão "Completa"
        await asyncio.sleep(random.uniform(1, 2))
        complete_response = format_response(COMMAND_RESPONSES[command_type]["complete_response"], command_type)
        
        result['steps'].append({
            'action': 'click_button',
            'button': '💎 Completa',
            'status': 'success',
            'message': 'Botão "Completa" clicado',
            'response': complete_response,
            'buttons': COMMAND_RESPONSES[command_type].get("final_buttons", [])
        })
        
        # Passo 3: Clica no botão final (VER RELATÓRIO, etc.)
        if COMMAND_RESPONSES[command_type].get("final_buttons"):
            await asyncio.sleep(random.uniform(1, 2))
            final_response = format_response(COMMAND_RESPONSES[command_type]["full_report"], command_type)
            
            result['steps'].append({
                'action': 'click_button',
                'button': COMMAND_RESPONSES[command_type]["final_buttons"][0],
                'status': 'success',
                'message': 'Botão final clicado',
                'response': final_response
            })
            
            # Faz scraping dos dados finais
            scraped_data = scrape_data(final_response, command_type)
            
            result['final_data'] = {
                'response_text': final_response,
                'scraped_data': scraped_data,
                'timestamp': time.time()
            }
        
        result['success'] = True
        result['processing_time'] = time.time() - start_time
        
    except Exception as e:
        result['error'] = str(e)
        result['processing_time'] = time.time() - start_time
    
    return result

@app.post("/send-command", response_model=CommandResponse)
async def send_command(request: CommandRequest):
    """Processa um comando simulado"""
    result = await simulate_command_flow(request.command, request.auto_click_buttons)
    
    return CommandResponse(
        success=result['success'],
        data=result,
        processing_time=result.get('processing_time', 0)
    )

@app.post("/discover-commands")
async def discover_commands(request: DiscoveryRequest):
    """Descobre todos os padrões de comandos"""
    discovery_results = {}
    
    test_commands = [
        "/cpf 123.456.789-00",
        "/telefone (11) 98765-4321",
        "/placa ABC1234",
        "/nome João Silva"
    ]
    
    for command in test_commands:
        result = await simulate_command_flow(command, auto_click_buttons=True)
        discovery_results[command] = result
    
    # Gera configuração de padrões
    config = {
        "discovery_timestamp": time.time(),
        "commands_tested": list(discovery_results.keys()),
        "button_patterns": {
            "initial_buttons": ["📊 Simples", "💎 Completa"],
            "final_buttons": ["VER RELATÓRIO COMPLETO", "VER DETALHES COMPLETOS", "VER HISTÓRICO COMPLETO", "VER ENDEREÇOS COMPLETOS"]
        },
        "recommended_flows": {}
    }
    
    for command_type in COMMAND_RESPONSES.keys():
        config["recommended_flows"][command_type] = {
            'initial_buttons': COMMAND_RESPONSES[command_type]["buttons"],
            'button_sequence': ['💎 Completa'] + COMMAND_RESPONSES[command_type].get("final_buttons", []),
            'final_actions': COMMAND_RESPONSES[command_type].get("final_buttons", [])
        }
    
    return {
        "success": True,
        "message": "Descoberta concluída",
        "discovery_results": discovery_results,
        "config": config
    }

@app.post("/test-all-commands")
async def test_all_commands():
    """Testa todos os comandos conhecidos"""
    test_commands = [
        "/cpf 123.456.789-00",
        "/telefone (11) 98765-4321",
        "/placa ABC1234",
        "/nome João Silva",
        "/email joao@email.com",
        "/cep 01310-100",
        "/cnpj 12.345.678/0001-90"
    ]
    
    results = {}
    successful = 0
    failed = 0
    
    for command in test_commands:
        result = await simulate_command_flow(command, auto_click_buttons=True)
        results[command] = result
        
        if result['success']:
            successful += 1
        else:
            failed += 1
    
    return {
        "success": True,
        "message": f"Testados {len(test_commands)} comandos",
        "results": results,
        "summary": {
            "total_commands": len(test_commands),
            "successful": successful,
            "failed": failed
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "OK",
        "mode": "demo",
        "features": {
            "command_simulation": True,
            "button_discovery": True,
            "data_scraping": True,
            "pattern_recognition": True
        }
    }

@app.get("/")
async def root():
    return {
        "service": "Demo Discovery System v1.0.0",
        "description": "Sistema de demonstração para descoberta de padrões de comandos Telegram",
        "features": [
            "🔍 Descoberta Automática de Comandos",
            "🔘 Simulação de Cliques em Botões",
            "📊 Extração Estruturada de Dados",
            "🧪 Testes em Lote",
            "📋 Análise de Padrões"
        ],
        "endpoints": {
            "send_command": "POST /send-command",
            "discover_commands": "POST /discover-commands",
            "test_all_commands": "POST /test-all-commands",
            "health": "GET /health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

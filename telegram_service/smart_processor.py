#!/usr/bin/env python3
"""
Processador Inteligente de Comandos Telegram
Baseado nos padrões descobertos, processa automaticamente qualquer comando
"""

import asyncio
import json
import time
import re
from typing import Dict, List, Optional, Any
from telethon import TelegramClient
from telethon.events import NewMessage, CallbackQuery
import os
from dotenv import load_dotenv

load_dotenv()

class SmartTelegramProcessor:
    def __init__(self):
        self.API_ID = int(os.getenv('API_ID', '0'))
        self.API_HASH = os.getenv('API_HASH', '')
        self.CHAT_ID = int(os.getenv('CHAT_ID', '0'))
        self.PHONE_NUMBER = os.getenv('PHONE_NUMBER', '')
        
        self.client = None
        self.discovery_config = None
        self.load_discovery_config()
        
        # Padrões de scraping baseados nos testes
        self.scraping_patterns = {
            'cpf': {
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
            'telefone': {
                'numero': r'📱\s*Telefone:\s*([^\n]+)',
                'operadora': r'📡\s*Operadora:\s*([^\n]+)',
                'tipo': r'📋\s*Tipo:\s*([^\n]+)',
                'status': r'✅\s*Status:\s*([^\n]+)'
            },
            'placa': {
                'placa': r'🚗\s*Placa:\s*([^\n]+)',
                'modelo': r'🚙\s*Modelo:\s*([^\n]+)',
                'marca': r'🏭\s*Marca:\s*([^\n]+)',
                'cor': r'🎨\s*Cor:\s*([^\n]+)',
                'ano': r'📅\s*Ano:\s*([^\n]+)',
                'situacao': r'✅\s*Situação:\s*([^\n]+)'
            },
            'nome': {
                'nome': r'👤\s*Nome:\s*([^\n]+)',
                'cpf': r'🆔\s*CPF:\s*([^\n]+)',
                'idade': r'📅\s*Idade:\s*([^\n]+)',
                'cidade': r'📍\s*Cidade:\s*([^\n]+)'
            },
            'email': {
                'email': r'📧\s*Email:\s*([^\n]+)',
                'validacao': r'✅\s*Validação:\s*([^\n]+)',
                'provedor': r'🌐\s*Provedor:\s*([^\n]+)',
                'risco': r'⚠️\s*Risco:\s*([^\n]+)'
            },
            'cep': {
                'cep': r'📍\s*CEP:\s*([^\n]+)',
                'endereco': r'🏠\s*Endereço:\s*([^\n]+)',
                'bairro': r'🏘️\s*Bairro:\s*([^\n]+)',
                'cidade': r'🏙️\s*Cidade:\s*([^\n]+)',
                'estado': r'🗺️\s*Estado:\s*([^\n]+)'
            },
            'cnpj': {
                'cnpj': r'🏢\s*CNPJ:\s*([^\n]+)',
                'razao_social': r'📋\s*Razão Social:\s*([^\n]+)',
                'situacao': r'✅\s*Situação:\s*([^\n]+)',
                'capital': r'💰\s*Capital:\s*([^\n]+)'
            }
        }
    
    def load_discovery_config(self):
        """Carrega configuração da descoberta"""
        try:
            with open('discovery_results.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.discovery_config = data['config']
                print("✅ Configuração de descoberta carregada")
        except FileNotFoundError:
            print("⚠️ Arquivo de descoberta não encontrado, usando configuração padrão")
            self.discovery_config = self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """Configuração padrão caso não tenha descoberta"""
        return {
            "recommended_flows": {
                "/cpf": {
                    "initial_buttons": ["📊 Simples", "💎 Completa"],
                    "button_sequence": ["💎 Completa", "VER RELATÓRIO COMPLETO"],
                    "final_actions": ["VER RELATÓRIO COMPLETO"]
                },
                "/telefone": {
                    "initial_buttons": ["📊 Simples", "💎 Completa"],
                    "button_sequence": ["💎 Completa", "VER RELATÓRIO COMPLETO"],
                    "final_actions": ["VER RELATÓRIO COMPLETO"]
                },
                "/placa": {
                    "initial_buttons": ["📊 Simples", "💎 Completa"],
                    "button_sequence": ["💎 Completa", "VER RELATÓRIO COMPLETO"],
                    "final_actions": ["VER RELATÓRIO COMPLETO"]
                }
            }
        }
    
    async def connect(self):
        """Conecta ao Telegram"""
        try:
            os.makedirs('session', exist_ok=True)
            self.client = TelegramClient('session/smart_processor_session', self.API_ID, self.API_HASH)
            await self.client.start(phone=self.PHONE_NUMBER)
            print("✅ Smart Processor conectado ao Telegram")
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            return False
    
    def get_command_type(self, command: str) -> str:
        """Identifica o tipo de comando"""
        if command.startswith('/cpf'):
            return 'cpf'
        elif command.startswith('/telefone'):
            return 'telefone'
        elif command.startswith('/placa'):
            return 'placa'
        elif command.startswith('/nome'):
            return 'nome'
        elif command.startswith('/email'):
            return 'email'
        elif command.startswith('/cep'):
            return 'cep'
        elif command.startswith('/cnpj'):
            return 'cnpj'
        elif command.startswith('/foto'):
            return 'foto'
        elif command.startswith('/titulo'):
            return 'titulo'
        elif command.startswith('/mae'):
            return 'mae'
        else:
            return 'unknown'
    
    def scrape_data(self, text: str, command_type: str) -> Dict[str, Any]:
        """Extrai dados estruturados do texto baseado no tipo de comando"""
        if command_type not in self.scraping_patterns:
            return {
                'raw_text': text,
                'command_type': command_type,
                'scraped_data': {}
            }
        
        patterns = self.scraping_patterns[command_type]
        scraped_data = {}
        
        try:
            for field, pattern in patterns.items():
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    # Converte números quando aplicável
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
    
    async def process_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Processa um comando usando fluxo inteligente"""
        print(f"\n🔍 Processando comando inteligente: {command}")
        
        result = {
            'command': command,
            'command_type': self.get_command_type(command),
            'success': False,
            'steps': [],
            'final_data': None,
            'error': None
        }
        
        try:
            # Envia o comando
            message = await self.client.send_message(self.CHAT_ID, command)
            result['steps'].append({
                'action': 'send_command',
                'status': 'success',
                'message': f"Comando {command} enviado"
            })
            
            # Espera pela resposta inicial
            await asyncio.sleep(3)
            
            # Procura pela resposta com botões
            initial_response = None
            buttons_found = []
            
            async for msg in self.client.iter_messages(self.CHAT_ID, limit=5):
                if msg.reply_to_msg_id == message.id:
                    initial_response = msg.text
                    if msg.buttons:
                        for row in msg.buttons:
                            for btn in row:
                                buttons_found.append({
                                    'text': btn.text,
                                    'data': getattr(btn, 'data', None)
                                })
                    break
            
            result['steps'].append({
                'action': 'receive_initial_response',
                'status': 'success',
                'message': f"Resposta inicial recebida com {len(buttons_found)} botões",
                'buttons': buttons_found
            })
            
            # Obtém fluxo recomendado
            command_type = result['command_type']
            recommended_flow = self.discovery_config.get('recommended_flows', {}).get(f"/{command_type}", {})
            
            if recommended_flow:
                # Segue o fluxo recomendado
                for button_sequence in recommended_flow.get('button_sequence', []):
                    print(f"🔘 Procurando botão: {button_sequence}")
                    
                    # Reenvia comando se necessário
                    if button_sequence == recommended_flow['button_sequence'][0]:
                        await self.client.send_message(self.CHAT_ID, command)
                        await asyncio.sleep(2)
                    
                    # Procura e clica no botão
                    async for msg in self.client.iter_messages(self.CHAT_ID, limit=5):
                        if msg.reply_to_msg_id and msg.buttons:
                            for row in msg.buttons:
                                for btn in row:
                                    if button_sequence.lower() in btn.text.lower():
                                        print(f"🔘 Clicando em: {btn.text}")
                                        await btn.click()
                                        await asyncio.sleep(3)
                                        
                                        result['steps'].append({
                                            'action': 'click_button',
                                            'status': 'success',
                                            'message': f"Botão '{btn.text}' clicado"
                                        })
                                        
                                        # Verifica se há resposta final
                                        final_response = None
                                        async for response_msg in self.client.iter_messages(self.CHAT_ID, limit=3):
                                            if response_msg.text and not response_msg.buttons:
                                                final_response = response_msg.text
                                                break
                                        
                                        if final_response:
                                            # Faz scraping dos dados
                                            scraped_data = self.scrape_data(final_response, command_type)
                                            
                                            result['final_data'] = {
                                                'response_text': final_response,
                                                'scraped_data': scraped_data,
                                                'timestamp': time.time()
                                            }
                                            
                                            result['steps'].append({
                                                'action': 'scrape_data',
                                                'status': 'success',
                                                'message': f"Dados extraídos: {len(scraped_data.get('scraped_data', {}))} campos"
                                            })
                                            
                                            result['success'] = True
                                            return result
                                        
                                        break
                            break
                        break
            
            # Se não seguiu fluxo, tenta clicar no primeiro botão completo
            for button in buttons_found:
                if "completa" in button['text'].lower() or "completo" in button['text'].lower():
                    print(f"🔘 Clicando no botão completo: {button['text']}")
                    
                    # Reenvia comando
                    await self.client.send_message(self.CHAT_ID, command)
                    await asyncio.sleep(2)
                    
                    # Clica no botão
                    async for msg in self.client.iter_messages(self.CHAT_ID, limit=5):
                        if msg.reply_to_msg_id and msg.buttons:
                            for row in msg.buttons:
                                for btn in row:
                                    if btn.text == button['text']:
                                        await btn.click()
                                        await asyncio.sleep(3)
                                        
                                        # Captura resposta
                                        final_response = None
                                        async for response_msg in self.client.iter_messages(self.CHAT_ID, limit=3):
                                            if response_msg.text and not response_msg.buttons:
                                                final_response = response_msg.text
                                                break
                                        
                                        if final_response:
                                            scraped_data = self.scrape_data(final_response, command_type)
                                            result['final_data'] = {
                                                'response_text': final_response,
                                                'scraped_data': scraped_data,
                                                'timestamp': time.time()
                                            }
                                            result['success'] = True
                                            return result
                                        break
                            break
                    break
            
            result['error'] = "Não foi possível completar o fluxo automaticamente"
            
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ Erro no processamento: {e}")
        
        return result
    
    async def batch_process_commands(self, commands: List[str]) -> Dict[str, Any]:
        """Processa múltiplos comandos em lote"""
        print(f"\n🚀 Processando lote de {len(commands)} comandos")
        
        results = {
            'batch_id': str(int(time.time())),
            'timestamp': time.time(),
            'commands_processed': 0,
            'success_count': 0,
            'error_count': 0,
            'results': {}
        }
        
        for command in commands:
            result = await self.process_command(command)
            results['results'][command] = result
            results['commands_processed'] += 1
            
            if result['success']:
                results['success_count'] += 1
            else:
                results['error_count'] += 1
            
            # Pausa entre comandos
            await asyncio.sleep(2)
        
        return results
    
    async def run_smart_tests(self):
        """Executa testes inteligentes de todos os comandos"""
        print("🧠 INICIANDO PROCESSADOR INTELIGENTE DE COMANDOS")
        print("=" * 60)
        
        if not await self.connect():
            return
        
        try:
            # Comandos para teste
            test_commands = [
                "/cpf 123.456.789-00",
                "/telefone (11) 98765-4321",
                "/placa ABC1234",
                "/nome João Silva",
                "/email joao@email.com",
                "/cep 01310-100",
                "/cnpj 12.345.678/0001-90"
            ]
            
            # Processa em lote
            results = await self.batch_process_commands(test_commands)
            
            # Salva resultados
            with open('smart_processor_results.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print("\n" + "=" * 60)
            print("✅ PROCESSAMENTO INTELIGENTE CONCLUÍDO!")
            print(f"📊 Comandos processados: {results['commands_processed']}")
            print(f"✅ Sucessos: {results['success_count']}")
            print(f"❌ Erros: {results['error_count']}")
            print(f"📄 Resultados salvos em: smart_processor_results.json")
            
            # Mostra resumo
            print("\n📋 RESUMO DOS RESULTADOS:")
            for command, result in results['results'].items():
                status = "✅" if result['success'] else "❌"
                data_count = len(result.get('final_data', {}).get('scraped_data', {}).get('scraped_data', {}))
                print(f"{status} {command} - {data_count} campos extraídos")
            
        except Exception as e:
            print(f"❌ Erro durante o processamento: {e}")
        
        finally:
            if self.client:
                await self.client.disconnect()

async def main():
    processor = SmartTelegramProcessor()
    await processor.run_smart_tests()

if __name__ == "__main__":
    asyncio.run(main())

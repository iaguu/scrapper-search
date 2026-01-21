#!/usr/bin/env python3
"""
Sistema de Descoberta e Teste de Comandos Telegram
Descobre botões, fluxos e extrai informações automaticamente
"""

import asyncio
import json
import time
import re
from typing import Dict, List, Optional, Tuple
from telethon import TelegramClient
from telethon.events import NewMessage, CallbackQuery
import os
from dotenv import load_dotenv

load_dotenv()

class TelegramDiscovery:
    def __init__(self):
        self.API_ID = int(os.getenv('API_ID', '0'))
        self.API_HASH = os.getenv('API_HASH', '')
        self.CHAT_ID = int(os.getenv('CHAT_ID', '0'))
        self.PHONE_NUMBER = os.getenv('PHONE_NUMBER', '')
        
        self.client = None
        self.discovered_commands = {}
        self.button_flows = {}
        self.test_results = {}
        
    async def connect(self):
        """Conecta ao Telegram"""
        try:
            os.makedirs('session', exist_ok=True)
            self.client = TelegramClient('session/discovery_session', self.API_ID, self.API_HASH)
            await self.client.start(phone=self.PHONE_NUMBER)
            print("✅ Conectado ao Telegram com sucesso!")
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            return False
    
    async def test_command(self, command: str) -> Dict:
        """Testa um comando específico e descobre o fluxo"""
        print(f"\n🔍 Testando comando: {command}")
        
        result = {
            'command': command,
            'initial_response': None,
            'buttons_found': [],
            'button_flow': [],
            'final_responses': [],
            'success': False,
            'error': None
        }
        
        try:
            # Envia o comando
            message = await self.client.send_message(self.CHAT_ID, command)
            print(f"📤 Comando enviado: {command}")
            
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
            
            result['initial_response'] = initial_response
            result['buttons_found'] = buttons_found
            
            print(f"📋 Resposta inicial recebida")
            print(f"🔘 Botões encontrados: {len(buttons_found)}")
            
            # Testa cada botão
            for i, button in enumerate(buttons_found):
                print(f"\n🔘 Testando botão {i+1}: {button['text']}")
                
                # Reenvia o comando
                await self.client.send_message(self.CHAT_ID, command)
                await asyncio.sleep(2)
                
                # Procura e clica no botão
                async for msg in self.client.iter_messages(self.CHAT_ID, limit=5):
                    if msg.reply_to_msg_id and msg.buttons:
                        for row in msg.buttons:
                            for btn in row:
                                if btn.text == button['text']:
                                    print(f"🔘 Clicando em: {btn.text}")
                                    await btn.click()
                                    await asyncio.sleep(3)
                                    
                                    # Captura a resposta após o clique
                                    button_response = None
                                    async for response_msg in self.client.iter_messages(self.CHAT_ID, limit=3):
                                        if response_msg.text and not response_msg.buttons:
                                            button_response = response_msg.text
                                            break
                                    
                                    result['button_flow'].append({
                                        'button_text': button['text'],
                                        'button_data': button['data'],
                                        'response': button_response
                                    })
                                    
                                    # Verifica se há novos botões
                                    new_buttons = []
                                    async for new_msg in self.client.iter_messages(self.CHAT_ID, limit=3):
                                        if new_msg.buttons:
                                            for row in new_msg.buttons:
                                                for new_btn in row:
                                                    new_buttons.append({
                                                        'text': new_btn.text,
                                                        'data': getattr(new_btn, 'data', None)
                                                    })
                                    
                                    if new_buttons:
                                        print(f"🔘 Novos botões encontrados: {len(new_buttons)}")
                                        # Testa o primeiro novo botão (geralmente "VER RELATÓRIO COMPLETO")
                                        for new_btn in new_buttons:
                                            if "COMPLETO" in new_btn['text'].upper():
                                                print(f"🔘 Clicando em: {new_btn['text']}")
                                                await new_btn.click()
                                                await asyncio.sleep(3)
                                                
                                                # Captura a resposta final
                                                final_response = None
                                                async for final_msg in self.client.iter_messages(self.CHAT_ID, limit=3):
                                                    if final_msg.text and "RESULTADO" in final_msg.text:
                                                        final_response = final_msg.text
                                                        break
                                                
                                                result['final_responses'].append({
                                                    'button': new_btn['text'],
                                                    'response': final_response
                                                })
                                                break
                                    break
                        break
                    break
            
            result['success'] = True
            print(f"✅ Teste do comando {command} concluído com sucesso!")
            
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ Erro no teste do comando {command}: {e}")
        
        return result
    
    async def discover_all_commands(self) -> Dict:
        """Descobre todos os comandos e seus fluxos"""
        commands_to_test = [
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
        
        print("🚀 Iniciando descoberta de todos os comandos...")
        
        for command in commands_to_test:
            result = await self.test_command(command)
            self.test_results[command] = result
            
            # Pausa entre comandos para não sobrecarregar
            await asyncio.sleep(2)
        
        return self.test_results
    
    def extract_patterns(self) -> Dict:
        """Extrai padrões dos resultados dos testes"""
        patterns = {
            'button_patterns': {},
            'response_patterns': {},
            'command_flows': {}
        }
        
        for command, result in self.test_results.items():
            if result['success']:
                # Analisa padrões de botões
                for button in result['buttons_found']:
                    button_type = self.classify_button(button['text'])
                    if button_type not in patterns['button_patterns']:
                        patterns['button_patterns'][button_type] = []
                    patterns['button_patterns'][button_type].append(button['text'])
                
                # Analisa fluxos de comandos
                command_type = command.split()[0]
                if command_type not in patterns['command_flows']:
                    patterns['command_flows'][command_type] = []
                patterns['command_flows'][command_type].append({
                    'buttons': result['buttons_found'],
                    'flow': result['button_flow'],
                    'final': result['final_responses']
                })
        
        return patterns
    
    def classify_button(self, button_text: str) -> str:
        """Classifica o tipo de botão"""
        text = button_text.lower()
        
        if "simples" in text or "básico" in text:
            return "basic_info"
        elif "completa" in text or "completo" in text:
            return "complete_info"
        elif "privado" in text:
            return "private_send"
        elif "relatório" in text or "relatorio" in text:
            return "report_view"
        elif "baixar" in text or "download" in text:
            return "download"
        elif "resumo" in text:
            return "summary"
        elif "fechar" in text:
            return "close"
        else:
            return "other"
    
    def generate_config(self) -> Dict:
        """Gera configuração baseada nos padrões descobertos"""
        patterns = self.extract_patterns()
        
        config = {
            "discovery_timestamp": time.time(),
            "commands_tested": list(self.test_results.keys()),
            "button_types": patterns['button_patterns'],
            "command_flows": patterns['command_flows'],
            "recommended_flows": {}
        }
        
        # Gera fluxos recomendados para cada tipo de comando
        for command_type, flows in patterns['command_flows'].items():
            if flows:
                # Pega o fluxo mais completo
                complete_flow = max(flows, key=lambda x: len(x['flow']))
                config['recommended_flows'][command_type] = {
                    'initial_buttons': [b['text'] for b in complete_flow['buttons']],
                    'button_sequence': [f['button_text'] for f in complete_flow['flow']],
                    'final_actions': [f['button'] for f in complete_flow['final']]
                }
        
        return config
    
    async def run_discovery(self):
        """Executa o processo completo de descoberta"""
        print("🔍 INICIANDO SISTEMA DE DESCOBERTA TELEGRAM")
        print("=" * 50)
        
        # Conecta ao Telegram
        if not await self.connect():
            return
        
        try:
            # Descobre todos os comandos
            results = await self.discover_all_commands()
            
            # Gera configuração
            config = self.generate_config()
            
            # Salva resultados
            with open('discovery_results.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'test_results': results,
                    'config': config
                }, f, indent=2, ensure_ascii=False)
            
            print("\n" + "=" * 50)
            print("✅ DESCOBERTA CONCLUÍDA!")
            print(f"📊 Comandos testados: {len(results)}")
            print(f"📄 Resultados salvos em: discovery_results.json")
            
            # Mostra resumo
            print("\n📋 RESUMO DOS COMANDOS:")
            for command, result in results.items():
                status = "✅" if result['success'] else "❌"
                buttons = len(result['buttons_found'])
                print(f"{status} {command} - {buttons} botões")
            
            print("\n🔘 PADRÕES DE BOTÕES DESCOBERTOS:")
            for btn_type, buttons in config['button_types'].items():
                print(f"  {btn_type}: {set(buttons)}")
            
        except Exception as e:
            print(f"❌ Erro durante a descoberta: {e}")
        
        finally:
            if self.client:
                await self.client.disconnect()

async def main():
    discovery = TelegramDiscovery()
    await discovery.run_discovery()

if __name__ == "__main__":
    asyncio.run(main())

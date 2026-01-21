#!/usr/bin/env python3
"""
Script de Teste de Conexão para Debug
"""

import asyncio
import requests
import json
import time
from typing import Dict, Any

class ConnectionTester:
    def __init__(self):
        self.services = {
            'python': {'url': 'http://localhost:8000', 'port': 8000},
            'node': {'url': 'http://localhost:3000', 'port': 3000},
            'manager': {'url': 'http://localhost:9000', 'port': 9000}
        }
    
    def test_connection(self, service_name: str) -> Dict[str, Any]:
        """Testa conexão com um serviço"""
        service = self.services[service_name]
        results = {
            'service': service_name,
            'url': service['url'],
            'port': service['port'],
            'timestamp': time.time(),
            'tests': {}
        }
        
        # Teste 1: Porta aberta
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex(('localhost', service['port']))
            sock.close()
            results['tests']['port_open'] = result == 0
        except Exception as e:
            results['tests']['port_open'] = False
            results['tests']['port_error'] = str(e)
        
        # Teste 2: Health Check
        try:
            response = requests.get(f"{service['url']}/health", timeout=5)
            results['tests']['health_check'] = {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text[:200]
            }
        except requests.exceptions.ConnectionError:
            results['tests']['health_check'] = {'success': False, 'error': 'Connection refused'}
        except requests.exceptions.Timeout:
            results['tests']['health_check'] = {'success': False, 'error': 'Timeout'}
        except Exception as e:
            results['tests']['health_check'] = {'success': False, 'error': str(e)}
        
        # Teste 3: API endpoints (se disponível)
        if service_name == 'python':
            try:
                response = requests.post(f"{service['url']}/send-command", 
                                       json={'command': '/test', 'timeout': 5}, 
                                       timeout=5)
                results['tests']['api_endpoint'] = {
                    'success': response.status_code in [200, 400, 500],  # Qualquer resposta válida
                    'status_code': response.status_code,
                    'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text[:200]
                }
            except Exception as e:
                results['tests']['api_endpoint'] = {'success': False, 'error': str(e)}
        
        elif service_name == 'node':
            try:
                response = requests.post(f"{service['url']}/query", 
                                       json={'type': 'cpf', 'query': 'test'}, 
                                       headers={'X-API-Key': 'demo_key_12345'},
                                       timeout=5)
                results['tests']['api_endpoint'] = {
                    'success': response.status_code in [200, 400, 401, 503],  # Qualquer resposta válida
                    'status_code': response.status_code,
                    'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text[:200]
                }
            except Exception as e:
                results['tests']['api_endpoint'] = {'success': False, 'error': str(e)}
        
        return results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Executa todos os testes"""
        print("🔍 Iniciando testes de conexão...")
        print("=" * 60)
        
        all_results = {
            'timestamp': time.time(),
            'services': {}
        }
        
        for service_name in self.services.keys():
            print(f"\n📋 Testando serviço: {service_name.upper()}")
            print("-" * 40)
            
            results = self.test_connection(service_name)
            all_results['services'][service_name] = results
            
            # Exibe resultados
            for test_name, test_result in results['tests'].items():
                if isinstance(test_result, dict) and test_result.get('success', False):
                    print(f"✅ {test_name}: OK")
                    if 'status_code' in test_result:
                        print(f"   Status: {test_result['status_code']}")
                elif isinstance(test_result, bool) and test_result:
                    print(f"✅ {test_name}: OK")
                else:
                    print(f"❌ {test_name}: FALHA")
                    if isinstance(test_result, dict) and 'error' in test_result:
                        print(f"   Erro: {test_result['error']}")
        
        return all_results
    
    def test_dashboard_integration(self) -> Dict[str, Any]:
        """Testa integração completa com dashboard"""
        print("\n🌐 Testando integração com Dashboard...")
        print("=" * 60)
        
        results = {
            'timestamp': time.time(),
            'tests': {}
        }
        
        # Teste 1: Verifica se todos os serviços estão online
        all_online = True
        for service_name in self.services.keys():
            test_result = self.test_connection(service_name)
            is_online = test_result['tests'].get('health_check', {}).get('success', False)
            results['tests'][f'{service_name}_online'] = is_online
            if not is_online:
                all_online = False
        
        results['tests']['all_services_online'] = all_online
        
        # Teste 2: Teste de fluxo completo (se todos online)
        if all_online:
            try:
                # Simula requisição da dashboard
                print("\n🔄 Testando fluxo completo: Dashboard -> Node -> Python")
                
                # Testa API Node
                node_response = requests.post(
                    'http://localhost:3000/query',
                    json={'type': 'cpf', 'query': '12345678901'},
                    headers={'X-API-Key': 'demo_key_12345'},
                    timeout=10
                )
                
                results['tests']['complete_flow'] = {
                    'success': node_response.status_code == 200,
                    'node_response': node_response.json() if node_response.headers.get('content-type', '').startswith('application/json') else node_response.text[:200]
                }
                
                if node_response.status_code == 200:
                    print("✅ Fluxo completo funcionando!")
                else:
                    print(f"⚠️ Fluxo completo com problemas: Status {node_response.status_code}")
                    
            except Exception as e:
                results['tests']['complete_flow'] = {'success': False, 'error': str(e)}
                print(f"❌ Erro no fluxo completo: {e}")
        else:
            results['tests']['complete_flow'] = {'success': False, 'error': 'Serviços não estão todos online'}
            print("⚠️ Fluxo completo não testado: serviços offline")
        
        return results

def main():
    """Função principal"""
    tester = ConnectionTester()
    
    # Testa todos os serviços
    service_results = tester.run_all_tests()
    
    # Testa integração
    integration_results = tester.test_dashboard_integration()
    
    # Salva resultados
    all_results = {
        'service_tests': service_results,
        'integration_tests': integration_results
    }
    
    with open('connection_test_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print("\n📊 Resultados salvos em 'connection_test_results.json'")
    print("\n🎯 Resumo:")
    
    # Resumo final
    total_services = len(tester.services)
    online_services = sum(1 for s in tester.services.keys() 
                         if service_results['services'][s]['tests'].get('health_check', {}).get('success', False))
    
    print(f"   Serviços online: {online_services}/{total_services}")
    print(f"   Integração dashboard: {'✅ OK' if integration_results['tests'].get('complete_flow', {}).get('success', False) else '❌ Falha'}")

if __name__ == "__main__":
    main()

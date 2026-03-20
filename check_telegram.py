import requests

# Verificar status do serviço Python e Telegram
print("🔍 Verificando status do serviço Python...")

try:
    # Health check do serviço Python
    print("📊 1. Health Check do Python Service...")
    health_response = requests.get('http://localhost:8001/health', timeout=5)
    print(f"   Status: {health_response.status_code}")
    if health_response.status_code == 200:
        health_data = health_response.json()
        print(f"   Telegram conectado: {health_data.get('telegram_connected', False)}")
        print(f"   Cliente disponível: {health_data.get('telegram_client_available', False)}")
        print(f"   API ID configurado: {health_data.get('api_id_configured', False)}")
        print(f"   API Hash configurado: {health_data.get('api_hash_configured', False)}")
        print(f"   Chat ID configurado: {health_data.get('chat_id_configured', False)}")
        print(f"   Phone configurado: {health_data.get('phone_configured', False)}")
    
    # Auth status
    print("\n📋 2. Auth Status...")
    auth_response = requests.get('http://localhost:8001/auth-status', timeout=5)
    print(f"   Status: {auth_response.status_code}")
    if auth_response.status_code == 200:
        auth_data = auth_response.json()
        print(f"   Conectado: {auth_data.get('connected', False)}")
        print(f"   Erro: {auth_data.get('error', 'N/A')}")
        print(f"   Detalhes: {auth_data.get('details', 'N/A')}")
    
    # Verificar se o serviço está realmente rodando
    print("\n🔍 3. Verificando se o serviço está rodando...")
    try:
        root_response = requests.get('http://localhost:8001/', timeout=5)
        print(f"   Status: {root_response.status_code}")
        if root_response.status_code == 200:
            print("   ✅ Serviço Python está rodando")
        else:
            print(f"   ❌ Serviço Python não está respondendo: {root_response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Erro ao verificar serviço: {e}")
        
    print("\n📋 4. Testando endpoint /query...")
    try:
        test_query = {
            "type": "cpf",
            "query": "12345678901"
        }
        query_response = requests.post('http://localhost:8001/query', json=test_query, timeout=10)
        print(f"   Status: {query_response.status_code}")
        print(f"   Response: {query_response.text}")
        
    except Exception as e:
        print(f"   ❌ Erro no teste de query: {e}")
        
except Exception as e:
    print(f"❌ Erro geral: {e}")

import requests
import json

# Testar endpoint /query diretamente
print("🔍 Testando endpoint /query diretamente...")

try:
    # Testar com dados válidos
    test_data = {
        "type": "cpf",
        "query": "12345678901"
    }
    
    print(f"📝 Enviando: {json.dumps(test_data)}")
    response = requests.post('http://localhost:8001/query', json=test_data, timeout=10)
    print(f"📊 Status: {response.status_code}")
    print(f"📋 Headers: {dict(response.headers)}")
    print(f"📄 Response: {response.text}")
    
    if response.status_code == 200:
        print("✅ Endpoint /query está funcionando!")
    else:
        print(f"❌ Erro {response.status_code}: {response.text}")
        
except Exception as e:
    print(f"❌ Erro na requisição: {e}")

# Testar endpoint /send-command para comparação
print("\n🔍 Testando endpoint /send-command para comparação...")
try:
    test_data = {
        "type": "cpf",
        "query": "12345678901"
    }
    
    print(f"📝 Enviando: {json.dumps(test_data)}")
    response = requests.post('http://localhost:8001/send-command', json=test_data, timeout=10)
    print(f"📊 Status: {response.status_code}")
    print(f"📋 Headers: {dict(response.headers)}")
    print(f"📄 Response: {response.text}")
    
except Exception as e:
    print(f"❌ Erro na requisição: {e}")

# Listar todos os endpoints
print("\n📋 Listando endpoints disponíveis...")
try:
    response = requests.get('http://localhost:8001/openapi.json', timeout=5)
    if response.status_code == 200:
        openapi = response.json()
        print("✅ Endpoints encontrados:")
        for path, methods in openapi.get('paths', {}).items():
            print(f"  📍 {path}: {list(methods.keys())}")
    else:
        print(f"❌ Erro ao obter endpoints: {response.status_code}")
        
except Exception as e:
    print(f"❌ Erro ao listar endpoints: {e}")

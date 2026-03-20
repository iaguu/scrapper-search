import requests
import json

# Testar endpoint /query
try:
    response = requests.get('http://localhost:8001/query')
    print(f"GET /query Status: {response.status_code}")
    print(f"GET /query Response: {response.text}")
except Exception as e:
    print(f"GET Error: {e}")

try:
    data = {"type": "cpf", "query": "12345678901"}
    response = requests.post('http://localhost:8001/query', json=data)
    print(f"POST /query Status: {response.status_code}")
    print(f"POST /query Response: {response.text}")
except Exception as e:
    print(f"POST Error: {e}")

# Listar endpoints disponíveis
try:
    response = requests.get('http://localhost:8001/openapi.json')
    print(f"OpenAPI Status: {response.status_code}")
    if response.status_code == 200:
        openapi = response.json()
        print("Endpoints disponíveis:")
        for path, methods in openapi.get('paths', {}).items():
            print(f"  {path}: {list(methods.keys())}")
except Exception as e:
    print(f"OpenAPI Error: {e}")

#!/usr/bin/env python3
"""
Comprehensive test for the Telegram Query Bridge system
Tests all services and their communication
"""

import requests
import json
import time
import sys
from typing import Dict, List

# Service URLs
MANAGER_URL = "http://localhost:9000"
PYTHON_URL = "http://localhost:8001"
NODE_URL = "http://localhost:3000"

def test_service_health(url: str, service_name: str) -> Dict:
    """Test if a service is healthy"""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        return {
            "service": service_name,
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "status_code": response.status_code,
            "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
            "url": url
        }
    except requests.exceptions.ConnectionError:
        return {
            "service": service_name,
            "status": "offline",
            "error": "Connection refused",
            "url": url
        }
    except requests.exceptions.Timeout:
        return {
            "service": service_name,
            "status": "timeout",
            "error": "Request timeout",
            "url": url
        }
    except Exception as e:
        return {
            "service": service_name,
            "status": "error",
            "error": str(e),
            "url": url
        }

def test_manager_endpoints() -> List[Dict]:
    """Test web manager endpoints"""
    results = []
    
    # Test health
    results.append(test_service_health(MANAGER_URL, "Web Manager"))
    
    # Test services status
    try:
        response = requests.get(f"{MANAGER_URL}/services/status", timeout=5)
        results.append({
            "service": "Web Manager - Services Status",
            "status": "success" if response.status_code == 200 else "failed",
            "status_code": response.status_code,
            "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        })
    except Exception as e:
        results.append({
            "service": "Web Manager - Services Status",
            "status": "error",
            "error": str(e)
        })
    
    return results

def test_node_endpoints() -> List[Dict]:
    """Test Node.js API endpoints"""
    results = []
    
    # Test health
    results.append(test_service_health(NODE_URL, "Node.js API"))
    
    # Test query endpoint (should fail without API key)
    try:
        response = requests.post(f"{NODE_URL}/query", 
                               json={"type": "cpf", "query": "12345678901"}, 
                               timeout=5)
        results.append({
            "service": "Node.js API - Query (no auth)",
            "status": "success" if response.status_code == 401 else "unexpected",
            "status_code": response.status_code,
            "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        })
    except Exception as e:
        results.append({
            "service": "Node.js API - Query (no auth)",
            "status": "error",
            "error": str(e)
        })
    
    return results

def test_python_endpoints() -> List[Dict]:
    """Test Python service endpoints"""
    results = []
    
    # Test health
    results.append(test_service_health(PYTHON_URL, "Python Service"))
    
    # Test auth status
    try:
        response = requests.get(f"{PYTHON_URL}/auth-status", timeout=5)
        results.append({
            "service": "Python Service - Auth Status",
            "status": "success" if response.status_code == 200 else "failed",
            "status_code": response.status_code,
            "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        })
    except Exception as e:
        results.append({
            "service": "Python Service - Auth Status",
            "status": "error",
            "error": str(e)
        })
    
    return results

def test_service_communication() -> List[Dict]:
    """Test communication between services"""
    results = []
    
    # Test if Node.js can reach Python service
    try:
        response = requests.get(f"{PYTHON_URL}/health", timeout=5)
        python_healthy = response.status_code == 200
        
        if python_healthy:
            # Test Node.js health check to Python
            response = requests.get(f"{NODE_URL}/health", timeout=5)
            if response.status_code == 200:
                node_data = response.json()
                results.append({
                    "service": "Service Communication",
                    "status": "success",
                    "message": "Node.js API is running and should be able to communicate with Python service",
                    "python_service": PYTHON_URL,
                    "node_service": NODE_URL
                })
            else:
                results.append({
                    "service": "Service Communication",
                    "status": "partial",
                    "message": "Python service is healthy but Node.js API is not responding"
                })
        else:
            results.append({
                "service": "Service Communication",
                "status": "failed",
                "message": "Python service is not healthy"
            })
    except Exception as e:
        results.append({
            "service": "Service Communication",
            "status": "error",
            "error": str(e)
        })
    
    return results

def print_results(results: List[Dict]):
    """Print test results in a formatted way"""
    print("\n" + "="*60)
    print("TELEGRAM QUERY BRIDGE - SYSTEM TEST RESULTS")
    print("="*60)
    
    healthy_count = 0
    total_count = len(results)
    
    for result in results:
        service = result.get("service", "Unknown")
        status = result.get("status", "unknown")
        
        if status == "healthy" or status == "success":
            symbol = "✅"
            healthy_count += 1
        elif status == "offline" or status == "failed":
            symbol = "❌"
        elif status == "partial":
            symbol = "⚠️"
        else:
            symbol = "❓"
        
        print(f"\n{symbol} {service}")
        print(f"   Status: {status}")
        
        if "url" in result:
            print(f"   URL: {result['url']}")
        
        if "status_code" in result:
            print(f"   HTTP Status: {result['status_code']}")
        
        if "error" in result:
            print(f"   Error: {result['error']}")
        
        if "message" in result:
            print(f"   Message: {result['message']}")
        
        if "response" in result and isinstance(result["response"], dict):
            print(f"   Response: {json.dumps(result['response'], indent=6)}")
    
    print(f"\n{'='*60}")
    print(f"SUMMARY: {healthy_count}/{total_count} services healthy")
    print(f"{'='*60}")
    
    if healthy_count == total_count:
        print("🎉 All systems operational!")
        return 0
    else:
        print("⚠️  Some services need attention")
        return 1

def main():
    """Main test function"""
    print("🔍 Testing Telegram Query Bridge System...")
    print("Waiting 2 seconds for services to stabilize...")
    time.sleep(2)
    
    all_results = []
    
    # Test all services
    print("\n📋 Testing Web Manager...")
    all_results.extend(test_manager_endpoints())
    
    print("\n🐍 Testing Python Service...")
    all_results.extend(test_python_endpoints())
    
    print("\n🟢 Testing Node.js API...")
    all_results.extend(test_node_endpoints())
    
    print("\n🔗 Testing Service Communication...")
    all_results.extend(test_service_communication())
    
    # Print results
    exit_code = print_results(all_results)
    
    # Print manual startup instructions if services are offline
    offline_services = [r for r in all_results if r.get("status") == "offline"]
    if offline_services:
        print(f"\n📝 MANUAL STARTUP INSTRUCTIONS:")
        print(f"   {'='*40}")
        for service in offline_services:
            name = service.get("service", "Unknown")
            if "Python" in name:
                print(f"   🐍 Python Service:")
                print(f"      cd telegram_service")
                print(f"      python -m uvicorn main:app --host 127.0.0.1 --port 8001")
            elif "Node.js" in name:
                print(f"   🟢 Node.js API:")
                print(f"      node api/index.js")
            elif "Web Manager" in name:
                print(f"   🌐 Web Manager:")
                print(f"      python server.py")
        print(f"\n   💡 Or use: npm run start-all")
    
    return exit_code

if __name__ == "__main__":
    exit(main())

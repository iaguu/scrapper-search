# Fixed Startup Guide

## ✅ Issues Fixed

1. **Port conflicts**: Node.js API now correctly connects to Python service on port 8001
2. **API endpoints**: All services have proper health endpoints
3. **Startup script**: Created manager-only startup option
4. **Service monitor**: Updated with correct ports and commands
5. **Comprehensive test**: Added system-wide testing

## 🚀 Usage

### Start Web Manager Only (Recommended)
```bash
npm start
# or
npm run manager
# or
start-manager-only.bat
```

### Start All Services
```bash
npm run start-all
# or
start-complete.bat
```

### Manual Service Startup
```bash
# Python Service (from telegram_service folder)
cd telegram_service
python -m uvicorn main:app --host 127.0.0.1 --port 8001

# Node.js API (from root folder)
node api/index.js

# Web Manager (from root folder)
python server.py
```

## 🧪 Testing

Run the comprehensive system test:
```bash
npm test
# or
python test_system.py
```

## 📡 Service URLs

- **Web Manager**: http://localhost:9000
- **Node.js API**: http://localhost:3000
- **Python Service**: http://localhost:8001

## 🔧 Service Control via Web Manager

Access http://localhost:9000 and use the dashboard to:
- Start/stop services individually
- Monitor service health
- View logs and status

## 📝 Notes

- The web manager provides a GUI to control Python and Node services
- Services can be started manually when needed
- Port configuration is now consistent across all files
- Health checks work properly between all services

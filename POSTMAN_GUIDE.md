# Postman Collection Usage Guide

## 📋 Import Collection

1. Open Postman
2. Click "Import" in the top left
3. Select "File" tab
4. Choose `Telegram_Query_Bridge_API.postman_collection.json`
5. Click "Import"

## 🔧 Setup Environment Variables

Before using the collection, set up your API key:

1. In Postman, click the "Environment" dropdown (top right)
2. Click "Edit" next to "Globals"
3. Add or edit the `api_key` variable:
   - Variable: `api_key`
   - Initial Value: `your-actual-api-key`
   - Current Value: `your-actual-api-key`

Or set it directly in the collection variables.

## 🧪 Test Scenarios

### 1. Health Checks
- **Node API Health**: Tests if Node.js service is running on port 3000
- **Python Service Health**: Tests if Python service is running on port 8001
- **Web Manager Health**: Tests if Web Manager is running on port 9000

### 2. Service Control
Use these to start/stop services via the Web Manager:
- **Start Python Service**: Starts the Python Telegram service
- **Start Node Service**: Starts the Node.js API service
- **Get Services Status**: Shows current status of all services
- **Stop Python Service**: Stops the Python service
- **Stop Node Service**: Stops the Node.js service

### 3. Query Tests
Test all supported query types through the Node.js API:
- **CPF**: Query CPF information
- **Telefone**: Query phone number information
- **Nome**: Query name information
- **Placa**: Query vehicle plate information
- **Email**: Query email information
- **CEP**: Query postal code information
- **CNPJ**: Query CNPJ information
- **Mãe**: Query mother's name information

### 4. Error Tests
Test error handling:
- **Query Without API Key**: Should return 401 Unauthorized
- **Query Invalid Type**: Should return 400 Bad Request
- **Query Missing Fields**: Should return 400 Bad Request
- **Invalid Service Control**: Should return 400 Bad Request

### 5. Direct Python Tests
Test Python service directly:
- **Python Auth Status**: Check Telegram authentication status
- **Python Start Telegram**: Start Telegram client
- **Python Direct Query**: Send query directly to Python service

## 🚀 Recommended Test Order

1. **Health Checks** - Verify all services are running
2. **Service Control** - Start services if needed
3. **Query Tests** - Test actual functionality
4. **Error Tests** - Verify error handling
5. **Direct Python Tests** - Debug Python service issues

## 📝 Notes

- All query requests require a valid API key in the `X-API-Key` header
- Make sure Python and Node services are running before testing queries
- The Web Manager (port 9000) can control the other services
- Check the console output of each service for detailed logs
- Use the "Get Services Status" endpoint to verify service states

## 🔍 Troubleshooting

If tests fail:

1. **Check service status**: Run health checks first
2. **Verify ports**: Ensure services are on correct ports (3000, 8001, 9000)
3. **Check API key**: Make sure your API key is set correctly
4. **Start services**: Use service control endpoints to start services
5. **Check logs**: Look at console output from each service
6. **Test directly**: Use direct Python tests to isolate issues

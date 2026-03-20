const axios = require('axios');

const API_URL = 'http://localhost:3000';
const API_KEY = 'demo_key_12345';

const testQueries = [
    { type: 'cpf', query: '12345678901', description: 'CPF Teste' },
    { type: 'telefone', query: '11987654321', description: 'Telefone Teste' },
    { type: 'placa', query: 'ABC1234', description: 'Placa Teste' },
    { type: 'nome', query: 'João Silva', description: 'Nome Teste' },
    { type: 'email', query: 'joao.silva@email.com', description: 'Email Teste' },
    { type: 'cep', query: '01310-100', description: 'CEP Teste' },
    { type: 'cnpj', query: '12.345.678/0001-90', description: 'CNPJ Teste' },
    { type: 'mae', query: 'Maria Silva', description: 'Mãe Teste' }
];

async function testQuery(type, query, description) {
    console.log(`\n🧪 Testando: ${description}`);
    console.log(`📝 Tipo: ${type}, Query: ${query}`);
    
    try {
        const startTime = Date.now();
        
        const response = await axios.post(`${API_URL}/query`, {
            type: type,
            query: query
        }, {
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': API_KEY
            },
            timeout: 30000
        });
        
        const endTime = Date.now();
        const responseTime = endTime - startTime;
        
        console.log(`✅ Sucesso! Tempo: ${responseTime}ms`);
        console.log(`📊 Resposta:`, JSON.stringify(response.data, null, 2));
        
        return {
            success: true,
            responseTime: responseTime,
            data: response.data
        };
        
    } catch (error) {
        console.log(`❌ Falha!`);
        console.log(`🔍 Erro:`, error.message);
        
        if (error.response) {
            console.log(`📊 Status: ${error.response.status}`);
            console.log(`📋 Detalhes:`, JSON.stringify(error.response.data, null, 2));
        }
        
        return {
            success: false,
            error: error.message,
            status: error.response?.status,
            details: error.response?.data
        };
    }
}

async function runAllTests() {
    console.log('🚀 Iniciando testes de consulta...');
    console.log('=' .repeat(50));
    
    const results = [];
    
    for (const test of testQueries) {
        const result = await testQuery(test.type, test.query, test.description);
        results.push({
            ...test,
            ...result
        });
        
        // Aguardar um pouco entre testes
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    console.log('\n' + '=' .repeat(50));
    console.log('📊 RESUMO DOS TESTES');
    console.log('=' .repeat(50));
    
    const successful = results.filter(r => r.success);
    const failed = results.filter(r => !r.success);
    
    console.log(`✅ Sucessos: ${successful.length}/${results.length}`);
    console.log(`❌ Falhas: ${failed.length}/${results.length}`);
    
    if (successful.length > 0) {
        const avgResponseTime = successful.reduce((sum, r) => sum + r.responseTime, 0) / successful.length;
        console.log(`⏱️ Tempo médio de resposta: ${avgResponseTime.toFixed(2)}ms`);
    }
    
    if (failed.length > 0) {
        console.log('\n❌ DETALHES DAS FALHAS:');
        failed.forEach(f => {
            console.log(`\n🔍 ${f.description}:`);
            console.log(`   Erro: ${f.error}`);
            if (f.status) console.log(`   Status: ${f.status}`);
            if (f.details) console.log(`   Detalhes: ${JSON.stringify(f.details, null, 4)}`);
        });
    }
    
    // Testar health check
    console.log('\n🏥 Testando Health Check...');
    try {
        const healthResponse = await axios.get(`${API_URL}/health`);
        console.log('✅ Health Check OK:', JSON.stringify(healthResponse.data, null, 2));
    } catch (error) {
        console.log('❌ Health Check Falhou:', error.message);
    }
    
    console.log('\n🏁 Testes concluídos!');
}

// Executar testes
runAllTests().catch(console.error);

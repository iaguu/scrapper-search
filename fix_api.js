const fs = require('fs');

let content = fs.readFileSync('api/index.js', 'utf8');
content = content.replace('const command = `${commandMap[type]} ${query}`;', 'const command = `${commandMap[type]} ${query}`;');
fs.writeFileSync('api/index.js', content);

console.log('Fixed syntax error in api/index.js');

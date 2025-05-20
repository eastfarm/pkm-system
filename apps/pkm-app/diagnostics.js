// File: apps/pkm-app/diagnostics.js
const fs = require('fs');
const path = require('path');

console.log('Running PKM App Diagnostics...');

// Check if key files exist
const requiredFiles = [
  'package.json',
  'next.config.js',
  'pages/_app.js',
  'pages/index.js',
  'pages/staging.js',
  'components/StagingTable.js'
];

console.log('\nChecking required files:');
requiredFiles.forEach(file => {
  const exists = fs.existsSync(path.join(process.cwd(), file));
  console.log(`- ${file}: ${exists ? '✅ Found' : '❌ Missing'}`);
});

// Check package.json
console.log('\nChecking package.json:');
const pkg = require('./package.json');
console.log(`- Next.js version: ${pkg.dependencies.next}`);
console.log(`- React version: ${pkg.dependencies.react}`);
console.log(`- Build script: ${pkg.scripts.build}`);

// Check next.config.js if it exists
if (fs.existsSync(path.join(process.cwd(), 'next.config.js'))) {
  console.log('\nNext.config.js exists');
  try {
    const config = require('./next.config.js');
    console.log('- Config loaded successfully');
    console.log('- Config contents:', config);
  } catch (e) {
    console.log('- Error loading config:', e.message);
  }
}

// Check imports in index.js
if (fs.existsSync(path.join(process.cwd(), 'pages/index.js'))) {
  console.log('\nAnalyzing index.js:');
  const indexContent = fs.readFileSync(path.join(process.cwd(), 'pages/index.js'), 'utf8');
  
  // Simple check for import statements
  const imports = indexContent.match(/import .+ from ['"].+['"]/g) || [];
  console.log('- Imports found:');
  imports.forEach(imp => console.log(`  ${imp}`));
  
  // Check for potential syntax errors
  console.log('- Syntax check:');
  try {
    eval('(' + indexContent + ')');
    console.log('  No obvious syntax errors (basic check only)');
  } catch (e) {
    console.log(`  Potential syntax error: ${e.message}`);
  }
}

console.log('\nDiagnostics complete. Add this output to your support request.');
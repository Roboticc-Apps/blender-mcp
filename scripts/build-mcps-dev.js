#!/usr/bin/env node
/**
 * MCP Development Build Script
 *
 * Creates mock MCP packages for development and testing.
 * For production builds, use build-mcps.js after setting up pkg and PyInstaller.
 */

const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');
const archiver = require('archiver');

const PROJECT_ROOT = path.resolve(__dirname, '..');
const MCP_PACKAGES_DIR = path.join(PROJECT_ROOT, 'mcp-packages', 'windows-base');
const DIST_DIR = path.join(PROJECT_ROOT, 'dist', 'mcps');

// ANSI colors
const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    red: '\x1b[31m'
};

function log(message, color = 'reset') {
    console.log(`${colors[color]}${message}${colors.reset}`);
}

async function calculateChecksum(filePath) {
    const fileBuffer = await fs.readFile(filePath);
    const hash = crypto.createHash('sha256');
    hash.update(fileBuffer);
    return 'sha256:' + hash.digest('hex');
}

async function createZipArchive(sourceDir, outputPath, files) {
    return new Promise((resolve, reject) => {
        const output = require('fs').createWriteStream(outputPath);
        const archive = archiver('zip', { zlib: { level: 9 } });

        output.on('close', () => {
            log(`✅ Created archive: ${path.basename(outputPath)} (${(archive.pointer() / 1024 / 1024).toFixed(2)} MB)`, 'green');
            resolve();
        });

        archive.on('error', reject);
        archive.pipe(output);

        // Add specific files
        for (const file of files) {
            const filePath = path.join(sourceDir, file);
            try {
                require('fs').statSync(filePath);
                archive.file(filePath, { name: file });
            } catch (error) {
                log(`⚠️  File not found: ${file}, skipping...`, 'yellow');
            }
        }

        archive.finalize();
    });
}

async function ensureDir(dir) {
    await fs.mkdir(dir, { recursive: true });
}

/**
 * Create mock executable (for development/testing)
 */
async function createMockExecutable(name, version) {
    const content = `#!/usr/bin/env node
/*
 * Mock ${name} Executable v${version}
 *
 * This is a development mock for testing the MCP installation system.
 * In production, this would be a standalone executable created with pkg/PyInstaller.
 */

console.log('Mock ${name} v${version} started');
console.log('PID:', process.pid);

// Simulate MCP server initialization
setTimeout(() => {
    console.log(JSON.stringify({
        jsonrpc: '2.0',
        method: 'initialized',
        params: {
            serverInfo: {
                name: '${name}',
                version: '${version}'
            }
        }
    }));
}, 1000);

// Handle stdin (JSON-RPC requests)
process.stdin.on('data', (data) => {
    try {
        const request = JSON.parse(data.toString());
        console.log('Received request:', request.method);

        // Mock response
        const response = {
            jsonrpc: '2.0',
            id: request.id,
            result: {
                success: true,
                message: 'Mock response from ${name}'
            }
        };

        console.log(JSON.stringify(response));
    } catch (error) {
        console.error('Error processing request:', error);
    }
});

// Keep alive
setInterval(() => {
    // Still alive
}, 5000);
`;

    return content;
}

/**
 * Build Filesystem MCP (Mock)
 */
async function buildFilesystemMCP() {
    log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'bright');
    log('📦 Building Filesystem MCP (Development Mock)', 'bright');
    log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', 'bright');

    const mcpDir = path.join(MCP_PACKAGES_DIR, 'filesystem-mcp');
    const buildDir = path.join(DIST_DIR, 'filesystem-mcp-build');

    await ensureDir(buildDir);

    // Read manifest
    const manifestPath = path.join(mcpDir, 'manifest.json');
    const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf-8'));
    log(`📄 Loaded manifest: ${manifest.name} v${manifest.version}`, 'yellow');

    // Create mock executable
    const mockExe = await createMockExecutable('filesystem-mcp', manifest.version);
    const exePath = path.join(buildDir, 'filesystem-mcp.exe');
    await fs.writeFile(exePath, mockExe);
    log(`📝 Created mock executable`, 'yellow');

    // Copy manifest
    await fs.copyFile(manifestPath, path.join(buildDir, 'manifest.json'));

    // Create README
    const readme = `# Filesystem MCP - Development Mock

This is a development mock executable for testing the MCP installation system.

## For Production

To create a real standalone executable:

1. Install pkg globally: \`npm install -g pkg\`
2. Run: \`pkg . --target node18-win-x64 --output dist/filesystem-mcp.exe\`

The real executable will bundle Node.js runtime and all dependencies.
`;
    await fs.writeFile(path.join(buildDir, 'README.txt'), readme);

    // Create ZIP
    const zipPath = path.join(DIST_DIR, `filesystem-mcp-v${manifest.version}.zip`);
    await createZipArchive(buildDir, zipPath, [
        'filesystem-mcp.exe',
        'manifest.json',
        'README.txt'
    ]);

    // Calculate checksum
    const checksum = await calculateChecksum(zipPath);
    log(`🔒 Checksum: ${checksum}`, 'green');

    return {
        mcp_id: 'filesystem-mcp',
        name: manifest.name,
        version: manifest.version,
        exe_name: 'filesystem-mcp.exe',
        zip_path: zipPath,
        checksum,
        size_mb: (await fs.stat(zipPath)).size / 1024 / 1024
    };
}

/**
 * Build Windows System Control MCP (Mock)
 */
async function buildWindowsMCP() {
    log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'bright');
    log('🐍 Building Windows System Control MCP (Development Mock)', 'bright');
    log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', 'bright');

    const mcpDir = path.join(MCP_PACKAGES_DIR, 'windows-mcp');
    const buildDir = path.join(DIST_DIR, 'windows-mcp-build');

    await ensureDir(buildDir);

    // Read manifest
    const manifestPath = path.join(mcpDir, 'manifest.json');
    const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf-8'));
    log(`📄 Loaded manifest: ${manifest.name} v${manifest.version}`, 'yellow');

    // Create mock executable (Python-style)
    const mockExe = `#!/usr/bin/env python3
# Mock Windows System Control MCP v${manifest.version}
# Development mock for testing

import sys
import json
import time

print(f"Mock Windows MCP v${manifest.version} started", file=sys.stderr)
print(f"PID: {id(sys)}", file=sys.stderr)

# Simulate initialization
time.sleep(1)
print(json.dumps({
    "jsonrpc": "2.0",
    "method": "initialized",
    "params": {
        "serverInfo": {
            "name": "windows-mcp",
            "version": "${manifest.version}"
        }
    }
}))

# For production: Use PyInstaller
# pyinstaller --onefile --name windows-mcp main.py
`;

    const exePath = path.join(buildDir, 'windows-mcp.exe');
    await fs.writeFile(exePath, mockExe);
    log(`📝 Created mock executable`, 'yellow');

    // Copy manifest
    await fs.copyFile(manifestPath, path.join(buildDir, 'manifest.json'));

    // Create README
    const readme = `# Windows System Control MCP - Development Mock

This is a development mock executable for testing.

## For Production

To create a real standalone executable:

1. Install PyInstaller: \`uv pip install pyinstaller\`
2. Run: \`uv run pyinstaller --onefile --name windows-mcp main.py\`

The real executable will bundle Python runtime and all dependencies.
`;
    await fs.writeFile(path.join(buildDir, 'README.txt'), readme);

    // Create ZIP
    const zipPath = path.join(DIST_DIR, `windows-mcp-v${manifest.version}.zip`);
    await createZipArchive(buildDir, zipPath, [
        'windows-mcp.exe',
        'manifest.json',
        'README.txt'
    ]);

    // Calculate checksum
    const checksum = await calculateChecksum(zipPath);
    log(`🔒 Checksum: ${checksum}`, 'green');

    return {
        mcp_id: 'windows-mcp',
        name: manifest.name,
        version: manifest.version,
        exe_name: 'windows-mcp.exe',
        zip_path: zipPath,
        checksum,
        size_mb: (await fs.stat(zipPath)).size / 1024 / 1024
    };
}

/**
 * Build Web Fetch MCP (Mock)
 */
async function buildFetchMCP() {
    log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'bright');
    log('🌐 Building Web Fetch MCP (Development Mock)', 'bright');
    log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', 'bright');

    const mcpDir = path.join(MCP_PACKAGES_DIR, 'fetch-mcp');
    const buildDir = path.join(DIST_DIR, 'fetch-mcp-build');

    await ensureDir(buildDir);

    // Read manifest
    const manifestPath = path.join(mcpDir, 'manifest.json');
    const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf-8'));
    log(`📄 Loaded manifest: ${manifest.name} v${manifest.version}`, 'yellow');

    // Create mock executable
    const mockExe = `#!/usr/bin/env python3
# Mock Fetch MCP v${manifest.version}

import sys
import json

print(f"Mock Fetch MCP v${manifest.version} started", file=sys.stderr)

# Simulate initialization
print(json.dumps({
    "jsonrpc": "2.0",
    "method": "initialized",
    "params": {
        "serverInfo": {
            "name": "fetch-mcp",
            "version": "${manifest.version}"
        }
    }
}))
`;

    const exePath = path.join(buildDir, 'fetch-mcp.exe');
    await fs.writeFile(exePath, mockExe);
    log(`📝 Created mock executable`, 'yellow');

    // Copy manifest
    await fs.copyFile(manifestPath, path.join(buildDir, 'manifest.json'));

    // Create README
    const readme = `# Web Fetch MCP - Development Mock

This is a development mock executable for testing.

## For Production

To create a real standalone executable:

1. Install dependencies: \`pip install mcp-server-fetch pyinstaller\`
2. Run: \`pyinstaller --onefile --name fetch-mcp main.py\`
`;
    await fs.writeFile(path.join(buildDir, 'README.txt'), readme);

    // Create ZIP
    const zipPath = path.join(DIST_DIR, `fetch-mcp-v${manifest.version}.zip`);
    await createZipArchive(buildDir, zipPath, [
        'fetch-mcp.exe',
        'manifest.json',
        'README.txt'
    ]);

    // Calculate checksum
    const checksum = await calculateChecksum(zipPath);
    log(`🔒 Checksum: ${checksum}`, 'green');

    return {
        mcp_id: 'fetch-mcp',
        name: manifest.name,
        version: manifest.version,
        exe_name: 'fetch-mcp.exe',
        zip_path: zipPath,
        checksum,
        size_mb: (await fs.stat(zipPath)).size / 1024 / 1024
    };
}

/**
 * Main build process
 */
async function main() {
    log('\n╔═══════════════════════════════════════════════╗', 'bright');
    log('║   MCP DEVELOPMENT BUILD - Mock Packages       ║', 'bright');
    log('╚═══════════════════════════════════════════════╝\n', 'bright');

    log('⚠️  Note: This creates mock executables for development/testing.', 'yellow');
    log('⚠️  For production, use build-mcps.js with pkg and PyInstaller.\n', 'yellow');

    // Create dist directory
    await ensureDir(DIST_DIR);

    const results = [];

    try {
        // Build all MCPs
        log('\n🚀 Starting build process...\n', 'green');

        results.push(await buildFilesystemMCP());
        results.push(await buildWindowsMCP());
        results.push(await buildFetchMCP());

        // Generate build manifest
        const buildManifest = {
            build_date: new Date().toISOString(),
            build_type: 'development_mock',
            platform: 'win32',
            package_name: 'windows-base',
            version: '1.0.0-dev',
            mcps: results.map(r => ({
                mcp_id: r.mcp_id,
                name: r.name,
                version: r.version,
                executable: {
                    filename: r.exe_name,
                    type: 'mock',
                    size_mb: parseFloat(r.size_mb.toFixed(2))
                },
                archive: {
                    filename: path.basename(r.zip_path),
                    checksum: r.checksum
                }
            }))
        };

        const manifestPath = path.join(DIST_DIR, 'build-manifest.json');
        await fs.writeFile(manifestPath, JSON.stringify(buildManifest, null, 2));

        // Success summary
        log('\n╔═══════════════════════════════════════════════╗', 'green');
        log('║            ✅ BUILD COMPLETE!                 ║', 'green');
        log('╚═══════════════════════════════════════════════╝\n', 'green');

        log('📦 Built Mock MCPs:', 'bright');
        results.forEach(r => {
            log(`   • ${r.name} v${r.version}`, 'green');
            log(`     - Executable: ${r.exe_name}`, 'yellow');
            log(`     - Archive: ${path.basename(r.zip_path)} (${r.size_mb.toFixed(2)} MB)`, 'yellow');
            log(`     - Checksum: ${r.checksum.substring(0, 50)}...`, 'yellow');
        });

        log(`\n📄 Build manifest: ${manifestPath}`, 'green');
        log(`\n🎉 Mock packages created successfully!`, 'bright');
        log(`\n📍 Location: ${DIST_DIR}`, 'blue');

        log(`\n⚠️  Next Steps:`, 'yellow');
        log(`   1. Test installation with mcp-manager.js`, 'yellow');
        log(`   2. For production: Install pkg and PyInstaller`, 'yellow');
        log(`   3. Run build-mcps.js for real executables`, 'yellow');

    } catch (error) {
        log('\n❌ BUILD FAILED!', 'red');
        log(`Error: ${error.message}`, 'red');
        if (error.stack) {
            log(`\nStack trace:\n${error.stack}`, 'red');
        }
        process.exit(1);
    }
}

// Run if called directly
if (require.main === module) {
    main().catch(error => {
        console.error('Fatal error:', error);
        process.exit(1);
    });
}

module.exports = { buildFilesystemMCP, buildWindowsMCP, buildFetchMCP };

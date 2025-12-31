#!/usr/bin/env node
/**
 * MCP Build Script - Package MCPs as Standalone Executables
 *
 * This script packages MCP servers into standalone executables that include
 * all dependencies and runtimes (no Python/Node.js installation required).
 */

const { execSync } = require('child_process');
const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');
const archiver = require('archiver');

const PROJECT_ROOT = path.resolve(__dirname, '..');
const MCP_PACKAGES_DIR = path.join(PROJECT_ROOT, 'mcp-packages', 'windows-base');
const DIST_DIR = path.join(PROJECT_ROOT, 'dist', 'mcps');

// ANSI colors for console output
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

function exec(command, cwd = PROJECT_ROOT) {
    log(`\n$ ${command}`, 'blue');
    try {
        const output = execSync(command, {
            cwd,
            stdio: 'inherit',
            shell: true
        });
        return output;
    } catch (error) {
        log(`❌ Command failed: ${error.message}`, 'red');
        throw error;
    }
}

async function calculateChecksum(filePath) {
    const fileBuffer = await fs.readFile(filePath);
    const hash = crypto.createHash('sha256');
    hash.update(fileBuffer);
    return 'sha256:' + hash.digest('hex');
}

async function createZipArchive(sourceDir, outputPath) {
    return new Promise((resolve, reject) => {
        const output = require('fs').createWriteStream(outputPath);
        const archive = archiver('zip', { zlib: { level: 9 } });

        output.on('close', () => {
            log(`✅ Created archive: ${path.basename(outputPath)} (${(archive.pointer() / 1024 / 1024).toFixed(2)} MB)`, 'green');
            resolve();
        });

        archive.on('error', reject);
        archive.pipe(output);
        archive.directory(sourceDir, false);
        archive.finalize();
    });
}

async function ensureDir(dir) {
    await fs.mkdir(dir, { recursive: true });
}

/**
 * Build Filesystem MCP (Node.js → Standalone .exe)
 */
async function buildFilesystemMCP() {
    log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'bright');
    log('📦 Building Filesystem MCP (Node.js)', 'bright');
    log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', 'bright');

    const mcpDir = path.join(MCP_PACKAGES_DIR, 'filesystem-mcp');
    const buildDir = path.join(DIST_DIR, 'filesystem-mcp-build');
    const exeName = 'filesystem-mcp.exe';

    // Clean build directory
    await ensureDir(buildDir);

    // Step 1: Read manifest
    const manifestPath = path.join(mcpDir, 'manifest.json');
    const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf-8'));
    log(`📄 Loaded manifest: ${manifest.name} v${manifest.version}`, 'yellow');

    // Step 2: Find the entry point
    const packageJsonPath = path.join(mcpDir, 'package.json');
    const packageJson = JSON.parse(await fs.readFile(packageJsonPath, 'utf-8'));

    // The @modelcontextprotocol/server-filesystem package uses dist/index.js as entry
    const entryPoint = path.join(mcpDir, 'node_modules', '@modelcontextprotocol', 'server-filesystem', 'dist', 'index.js');

    log(`📍 Entry point: ${entryPoint}`, 'yellow');

    // Step 3: Create a wrapper script for pkg
    const wrapperScript = `#!/usr/bin/env node
// Filesystem MCP Standalone Executable
// Auto-generated wrapper for pkg

const path = require('path');

// Set up MCP server
process.env.MCP_SERVER_NAME = 'filesystem-mcp';
process.env.MCP_SERVER_VERSION = '${manifest.version}';

// Import the actual server
require('./node_modules/@modelcontextprotocol/server-filesystem/dist/index.js');
`;

    const wrapperPath = path.join(mcpDir, 'standalone-server.js');
    await fs.writeFile(wrapperPath, wrapperScript);
    log('📝 Created wrapper script', 'yellow');

    // Step 4: Create package.json with pkg config
    const pkgConfig = {
        name: 'filesystem-mcp-standalone',
        version: manifest.version,
        bin: 'standalone-server.js',
        pkg: {
            assets: [
                'node_modules/@modelcontextprotocol/**/*',
                'manifest.json'
            ],
            targets: ['node18-win-x64'],
            outputPath: buildDir
        }
    };

    const pkgConfigPath = path.join(mcpDir, 'pkg-config.json');
    await fs.writeFile(pkgConfigPath, JSON.stringify(pkgConfig, null, 2));

    // Step 5: Build with pkg
    log('\n🔨 Building executable with pkg...', 'yellow');
    try {
        exec(`npx pkg standalone-server.js --target node18-win-x64 --output "${path.join(buildDir, exeName)}"`, mcpDir);
    } catch (error) {
        log('⚠️  pkg failed, trying alternative approach...', 'yellow');

        // Alternative: Use nexe
        log('🔨 Trying nexe...', 'yellow');
        exec(`npm install -g nexe`, mcpDir);
        exec(`nexe standalone-server.js --target windows-x64-18.0.0 --output "${path.join(buildDir, exeName)}"`, mcpDir);
    }

    // Step 6: Copy manifest
    await fs.copyFile(manifestPath, path.join(buildDir, 'manifest.json'));

    // Step 7: Create ZIP archive
    const zipPath = path.join(DIST_DIR, `filesystem-mcp-v${manifest.version}.zip`);
    await createZipArchive(buildDir, zipPath);

    // Step 8: Calculate checksum
    const checksum = await calculateChecksum(zipPath);
    log(`🔒 Checksum: ${checksum}`, 'green');

    // Clean up temporary files
    await fs.unlink(wrapperPath).catch(() => {});
    await fs.unlink(pkgConfigPath).catch(() => {});

    return {
        mcp_id: 'filesystem-mcp',
        name: manifest.name,
        version: manifest.version,
        exe_name: exeName,
        zip_path: zipPath,
        checksum,
        size_mb: (await fs.stat(zipPath)).size / 1024 / 1024
    };
}

/**
 * Build Windows System Control MCP (Python + UV → Standalone .exe)
 */
async function buildWindowsMCP() {
    log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'bright');
    log('🐍 Building Windows System Control MCP (Python)', 'bright');
    log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', 'bright');

    const mcpDir = path.join(MCP_PACKAGES_DIR, 'windows-mcp');
    const buildDir = path.join(DIST_DIR, 'windows-mcp-build');
    const exeName = 'windows-mcp.exe';

    await ensureDir(buildDir);

    // Step 1: Read manifest
    const manifestPath = path.join(mcpDir, 'manifest.json');
    const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf-8'));
    log(`📄 Loaded manifest: ${manifest.name} v${manifest.version}`, 'yellow');

    // Step 2: Install dependencies with UV (if not already installed)
    log('\n📦 Installing dependencies with UV...', 'yellow');
    exec('uv sync', mcpDir);

    // Step 3: Install PyInstaller
    log('\n📦 Installing PyInstaller...', 'yellow');
    exec('uv pip install pyinstaller', mcpDir);

    // Step 4: Build with PyInstaller
    log('\n🔨 Building executable with PyInstaller...', 'yellow');

    const pyinstallerCmd = `uv run pyinstaller --onefile --name "${path.parse(exeName).name}" --distpath "${buildDir}" --workpath "${path.join(buildDir, 'build')}" --specpath "${path.join(buildDir, 'spec')}" --add-data "manifest.json;." --add-data "assets;assets" --hidden-import fastmcp --hidden-import humancursor --hidden-import pywinauto --hidden-import uiautomation --hidden-import psutil --hidden-import pyautogui --hidden-import pillow --hidden-import click --hidden-import fuzzywuzzy --hidden-import markdownify --hidden-import pdfplumber --hidden-import pygetwindow --hidden-import requests --hidden-import tabulate --console main.py`;

    exec(pyinstallerCmd, mcpDir);

    // Step 5: Copy manifest
    await fs.copyFile(manifestPath, path.join(buildDir, 'manifest.json'));

    // Step 6: Copy assets if they exist
    const assetsDir = path.join(mcpDir, 'assets');
    try {
        await fs.access(assetsDir);
        const assetsDestDir = path.join(buildDir, 'assets');
        await ensureDir(assetsDestDir);
        await exec(`xcopy "${assetsDir}" "${assetsDestDir}" /E /I /Y`, mcpDir);
    } catch (error) {
        log('⚠️  No assets directory found, skipping...', 'yellow');
    }

    // Step 7: Create ZIP archive
    const zipPath = path.join(DIST_DIR, `windows-mcp-v${manifest.version}.zip`);
    await createZipArchive(buildDir, zipPath);

    // Step 8: Calculate checksum
    const checksum = await calculateChecksum(zipPath);
    log(`🔒 Checksum: ${checksum}`, 'green');

    return {
        mcp_id: 'windows-mcp',
        name: manifest.name,
        version: manifest.version,
        exe_name: exeName,
        zip_path: zipPath,
        checksum,
        size_mb: (await fs.stat(zipPath)).size / 1024 / 1024
    };
}

/**
 * Build Web Fetch MCP (Python → Standalone .exe)
 */
async function buildFetchMCP() {
    log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'bright');
    log('🌐 Building Web Fetch MCP (Python)', 'bright');
    log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n', 'bright');

    const mcpDir = path.join(MCP_PACKAGES_DIR, 'fetch-mcp');
    const buildDir = path.join(DIST_DIR, 'fetch-mcp-build');
    const exeName = 'fetch-mcp.exe';

    await ensureDir(buildDir);

    // Step 1: Read manifest
    const manifestPath = path.join(mcpDir, 'manifest.json');
    const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf-8'));
    log(`📄 Loaded manifest: ${manifest.name} v${manifest.version}`, 'yellow');

    // Step 2: Create a temporary directory for building
    const tempBuildDir = path.join(mcpDir, 'build-temp');
    await ensureDir(tempBuildDir);

    // Step 3: Install dependencies
    log('\n📦 Installing mcp-server-fetch and dependencies...', 'yellow');
    exec(`pip install --target "${tempBuildDir}" mcp-server-fetch>=2025.4.7 httpx markdownify mcp protego pydantic readabilipy requests beautifulsoup4 html5lib lxml`);

    // Step 4: Create entry point script
    const entryScript = `#!/usr/bin/env python3
"""
Web Fetch MCP - Standalone Entry Point
Auto-generated for PyInstaller
"""

import sys
import os

# Add dependencies to path
sys.path.insert(0, os.path.dirname(__file__))

# Run the MCP server
from mcp_server_fetch import main

if __name__ == "__main__":
    main()
`;

    const entryScriptPath = path.join(tempBuildDir, 'main.py');
    await fs.writeFile(entryScriptPath, entryScript);

    // Step 5: Copy manifest
    await fs.copyFile(manifestPath, path.join(tempBuildDir, 'manifest.json'));

    // Step 6: Install PyInstaller
    log('\n📦 Installing PyInstaller...', 'yellow');
    exec('pip install pyinstaller');

    // Step 7: Build with PyInstaller
    log('\n🔨 Building executable with PyInstaller...', 'yellow');

    const pyinstallerCmd = `pyinstaller --onefile --name "${path.parse(exeName).name}" --distpath "${buildDir}" --workpath "${path.join(tempBuildDir, 'build')}" --specpath "${path.join(tempBuildDir, 'spec')}" --add-data "manifest.json;." --hidden-import mcp_server_fetch --hidden-import httpx --hidden-import markdownify --hidden-import mcp --hidden-import protego --hidden-import pydantic --hidden-import readabilipy --hidden-import requests --hidden-import beautifulsoup4 --hidden-import html5lib --hidden-import lxml --console main.py`;

    exec(pyinstallerCmd, tempBuildDir);

    // Step 8: Copy manifest to build dir
    await fs.copyFile(manifestPath, path.join(buildDir, 'manifest.json'));

    // Step 9: Create ZIP archive
    const zipPath = path.join(DIST_DIR, `fetch-mcp-v${manifest.version}.zip`);
    await createZipArchive(buildDir, zipPath);

    // Step 10: Calculate checksum
    const checksum = await calculateChecksum(zipPath);
    log(`🔒 Checksum: ${checksum}`, 'green');

    // Clean up temp directory
    await fs.rm(tempBuildDir, { recursive: true, force: true });

    return {
        mcp_id: 'fetch-mcp',
        name: manifest.name,
        version: manifest.version,
        exe_name: exeName,
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
    log('║   MCP BUILD SYSTEM - Standalone Executables   ║', 'bright');
    log('╚═══════════════════════════════════════════════╝\n', 'bright');

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
            platform: 'win32',
            package_name: 'windows-base',
            version: '1.0.0',
            mcps: results.map(r => ({
                mcp_id: r.mcp_id,
                name: r.name,
                version: r.version,
                executable: {
                    filename: r.exe_name,
                    type: 'standalone',
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

        log('📦 Built MCPs:', 'bright');
        results.forEach(r => {
            log(`   • ${r.name} v${r.version}`, 'green');
            log(`     - Executable: ${r.exe_name}`, 'yellow');
            log(`     - Archive: ${path.basename(r.zip_path)} (${r.size_mb.toFixed(2)} MB)`, 'yellow');
            log(`     - Checksum: ${r.checksum.substring(0, 50)}...`, 'yellow');
        });

        log(`\n📄 Build manifest: ${manifestPath}`, 'green');
        log(`\n🎉 All MCPs successfully packaged as standalone executables!`, 'bright');

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

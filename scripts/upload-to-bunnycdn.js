#!/usr/bin/env node
/**
 * BunnyCDN Upload Script
 *
 * Uploads MCP packages to BunnyCDN storage
 * Requires environment variables or .env file with BunnyCDN credentials
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

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

// Try to load .env file if it exists
const envPath = path.join(__dirname, '..', '.env');
if (fs.existsSync(envPath)) {
    require('dotenv').config({ path: envPath });
}

// Configuration from environment variables
const BUNNY_STORAGE_ZONE = process.env.BUNNY_STORAGE_ZONE;
const BUNNY_ACCESS_KEY = process.env.BUNNY_ACCESS_KEY;
const BUNNY_REGION = process.env.BUNNY_REGION || 'falkenstein';

// Storage endpoint mapping
const STORAGE_ENDPOINTS = {
    'falkenstein': 'storage.bunnycdn.com',
    'ny': 'ny.storage.bunnycdn.com',
    'la': 'la.storage.bunnycdn.com',
    'sg': 'sg.storage.bunnycdn.com',
    'syd': 'syd.storage.bunnycdn.com',
    'uk': 'uk.storage.bunnycdn.com',
};

const STORAGE_HOST = STORAGE_ENDPOINTS[BUNNY_REGION] || 'storage.bunnycdn.com';

/**
 * Upload file to BunnyCDN storage
 */
async function uploadFile(localPath, remotePath) {
    return new Promise((resolve, reject) => {
        // Validate credentials
        if (!BUNNY_STORAGE_ZONE || !BUNNY_ACCESS_KEY) {
            reject(new Error('Missing BunnyCDN credentials. Set BUNNY_STORAGE_ZONE and BUNNY_ACCESS_KEY environment variables.'));
            return;
        }

        // Read file
        const fileBuffer = fs.readFileSync(localPath);
        const fileSizeMB = (fileBuffer.length / 1024 / 1024).toFixed(2);

        log(`\n📤 Uploading: ${path.basename(localPath)} (${fileSizeMB} MB)`, 'yellow');
        log(`📍 Destination: ${remotePath}`, 'blue');

        // Prepare request
        const options = {
            hostname: STORAGE_HOST,
            path: `/${BUNNY_STORAGE_ZONE}${remotePath}`,
            method: 'PUT',
            headers: {
                'AccessKey': BUNNY_ACCESS_KEY,
                'Content-Type': 'application/octet-stream',
                'Content-Length': fileBuffer.length
            }
        };

        const req = https.request(options, (res) => {
            let responseData = '';

            res.on('data', (chunk) => {
                responseData += chunk;
            });

            res.on('end', () => {
                if (res.statusCode === 201) {
                    log(`✅ Upload successful!`, 'green');
                    log(`   Status: ${res.statusCode} ${res.statusMessage}`, 'green');
                    resolve({
                        success: true,
                        statusCode: res.statusCode,
                        remotePath
                    });
                } else {
                    log(`❌ Upload failed!`, 'red');
                    log(`   Status: ${res.statusCode} ${res.statusMessage}`, 'red');
                    log(`   Response: ${responseData}`, 'red');
                    reject(new Error(`Upload failed with status ${res.statusCode}: ${responseData}`));
                }
            });
        });

        req.on('error', (error) => {
            log(`❌ Upload error: ${error.message}`, 'red');
            reject(error);
        });

        // Write file data
        req.write(fileBuffer);
        req.end();
    });
}

/**
 * Main upload process
 */
async function main() {
    log('\n╔═══════════════════════════════════════════════╗', 'bright');
    log('║       BunnyCDN Upload - MCP Packages          ║', 'bright');
    log('╚═══════════════════════════════════════════════╝\n', 'bright');

    const PROJECT_ROOT = path.resolve(__dirname, '..');

    // Files to upload
    const uploads = [
        {
            local: 'D:\\development\\python\\blender-mcp\\dist\\blender-mcp-v1.6.3-win32.zip',
            remote: '/mcps/creative/blender-mcp/blender-mcp-v1.6.3-win32.zip'
        }
    ];

    try {
        log('🔧 Configuration:', 'yellow');
        log(`   Storage Zone: ${BUNNY_STORAGE_ZONE}`, 'blue');
        log(`   Region: ${BUNNY_REGION}`, 'blue');
        log(`   Endpoint: ${STORAGE_HOST}`, 'blue');

        for (const upload of uploads) {
            if (!fs.existsSync(upload.local)) {
                log(`\n⚠️  File not found: ${upload.local}`, 'yellow');
                log(`   Skipping...`, 'yellow');
                continue;
            }

            await uploadFile(upload.local, upload.remote);
        }

        log('\n╔═══════════════════════════════════════════════╗', 'green');
        log('║            ✅ UPLOAD COMPLETE!                ║', 'green');
        log('╚═══════════════════════════════════════════════╝\n', 'green');

    } catch (error) {
        log('\n❌ UPLOAD FAILED!', 'red');
        log(`Error: ${error.message}`, 'red');
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

module.exports = { uploadFile };

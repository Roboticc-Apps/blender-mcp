# MCP Build and Upload Guide for OneController

**Date**: 2025-12-22 (Updated)
**Purpose**: Document the complete process for building, packaging, and deploying MCPs to OneController marketplace

> **IMPORTANT PROJECT PATHS**:
> - **Windows MCP**: `D:\development\python\windows-mcp` (SEPARATE repo)
> - **OneController**: `D:\development\python\one_controller`
> - **Upload Script**: `D:\development\python\one_controller\scripts\upload-to-bunnycdn.js`

---

## Table of Contents

1. [Deployment Checklist](#deployment-checklist) ⚠️ **READ FIRST**
2. [Architecture Overview](#architecture-overview)
3. [Database Schema](#database-schema)
4. [MCP Package Structure](#mcp-package-structure)
5. [Build Process](#build-process)
6. [Upload to Bunny CDN](#upload-to-bunny-cdn)
7. [Database Registration](#database-registration)
8. [Playwright MCP Implementation](#playwright-mcp-implementation)
9. [Testing](#testing)

---

## Deployment Checklist

> ⚠️ **MANDATORY**: Complete this checklist for EVERY MCP build and deployment. Check database first - some items may already be done.

### Pre-Deployment Verification

```
□ Read and understand this guide before starting
□ Verify you're using the correct Supabase project ID: icajylcaekqydjsbyssp
□ ⚠️ BUMP VERSION NUMBER in manifest.json BEFORE building
  - NEVER reuse the same version number
  - Use semantic versioning: major.minor.patch (e.g., 1.0.5 → 1.0.6)
  - Check current version: query mcp_servers table first
```

### Build Phase

```
□ Version number in manifest.json is NEW (higher than database)
□ Executable builds successfully without errors
□ Run test to verify executable works (test_core_tools.py or similar)
□ ZIP package created in dist/ folder
□ SHA-256 checksum generated and saved to .sha256 file
□ Note the exact file size in bytes FROM THE BUILT FILE (not from memory)
```

### Upload Phase (Bunny CDN)

```
□ Upload to correct directory structure:
  /mcps/{category}/{mcp-slug}/{mcp-slug}-v{version}-{platform}.zip

  Examples:
  - /mcps/productivity/oc-sheet-mcp/oc-sheet-mcp-v1.0.5-win32.zip
  - /mcps/browser/playwright-mcp/playwright-mcp-v2025.12.04-win32.zip
  - /mcps/windows/windows-mcp/windows-mcp-v0.5.35-win32.zip

□ Verify upload successful (HTTP 201 response)
□ Test CDN URL is accessible: https://onecontroller.b-cdn.net/mcps/...
□ ⚠️ GET ACTUAL FILE SIZE FROM CDN (use curl -I to check Content-Length header)
  - Command: curl -sI "https://onecontroller.b-cdn.net/mcps/..." | grep Content-Length
  - Use THIS value for size_bytes in database, NOT the local file size
```

### Database Updates (Supabase)

**Use Supabase MCP with project ID: `icajylcaekqydjsbyssp`**

#### 1. mcp_servers Table
```
□ Check if MCP entry exists (query by slug)
□ If new: INSERT complete record
□ If updating: UPDATE with new version, checksum, size_bytes, cdn_url
□ Verify manifest JSONB includes "platforms" field (CRITICAL for marketplace visibility)
□ Verify checksum matches the .sha256 file exactly
□ Verify size_bytes matches actual file size
□ Verify cdn_url points to correct Bunny CDN path
```

#### 2. unified_commands Table
```
□ Query existing commands for this MCP
□ Add any NEW tools as unified_commands
□ Verify all tools from manifest.json have corresponding commands
□ Verify command_triggers are set for voice activation
□ Verify mcp_server_id references correct UUID from mcp_servers
□ Verify is_enabled = true for all commands
```

#### 3. app_prompts Table
```
□ Query existing prompt for this MCP (by app_identifier)
□ If new: INSERT comprehensive app_prompt with:
  - All available tools and their parameters
  - Common voice command mappings
  - Best practices for AI agent
□ If updating: UPDATE prompt_text with any new tools/features
□ Verify is_active = true
```

### Post-Deployment Verification

```
□ Query mcp_servers to confirm all fields are correct
□ Query unified_commands to confirm command count matches tool count
□ Query app_prompts to confirm prompt exists and is active
□ Verify MCP appears in marketplace (may need to check platform filter)
```

### Quick Verification Queries

```sql
-- Check mcp_servers entry
SELECT slug, latest_version, checksum, size_bytes,
       manifest->'platforms' as platforms,
       cdn_url
FROM mcp_servers WHERE slug = 'your-mcp-slug';

-- Count unified_commands
SELECT COUNT(*) FROM unified_commands WHERE app_identifier = 'your-mcp-slug';

-- Check app_prompts
SELECT app_identifier, is_active, LENGTH(prompt_text) as prompt_length
FROM app_prompts WHERE app_identifier = 'your-mcp-slug';
```

### Common Issues Checklist

| Issue | Cause | Fix |
|-------|-------|-----|
| MCP not in marketplace | `manifest.platforms` missing | Add platforms to manifest JSONB |
| Wrong checksum | Rebuilt after upload | Re-upload and update DB |
| **Installation fails** | **size_bytes mismatch** | **curl -I CDN URL to get actual Content-Length, update DB** |
| **Same version conflict** | **Didn't bump version** | **ALWAYS bump version in manifest.json before building** |
| Tools not working | Missing unified_commands | Add commands for each tool |
| AI doesn't know how to use MCP | Missing app_prompt | Create app_prompt with instructions |
| File download fails | Wrong CDN path | Verify directory structure |

---

## Architecture Overview

### MCP Lifecycle in OneController

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. BUILD PHASE                                                   │
│    • Create manifest.json                                        │
│    • Write index.js wrapper                                      │
│    • Install dependencies (npm install)                          │
│    • Bundle as executable (pkg for Node.js, PyInstaller for Python)│
│    • Create ZIP archive                                          │
│    • Generate checksum                                           │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. UPLOAD PHASE                                                  │
│    • Upload ZIP to Bunny CDN                                     │
│    • Get CDN URL                                                 │
│    • Register in Supabase mcp_servers table                      │
│    • Tools are read from manifest.json (no separate table)       │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. MARKETPLACE PHASE                                             │
│    • User browses marketplace (Settings > MCPs > Marketplace)    │
│    • MCPs fetched from Supabase (filtered by platform)          │
│    • User clicks "Install"                                       │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. INSTALLATION PHASE                                            │
│    • Frontend calls IPC: mcp-install                             │
│    • MCPManager.installMCP() downloads from CDN URL              │
│    • Extract to: AppData/OneController/mcps/{mcp_id}/            │
│    • Save manifest.json                                          │
│    • Record in user_mcp_installations table                      │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. RUNTIME PHASE                                                 │
│    • User clicks "Start"                                         │
│    • MCPManager spawns process (node index.js)                   │
│    • JSON-RPC communication via stdio                            │
│    • Tools available for voice commands                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Table: `mcp_servers`

```sql
CREATE TABLE public.mcp_servers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(255) UNIQUE NOT NULL,      -- e.g., "google-workspace-mcp"
    name VARCHAR(255) NOT NULL,             -- e.g., "Google Workspace MCP"
    npm_package VARCHAR(255) NOT NULL,      -- Package identifier (can be slug for non-npm packages)
    github_repo VARCHAR(255),               -- GitHub repository URL
    description TEXT NOT NULL,              -- Short description
    long_description TEXT,                  -- Detailed description
    documentation_url TEXT,                 -- Documentation URL
    latest_version VARCHAR(50) NOT NULL,    -- e.g., "1.6.0"
    install_command TEXT NOT NULL,          -- CRITICAL: Executable name (e.g., "mcp-name.exe" or "index.js")
    min_node_version VARCHAR(20),           -- e.g., "18.0.0" (NULL for Python packages)
    estimated_size_mb INTEGER,              -- Estimated installation size
    platforms TEXT[] DEFAULT ARRAY['win32', 'darwin', 'linux'],
    requires_admin BOOLEAN DEFAULT false,
    dependencies JSONB DEFAULT '[]',        -- Additional dependencies
    category VARCHAR(100) NOT NULL,         -- e.g., "productivity", "browser", "base"
    tags TEXT[] DEFAULT '{}',               -- Search tags
    downloads INTEGER DEFAULT 0,
    rating NUMERIC(3,2) DEFAULT 0.0,
    rating_count INTEGER DEFAULT 0,
    is_official BOOLEAN DEFAULT false,      -- Official OneController package
    is_verified BOOLEAN DEFAULT false,      -- Verified by OneController team
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    cdn_url TEXT,                           -- Bunny CDN URL for ZIP package
    checksum TEXT,                          -- SHA-256 checksum
    size_bytes BIGINT,                      -- Exact file size in bytes
    manifest JSONB,                         -- Complete manifest.json as JSONB (includes tools array)
    is_base_package BOOLEAN DEFAULT false,
    permission_level VARCHAR(50) DEFAULT 'safe',  -- "safe", "moderate", "dangerous"
    installation_status VARCHAR(50) DEFAULT 'available',
    display_name VARCHAR(255)
);

-- Indexes
CREATE INDEX idx_mcp_servers_slug ON mcp_servers(slug);
CREATE INDEX idx_mcp_servers_category ON mcp_servers(category);
CREATE INDEX idx_mcp_servers_tags ON mcp_servers USING gin(tags);
CREATE INDEX idx_mcp_servers_active ON mcp_servers(is_active) WHERE is_active = true;
CREATE INDEX idx_mcp_servers_base_package ON mcp_servers(is_base_package) WHERE is_base_package = true;
CREATE INDEX idx_mcp_servers_permission ON mcp_servers(permission_level);
```

**Important Notes**:

1. **`install_command` Field**: This field MUST contain the executable filename (e.g., `"windows-mcp.exe"` or `"index.js"`), NOT installation instructions. OneController uses this value to locate and run the MCP executable after installation.

2. **Tools Storage**: Tools are defined in the MCP's `manifest.json` file and stored in the `manifest` JSONB column. There is no separate `mcp_tools` table. The manifest contains complete tool definitions including names, descriptions, categories, and input schemas.

### Table: `user_mcp_installations`

```sql
CREATE TABLE public.user_mcp_installations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    mcp_server_id UUID REFERENCES mcp_servers(id) ON DELETE CASCADE,

    installed_version TEXT,
    install_path TEXT,
    status TEXT DEFAULT 'stopped',  -- "active", "stopped", "error"
    server_process_id TEXT,         -- For tracking running process

    installed_at TIMESTAMP DEFAULT NOW(),
    last_started_at TIMESTAMP,

    UNIQUE(user_id, mcp_server_id)
);
```

---

## MCP Package Structure

### Directory Layout

```
playwright-mcp/
├── manifest.json          # MCP metadata and configuration
├── index.js              # Entry point / wrapper
├── package.json          # Node.js dependencies
├── package-lock.json     # Dependency lock file
├── node_modules/         # Dependencies (bundled)
│   └── @playwright/...
└── dist/                 # Build output (optional)
    └── playwright-mcp.exe (Windows)
```

### manifest.json Structure

```json
{
  "id": "playwright-mcp",
  "name": "Playwright MCP",
  "version": "2025.12.04",
  "description": "Browser automation using Playwright. Navigate, fill forms, extract data from web pages.",
  "author": "Microsoft",
  "category": "browser",
  "permission_level": "moderate",
  "platforms": ["win32", "darwin", "linux"],

  "server": {
    "type": "node",
    "entrypoint": "index.js",
    "port": 3200
  },

  "dependencies": {
    "node_packages": [
      "@playwright/test@^1.40.0",
      "@modelcontextprotocol/sdk@^0.1.0"
    ]
  },

  "requirements": {
    "min_node_version": "18.0.0",
    "disk_space_mb": 300
  },

  "tools": [
    {
      "name": "navigate",
      "description": "Navigate to a URL",
      "category": "browser",
      "inputSchema": {
        "type": "object",
        "properties": {
          "url": {
            "type": "string",
            "description": "URL to navigate to"
          }
        },
        "required": ["url"]
      }
    },
    {
      "name": "fill",
      "description": "Fill an input field",
      "category": "browser",
      "inputSchema": {
        "type": "object",
        "properties": {
          "selector": {
            "type": "string",
            "description": "CSS selector for the input"
          },
          "value": {
            "type": "string",
            "description": "Value to fill"
          }
        },
        "required": ["selector", "value"]
      }
    },
    {
      "name": "click",
      "description": "Click an element",
      "category": "browser",
      "inputSchema": {
        "type": "object",
        "properties": {
          "selector": {
            "type": "string",
            "description": "CSS selector for the element"
          }
        },
        "required": ["selector"]
      }
    }
  ]
}
```

### ⚠️ CRITICAL: manifest.platforms Field Requirement

**THE MCP WILL NOT APPEAR IN THE MARKETPLACE IF THIS IS MISSING!**

The `platforms` field in `manifest.json` is **MANDATORY** and must be included in **BOTH**:
1. The `manifest.json` file in your ZIP package
2. The `manifest` JSONB column in the database

**Why This Matters:**
- The marketplace edge function filters MCPs by platform using `manifest.platforms`
- If this field is missing or empty, the MCP **will not show up** for any platform
- The ON CONFLICT clause must update the `manifest` field to ensure platforms are synced

**Common Mistake:**
```sql
-- ❌ WRONG - ON CONFLICT doesn't update manifest field
ON CONFLICT (slug) DO UPDATE SET
    latest_version = EXCLUDED.latest_version,
    cdn_url = EXCLUDED.cdn_url;
    -- Missing: manifest = EXCLUDED.manifest !!!

-- ✅ CORRECT - Always update manifest field
ON CONFLICT (slug) DO UPDATE SET
    latest_version = EXCLUDED.latest_version,
    cdn_url = EXCLUDED.cdn_url,
    manifest = EXCLUDED.manifest,  -- CRITICAL!
    updated_at = NOW();
```

**Valid Platform Values:**
- `"win32"` - Windows
- `"darwin"` - macOS
- `"linux"` - Linux

**Example:**
```json
{
  "id": "my-mcp",
  "name": "My MCP",
  "platforms": ["win32"],  // REQUIRED - Even if only one platform!
  "tools": [...]
}
```

**Troubleshooting:**
If your MCP doesn't appear in the marketplace:
1. Check the database: `SELECT slug, manifest->'platforms' FROM mcp_servers WHERE slug = 'your-mcp';`
2. Verify the platforms field exists and has values: `["win32"]`
3. If missing, update: `UPDATE mcp_servers SET manifest = jsonb_set(manifest, '{platforms}', '["win32"]') WHERE slug = 'your-mcp';`

---

### index.js Wrapper

```javascript
#!/usr/bin/env node

/**
 * Playwright MCP Server
 * Browser automation via Model Context Protocol
 */

const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const { chromium } = require('@playwright/test');

// MCP Server implementation
class PlaywrightMCPServer {
    constructor() {
        this.server = new Server(
            {
                name: 'playwright-mcp',
                version: '2025.12.04',
            },
            {
                capabilities: {
                    tools: {},
                },
            }
        );

        this.browser = null;
        this.page = null;

        this.setupToolHandlers();
    }

    setupToolHandlers() {
        // Register tools
        this.server.setRequestHandler('tools/list', async () => {
            return {
                tools: [
                    {
                        name: 'navigate',
                        description: 'Navigate to a URL',
                        inputSchema: {
                            type: 'object',
                            properties: {
                                url: { type: 'string' }
                            },
                            required: ['url']
                        }
                    },
                    {
                        name: 'fill',
                        description: 'Fill an input field',
                        inputSchema: {
                            type: 'object',
                            properties: {
                                selector: { type: 'string' },
                                value: { type: 'string' }
                            },
                            required: ['selector', 'value']
                        }
                    },
                    {
                        name: 'click',
                        description: 'Click an element',
                        inputSchema: {
                            type: 'object',
                            properties: {
                                selector: { type: 'string' }
                            },
                            required: ['selector']
                        }
                    }
                ]
            };
        });

        // Handle tool calls
        this.server.setRequestHandler('tools/call', async (request) => {
            const { name, arguments: args } = request.params;

            try {
                switch (name) {
                    case 'navigate':
                        return await this.navigate(args.url);
                    case 'fill':
                        return await this.fill(args.selector, args.value);
                    case 'click':
                        return await this.click(args.selector);
                    default:
                        throw new Error(`Unknown tool: ${name}`);
                }
            } catch (error) {
                return {
                    content: [{
                        type: 'text',
                        text: `Error: ${error.message}`
                    }],
                    isError: true
                };
            }
        });
    }

    async ensureBrowser() {
        if (!this.browser) {
            this.browser = await chromium.launch({ headless: false });
            this.page = await this.browser.newPage();
        }
    }

    async navigate(url) {
        await this.ensureBrowser();
        await this.page.goto(url);
        return {
            content: [{
                type: 'text',
                text: `Navigated to ${url}`
            }]
        };
    }

    async fill(selector, value) {
        await this.ensureBrowser();
        await this.page.fill(selector, value);
        return {
            content: [{
                type: 'text',
                text: `Filled ${selector} with value`
            }]
        };
    }

    async click(selector) {
        await this.ensureBrowser();
        await this.page.click(selector);
        return {
            content: [{
                type: 'text',
                text: `Clicked ${selector}`
            }]
        };
    }

    async start() {
        const transport = new StdioServerTransport();
        await this.server.connect(transport);
        console.error('Playwright MCP Server started');
    }
}

// Start server
const server = new PlaywrightMCPServer();
server.start().catch(console.error);
```

---

## Build Process

The build process differs based on MCP type (Node.js vs Python):

---

### 🟢 Node.js MCP Build Process

**Example**: Playwright MCP, Filesystem MCP

#### Step 1: Create MCP Directory

```bash
mkdir -p mcp-packages/browser/playwright-mcp
cd mcp-packages/browser/playwright-mcp
```

#### Step 2: Create manifest.json

```json
{
  "id": "playwright-mcp",
  "name": "Playwright MCP",
  "version": "2025.12.04",
  "platforms": ["win32", "darwin", "linux"],
  "server": {
    "type": "node",
    "entrypoint": "index.js"
  },
  "tools": [...]
}
```

#### Step 3: Create index.js

Implement MCP server with Model Context Protocol SDK.

#### Step 4: Install Dependencies

```bash
npm install
```

#### Step 5: Bundle as Executable

**Required: Use pkg to bundle as standalone executable**
```bash
npm install -g pkg
pkg index.js --targets node18-win-x64 --output dist/playwright-mcp.exe
```

> **Note**: Node.js MCPs must be bundled as standalone executables. Do not ship raw source code with node_modules.

#### Step 6: Create ZIP Package

```bash
# Navigate to dist folder
cd dist

# Create ZIP with executable and manifest
powershell Compress-Archive -Path playwright-mcp.exe,manifest.json -DestinationPath playwright-mcp-v2025.12.04-win32.zip
```

#### Step 7: Generate Checksum

```bash
powershell (Get-FileHash playwright-mcp-v2025.12.04-win32.zip -Algorithm SHA256).Hash
```

---

### 🔵 Python MCP Build Process

**Example**: Windows MCP

#### Step 1: MCP Directory Structure

**Windows MCP Location**: `D:\development\python\windows-mcp`

> **IMPORTANT**: The windows-mcp project lives in a SEPARATE directory from one_controller.
> Do NOT confuse with the old path `mcp-packages/windows-base/windows-mcp` which is deprecated.

```bash
cd D:\development\python\windows-mcp
```

Structure:
```
D:\development\python\windows-mcp\
├── main.py              # Entry point
├── src/                 # Source modules
│   ├── desktop/         # Desktop automation (service.py, views.py, config.py)
│   └── tree/            # UI tree scanning
├── manifest.json        # MCP metadata
├── pyproject.toml       # Python dependencies
├── windows-mcp.spec     # PyInstaller spec file
├── build.ps1            # Build script
├── test_state_tool.py   # Test script for State-Tool
└── .venv/               # Virtual environment
```

#### Step 2: Create manifest.json

```json
{
  "id": "windows-mcp",
  "name": "Windows System Control MCP",
  "version": "0.5.1",
  "platforms": ["win32"],
  "server": {
    "type": "python",
    "entrypoint": "main.py",
    "command": "uv",
    "args": ["--directory", "${install_path}", "run", "main.py"]
  },
  "dependencies": {
    "python_packages": [...],
    "system_packages": ["uv"]
  },
  "tools": [...]
}
```

#### Step 3: Create PyInstaller Spec File

**⚠️ CRITICAL: FastMCP 2.14.1+ Requirement**

If your MCP uses FastMCP 2.14.1 or later, you MUST properly bundle the lupa library (Python-Lua bindings) and fakeredis. FastMCP uses pydocket for background tasks, which depends on fakeredis[lua], which requires lupa's compiled C extensions (.pyd files on Windows).

**Without proper bundling, you'll get:**
- `ModuleNotFoundError: No module named 'lupa.lua51'`
- `ModuleNotFoundError: No module named 'DLFCN'`
- `unknown command 'evalsha'` (if lupa partially loads but binaries are missing)

**The Solution:**

Use `collect_all()` to bundle **BOTH** data files AND binary files (.pyd/.so) for lupa and fakeredis:

```python
# windows-mcp.spec
from PyInstaller.utils.hooks import copy_metadata, collect_data_files, collect_all

datas = []
binaries = []

# Collect metadata for FastMCP and MCP
datas += copy_metadata('fastmcp')
datas += copy_metadata('mcp')

# CRITICAL: Collect all fakeredis files including commands.json
# fakeredis needs its data files for Lua command definitions
fakeredis_data = collect_all('fakeredis')
if fakeredis_data[0]:
    datas += fakeredis_data[0]  # datas
if fakeredis_data[1]:
    binaries += fakeredis_data[1]  # binaries
hiddenimports_fakeredis = fakeredis_data[2] if fakeredis_data[2] else []

# CRITICAL: Collect lupa files (both data and binaries)
# lupa contains compiled .pyd/.so files that MUST be included
# Without these, you'll get "ModuleNotFoundError: No module named 'lupa.lua51'" errors
lupa_all = collect_all('lupa')
if lupa_all[0]:
    datas += lupa_all[0]  # data files
if lupa_all[1]:
    binaries += lupa_all[1]  # binary files (.pyd/.so) - CRITICAL!
hiddenimports_lupa = lupa_all[2] if lupa_all[2] else []

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,  # CRITICAL: Must include collected binaries
    datas=datas,  # CRITICAL: Must include collected data files
    hiddenimports=[
        'fastmcp',
        'mcp',
        'lupa',
        'humancursor',
        'uiautomation',
    ] + hiddenimports_fakeredis + hiddenimports_lupa,  # Add collected hidden imports
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='windows-mcp',
    debug=False,
    strip=False,
    upx=True,
    console=True,  # MUST be True for stdio communication (JSON-RPC)
)
```

**Why This Is Critical:**

1. **collect_all() Returns 3 Things:**
   - `[0]` = Data files (JSON, text, etc.)
   - `[1]` = Binary files (.pyd, .so, .dll) - **MUST include for lupa!**
   - `[2]` = Hidden imports (Python modules)

2. **lupa Binary Extensions:**
   - lupa ships with compiled Lua bindings: lua51, lua52, lua53, lua54, luajit20, luajit21
   - These are .pyd files on Windows that must be bundled
   - Without them, Python can't load the Lua runtime

3. **Common Mistake:**
   - Using `collect_data_files('lupa')` only gets data files, not binaries
   - Using `hiddenimports=['lupa']` only tells PyInstaller to look for lupa, but doesn't bundle the .pyd files
   - You MUST use `collect_all()` and add both `datas` and `binaries`

#### Step 4: Create Build Script

```powershell
# build.ps1
param(
    [string]$Version = "0.5.1",
    [string]$Platform = "win32"
)

Set-Location $PSScriptRoot

# 1. Clean previous builds
Remove-Item "build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "dist\windows-mcp.exe" -Force -ErrorAction SilentlyContinue

# 2. Bundle with PyInstaller
& .\.venv\Scripts\pyinstaller.exe --clean windows-mcp.spec

# 3. Copy additional files to dist
Copy-Item "manifest.json" -Destination "dist\manifest.json" -Force
Copy-Item "README.md" -Destination "dist\README.md" -Force
Copy-Item "LICENSE.md" -Destination "dist\LICENSE.md" -Force

# 4. Create ZIP package
$zipName = "windows-mcp-v$Version-$Platform.zip"
$filesToZip = @(
    "dist\windows-mcp.exe",
    "dist\manifest.json",
    "dist\README.md",
    "dist\LICENSE.md"
)

Compress-Archive -Path $filesToZip -DestinationPath "dist\$zipName" -Force

# 5. Generate checksum
$hash = (Get-FileHash "dist\$zipName" -Algorithm SHA256).Hash
Set-Content -Path "dist\$zipName.sha256" -Value "$hash  $zipName"

Write-Host "Build complete: dist\$zipName"
Write-Host "SHA-256: $hash"
```

#### Step 5: Run Build

```bash
# From the windows-mcp directory
cd D:\development\python\windows-mcp

# Run with version parameter
powershell -ExecutionPolicy Bypass -Command ".\build.ps1 -Version '0.5.25'"
```

**Output**:
```
D:\development\python\windows-mcp\dist\
├── windows-mcp.exe                      # ~70 MB bundled executable
├── manifest.json
├── README.md
├── LICENSE.md
├── windows-mcp-v0.5.25-win32.zip        # ~70 MB
└── windows-mcp-v0.5.25-win32.zip.sha256
```

#### Step 6: Upload to BunnyCDN

```bash
# From one_controller directory
cd D:\development\python\one_controller
node scripts/upload-to-bunnycdn.js
```

> **Note**: Update the upload script paths in `scripts/upload-to-bunnycdn.js` before uploading.
> The script should point to `D:\development\python\windows-mcp\dist\windows-mcp-vX.X.X-win32.zip`

---

### ⚠️ CRITICAL: Virtual Environment Build Requirement for Python MCPs

**YOU MUST USE VENV PYTHON TO RUN PYINSTALLER OR YOU'LL WASTE HOURS DEBUGGING!**

**Common Mistake That Causes Hours of Debugging:**
```bash
# ❌ WRONG - Uses system Python, bundles wrong packages
pyinstaller --clean your-app.spec

# ❌ WRONG - Even activating venv first doesn't guarantee correct Python
.venv\Scripts\activate
pyinstaller --clean your-app.spec
```

**What Happens When You Do This Wrong:**
1. ✅ Build succeeds with no errors
2. ❌ Executable crashes: `ModuleNotFoundError: No module named 'redis'`
3. 😰 You add `collect_all('redis')` to spec → Still fails with `ModuleNotFoundError: No module named 'opentelemetry'`
4. 😰 You add opentelemetry → Fails with wrapt error
5. 😰 You add wrapt → Fails with cloudpickle error
6. 😱 **HOURS LATER** you're still adding packages one by one...

**Why This Happens:**
- PyInstaller bundles packages from the Python installation it's run with
- System `pyinstaller` uses system Python (which doesn't have your venv packages)
- Adding packages to `hiddenimports` doesn't help if PyInstaller can't find them
- Error messages DON'T tell you the real problem!

**The Correct Way (Use Venv Python Explicitly):**
```bash
# ✅ CORRECT - Explicitly use venv Python
.venv\Scripts\python -m PyInstaller --clean your-app.spec

# ✅ ALSO CORRECT - Use venv's pyinstaller directly
.venv\Scripts\pyinstaller.exe --clean your-app.spec

# Verify you're using the right Python:
where python  # Should show .venv\Scripts\python.exe, NOT C:\Python\...
```

**How to Know You Made This Mistake:**
- Cascading `ModuleNotFoundError` (redis → opentelemetry → wrapt → cloudpickle → ...)
- Each package you add reveals another missing package
- Packages ARE installed in venv (you can import them in Python)
- But PyInstaller can't find them

**The Fix Takes 30 Seconds:**
```bash
# Delete bad build
rm -rf build/ dist/

# Rebuild with venv Python
.venv\Scripts\python -m PyInstaller --clean your-app.spec

# Test - should work immediately!
./dist/your-app.exe
```

---

### 📦 Build Process Comparison

| Step | Node.js MCP | Python MCP |
|------|-------------|------------|
| **Bundler** | pkg (standalone exe) | PyInstaller |
| **Entry Point** | index.js | main.py |
| **Spec File** | package.json | windows-mcp.spec |
| **Build Command** | `pkg index.js` | `.venv\Scripts\python -m PyInstaller --clean windows-mcp.spec` |
| **Output** | Single .exe (~30-50 MB) | Single .exe (~50-100 MB) |
| **Dependencies** | Bundled in exe | Bundled in exe |
| **Executable Size** | 30-50 MB | 50-100 MB |
| **ZIP Contents** | exe + manifest.json | exe + manifest.json + docs |

---

### 🔑 Key Differences

#### Node.js MCPs:
- **Lighter executables** (~30-50 MB)
- **Faster builds** (pkg is quick)
- **Runtime**: Requires Node.js (or use pkg for standalone)
- **Package manager**: npm/yarn
- **Example MCPs**: playwright-mcp, filesystem-mcp

#### Python MCPs:
- **Heavier executables** (~50-100 MB due to Python runtime)
- **Slower builds** (PyInstaller bundles entire runtime)
- **Runtime**: Self-contained (includes Python interpreter)
- **Package manager**: pip/uv
- **Example MCPs**: windows-mcp

---

### 🎨 MCP-UI Build Process (MCPs with UI folder)

**Example**: OC-Sheet-MCP

Some MCPs have a UI component (HTML/CSS/JS) that provides a visual interface. These are identified by `"type": "mcp-ui"` and `"ui_enabled": true` in manifest.json.

#### Directory Structure for MCP-UI

```
D:\development\python\oc-sheet-mcp\
├── server.py            # MCP server entry point
├── manifest.json        # Must have "type": "mcp-ui", "ui_enabled": true
├── ui/                  # UI folder - CRITICAL for MCP-UI!
│   ├── index.html       # Main UI file
│   ├── styles.css       # Styles
│   └── script.js        # UI logic
├── oc-sheet-mcp.spec    # PyInstaller spec file
├── build/               # PyInstaller build artifacts
├── dist/                # Final output
└── .venv/               # Virtual environment
```

#### PyInstaller Spec File for MCP-UI

**CRITICAL**: The UI folder must be included in the PyInstaller `datas` list:

```python
# In your .spec file
datas = []

# Add UI files and manifest - REQUIRED for MCP-UI!
datas += [('ui', 'ui'), ('manifest.json', '.')]

a = Analysis(
    ['server.py'],
    datas=datas,  # UI folder will be bundled inside exe
    # ... rest of config
)
```

#### ZIP Package Contents for MCP-UI

The ZIP must contain:
1. **Executable** (e.g., `oc-sheet-mcp.exe`) - has UI bundled inside
2. **manifest.json** - with `"type": "mcp-ui"`

**IMPORTANT**: The UI folder is ONLY bundled inside the executable, NOT separately in the ZIP. PyInstaller extracts it at runtime.

```powershell
# Create ZIP with exe and manifest only (UI is inside exe)
Compress-Archive -Path 'dist\oc-sheet-mcp.exe', 'manifest.json' -DestinationPath 'dist\oc-sheet-mcp-v1.0.8-win32.zip' -Force
```

#### Common MCP-UI Mistakes

| Issue | Cause | Fix |
|-------|-------|-----|
| Runtime error accessing UI | UI not in spec datas | Add `datas += [('ui', 'ui')]` to spec file |
| manifest.json not found | Not bundled in exe | Add `('manifest.json', '.')` to spec datas |

---

## Upload to Bunny CDN

### Manual Upload

1. **Login to Bunny.net**
   - URL: https://panel.bunny.net/
   - Navigate to Storage Zones
   - Select: `onecontroller` zone

2. **Create Directory Structure**
   ```
   /mcps/browser/playwright-mcp/
   ```

3. **Upload ZIP Files**
   - `playwright-mcp-v2025.12.04-win32.zip`
   - `playwright-mcp-v2025.12.04-darwin.zip`
   - `playwright-mcp-v2025.12.04-linux.zip`

4. **Get CDN URLs**
   ```
   https://onecontroller.b-cdn.net/mcps/browser/playwright-mcp/playwright-mcp-v2025.12.04-win32.zip
   ```

### Programmatic Upload (via Edge Function)

OneController has a `bunny-storage` Edge Function that handles uploads:

```javascript
// Call from backend or script
const { data, error } = await supabase.functions.invoke('bunny-storage', {
    body: {
        action: 'upload',
        path: '/mcps/browser/playwright-mcp/playwright-mcp-v2025.12.04-win32.zip',
        file: fileBuffer,
        contentType: 'application/zip'
    }
});
```

---

## Database Registration

### ⚠️ CRITICAL Pre-Registration Checklist

**BEFORE registering your MCP in the database, verify:**

1. ✅ **manifest.json includes `platforms` array**
   ```json
   {
     "platforms": ["win32"]  // REQUIRED!
   }
   ```

2. ✅ **manifest JSONB in SQL includes `platforms`**
   ```sql
   manifest = '{
     "platforms": ["win32"],  -- MUST be present!
     "tools": [...]
   }'::jsonb
   ```

3. ✅ **ON CONFLICT clause updates `manifest` field**
   ```sql
   ON CONFLICT (slug) DO UPDATE SET
       manifest = EXCLUDED.manifest,  -- CRITICAL!
       updated_at = NOW();
   ```

**If any of these are missing, your MCP WILL NOT appear in the marketplace!**

See the "manifest.platforms Field Requirement" section above for detailed troubleshooting.

---

### Insert into mcp_servers Table

```sql
INSERT INTO public.mcp_servers (
    slug,
    name,
    npm_package,
    github_repo,
    description,
    long_description,
    documentation_url,
    latest_version,
    install_command,
    min_node_version,
    estimated_size_mb,
    platforms,
    requires_admin,
    dependencies,
    category,
    tags,
    is_official,
    is_verified,
    is_active,
    cdn_url,
    checksum,
    size_bytes,
    manifest,
    permission_level,
    display_name
) VALUES (
    'playwright-mcp',
    'Playwright MCP',
    '@microsoft/playwright-mcp',
    'https://github.com/microsoft/playwright-mcp',
    'Browser automation using Playwright. Navigate, fill forms, extract data.',
    'Complete browser automation MCP using Microsoft Playwright. Provides tools for navigating web pages, filling forms, clicking elements, extracting data, taking screenshots, and more.',
    'https://github.com/microsoft/playwright-mcp#readme',
    '2025.12.04',
    'playwright-mcp.exe',  -- IMPORTANT: Executable name (e.g., 'mcp-name.exe' or 'index.js')
    '18.0.0',
    300,
    ARRAY['win32', 'darwin', 'linux'],
    false,
    '[]'::jsonb,
    'browser',
    ARRAY['browser', 'automation', 'playwright', 'scraping', 'testing'],
    false,
    true,
    true,
    'https://onecontroller.b-cdn.net/mcps/browser/playwright-mcp/playwright-mcp-v2025.12.04-win32.zip',
    'abc123...def456',  -- Replace with actual SHA-256 checksum
    256000000,
    '{
        "id": "playwright-mcp",
        "name": "Playwright MCP",
        "version": "2025.12.04",
        "description": "Browser automation using Playwright",
        "category": "browser",
        "permission_level": "moderate",
        "platforms": ["win32", "darwin", "linux"],
        "server": {
            "type": "node",
            "entrypoint": "index.js"
        },
        "tools": [
            {"name": "navigate", "description": "Navigate to a URL", "category": "browser"},
            {"name": "fill", "description": "Fill form fields", "category": "browser"},
            {"name": "click", "description": "Click elements", "category": "browser"}
        ]
    }'::jsonb,
    'moderate',
    'Playwright MCP'
)
ON CONFLICT (slug) DO UPDATE SET
    latest_version = EXCLUDED.latest_version,
    description = EXCLUDED.description,
    long_description = EXCLUDED.long_description,
    cdn_url = EXCLUDED.cdn_url,
    checksum = EXCLUDED.checksum,
    size_bytes = EXCLUDED.size_bytes,
    manifest = EXCLUDED.manifest,  -- CRITICAL: Must update to sync platforms field!
    tags = EXCLUDED.tags,
    updated_at = NOW();
```

**Important**: After registration, the MCP's tools will be automatically read from the `manifest.json` file included in the ZIP package when users install the MCP. Tools are not stored in a separate database table - they are defined in the manifest and parsed at runtime.

---

## Playwright MCP Implementation

### Quick Start Guide

1. **Create manifest.json** (see structure above)
2. **Create index.js** (see template above)
3. **Install dependencies**:
   ```bash
   npm install @playwright/test @modelcontextprotocol/sdk
   ```
4. **Test locally**:
   ```bash
   node index.js
   # Server starts and waits for JSON-RPC via stdin/stdout
   ```
5. **Build and package** (see Build Process section)
6. **Upload to Bunny CDN** (see Upload section)
7. **Register in database** (see Database Registration section)

### Recommended Tools to Implement

1. **navigate(url)** - Go to URL
2. **fill(selector, value)** - Fill form fields
3. **click(selector)** - Click elements
4. **getText(selector)** - Extract text
5. **screenshot(path)** - Capture screenshots
6. **waitForSelector(selector)** - Wait for elements
7. **evaluate(script)** - Execute JavaScript
8. **goBack()** - Browser back
9. **goForward()** - Browser forward
10. **reload()** - Refresh page

---

## Testing

### Local Testing

```bash
# Start MCP server manually
cd mcp-packages/browser/playwright-mcp
node index.js

# In another terminal, send JSON-RPC requests
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | node index.js
```

### Integration Testing

1. Install MCP via OneController marketplace
2. Start MCP from Settings > MCPs
3. Test voice commands:
   - "go to google.com"
   - "fill in the search box with test"
   - "click the search button"

### Debug Logging

MCPs log to:
- **Windows**: `%APPDATA%\OneController\logs\mcp-{slug}.log`
- **macOS**: `~/Library/Application Support/OneController/logs/mcp-{slug}.log`

---

## Troubleshooting

### MCP Not Appearing in Marketplace

**Symptom**: Your MCP is registered in the database but doesn't show up in the OneController marketplace.

**Root Cause**: 99% of the time, this is because the `manifest.platforms` field is missing or empty.

**How the Marketplace Works:**
1. Frontend calls `mcp-get-marketplace` IPC with platform (e.g., "win32")
2. Backend calls Supabase edge function `mcp-marketplace`
3. Edge function queries `mcp_servers` table
4. **CRITICAL**: Edge function filters results by `manifest.platforms` array:
   ```typescript
   if (platform) {
     filteredMCPs = filteredMCPs.filter(mcp => {
       const platforms = mcp.manifest?.platforms || [];
       return platforms.some(p => normalizePlatform(p) === normalizedPlatform);
     });
   }
   ```
5. If `manifest.platforms` is missing/empty, the MCP is filtered out!

**Step-by-Step Debugging:**

1. **Check Database Entry**
   ```sql
   SELECT slug, name, category, is_base_package, is_active, is_verified,
          manifest->'platforms' as platforms
   FROM public.mcp_servers
   WHERE slug = 'your-mcp-slug';
   ```

   **Expected Result:**
   ```
   slug: "file-browser"
   platforms: ["win32"]  ← MUST have values!
   is_active: true
   is_verified: true
   ```

2. **Verify Platforms Field**
   ```sql
   -- Check if platforms exists and has values
   SELECT
       slug,
       manifest->'platforms' as platforms,
       jsonb_array_length(manifest->'platforms') as platform_count
   FROM public.mcp_servers
   WHERE slug = 'your-mcp-slug';
   ```

   If `platforms` is `null` or `platform_count` is `0`, that's your problem!

3. **Fix Missing Platforms**
   ```sql
   -- Add platforms field to manifest
   UPDATE public.mcp_servers
   SET manifest = jsonb_set(
       manifest,
       '{platforms}',
       '["win32"]'::jsonb
   )
   WHERE slug = 'your-mcp-slug';
   ```

4. **Verify Other Required Fields**
   ```sql
   SELECT slug, is_active, is_verified, category, is_base_package
   FROM public.mcp_servers
   WHERE slug = 'your-mcp-slug';
   ```

   Ensure:
   - `is_active = true`
   - `is_verified = true`
   - `category` matches expected value ("base", "productivity", etc.)

5. **Refresh Marketplace**
   - Close and reopen OneController Settings
   - Navigate to MCPs > Marketplace tab
   - MCP should now appear in the correct category

**Common Mistakes:**

| Issue | Cause | Fix |
|-------|-------|-----|
| MCP missing from marketplace | `manifest.platforms` is null/empty | Add platforms to manifest JSONB |
| MCP in wrong category | `category` field incorrect OR `is_base_package` wrong | Update category/is_base_package |
| ON CONFLICT doesn't update platforms | ON CONFLICT clause missing `manifest = EXCLUDED.manifest` | Update SQL to include manifest field |
| manifest.json has platforms but DB doesn't | ON CONFLICT didn't update manifest | Always include `manifest = EXCLUDED.manifest` in ON CONFLICT |

**Real-World Example (December 2025):**

**Problem**: file-browser v1.13.1 uploaded successfully, database entry created, but MCP didn't show in marketplace.

**Debugging Steps:**
1. Checked installed MCPs - file-browser was there but not in marketplace list
2. Verified database - is_active=true, is_verified=true, category correct
3. Compared with working MCPs (web-fetch-mcp) - found platforms field difference
4. Checked edge function code - discovered platform filtering by `manifest.platforms`
5. Verified file-browser manifest - platforms field was MISSING!

**Root Cause**: ON CONFLICT clause didn't include `manifest = EXCLUDED.manifest`, so old manifest (without platforms) persisted.

**Fix**:
```sql
UPDATE public.mcp_servers
SET manifest = jsonb_set(manifest, '{platforms}', '["win32"]')
WHERE slug = 'file-browser';
```

**Prevention**: Always include in ON CONFLICT:
```sql
ON CONFLICT (slug) DO UPDATE SET
    manifest = EXCLUDED.manifest,  -- CRITICAL!
    -- ... other fields
    updated_at = NOW();
```

**Time Lost**: 2+ hours of debugging
**Lesson**: Check `manifest.platforms` FIRST when MCP doesn't appear in marketplace!

---

## Appendix

### MCP Manager Code Flow

```
User clicks "Install" in marketplace
    ↓
frontend/settings/scripts/mcp-handler.js
    → handleInstallClick()
    ↓
frontend/mcp-ipc-handlers.js
    → ipcMain.handle('mcp-install')
    ↓
frontend/mcp-manager.js
    → MCPManager.installMCP()
    ↓
frontend/services/backend-storage-service.js
    → getMCPInfo() - fetch metadata from Supabase
    → downloadSingleFileMCP() - download ZIP from Bunny CDN
    ↓
Extract to AppData/OneController/mcps/{mcp_id}/
Save manifest.json
Record in user_mcp_installations table
```

### File Locations

- **MCPs installed to**: `%APPDATA%\OneController\mcps\{mcp_id}\`
- **Windows MCP source**: `D:\development\python\windows-mcp\` (SEPARATE from one_controller)
- **OneController project**: `D:\development\python\one_controller\`
- **Frontend handlers**: `frontend/mcp-*.js`
- **Settings UI**: `frontend/settings/scripts/mcp-handler.js`
- **Upload script**: `D:\development\python\one_controller\scripts\upload-to-bunnycdn.js`

---

**End of Guide**

For Windows MCP development, refer to `D:\development\python\windows-mcp\` for the source code.

# MCP Build and Upload Guide for OneController

**Date**: 2025-12-04
**Purpose**: Document the complete process for building, packaging, and deploying MCPs to OneController marketplace

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Database Schema](#database-schema)
3. [MCP Package Structure](#mcp-package-structure)
4. [Build Process](#build-process)
5. [Upload to Bunny CDN](#upload-to-bunny-cdn)
6. [Database Registration](#database-registration)
7. [Playwright MCP Implementation](#playwright-mcp-implementation)
8. [Testing](#testing)

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

#### Step 1: Create MCP Directory Structure

```bash
cd mcp-packages/windows-base/windows-mcp
```

Structure:
```
windows-mcp/
├── main.py          # Entry point
├── src/             # Source modules
├── manifest.json    # MCP metadata
├── pyproject.toml   # Python dependencies
├── windows-mcp.spec # PyInstaller spec file
├── build.ps1        # Build script
└── .venv/           # Virtual environment
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

```python
# windows-mcp.spec
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['live_inspect', 'fastmcp', 'humancursor', 'uiautomation'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

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
    console=True,
)
```

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
powershell -ExecutionPolicy Bypass -File build.ps1
```

**Output**:
```
dist/
├── windows-mcp.exe                      # ~59 MB bundled executable
├── manifest.json
├── README.md
├── LICENSE.md
├── windows-mcp-v0.5.1-win32.zip         # ~58 MB
└── windows-mcp-v0.5.1-win32.zip.sha256
```

---

### 📦 Build Process Comparison

| Step | Node.js MCP | Python MCP |
|------|-------------|------------|
| **Bundler** | pkg (standalone exe) | PyInstaller |
| **Entry Point** | index.js | main.py |
| **Spec File** | package.json | windows-mcp.spec |
| **Build Command** | `pkg index.js` | `pyinstaller --clean windows-mcp.spec` |
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
    cdn_url = EXCLUDED.cdn_url,
    checksum = EXCLUDED.checksum,
    size_bytes = EXCLUDED.size_bytes,
    manifest = EXCLUDED.manifest,
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
- **MCP source (dev)**: `D:\development\python\one_controller\mcp-packages\`
- **Frontend handlers**: `frontend/mcp-*.js`
- **Settings UI**: `frontend/settings/scripts/mcp-handler.js`

---

**End of Guide**

For questions or issues, refer to existing MCPs in `mcp-packages/windows-base/` for examples.

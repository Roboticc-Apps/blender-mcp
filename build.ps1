# Build script for blender-mcp v1.6.0
# Builds the MCP server with AI Control System

param(
    [string]$Version = "1.6.0",
    [string]$Platform = "win32"
)

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Building blender-mcp v$Version" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

# Step 1: Clean previous builds
Write-Host "[1/6] Cleaning previous builds..." -ForegroundColor Yellow
Remove-Item "build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "dist\blender-mcp.exe" -Force -ErrorAction SilentlyContinue
Remove-Item "dist\blender-mcp-v*.zip" -Force -ErrorAction SilentlyContinue
Remove-Item "dist\blender-mcp-v*.sha256" -Force -ErrorAction SilentlyContinue
Write-Host "   Done - Cleaned" -ForegroundColor Green
Write-Host ""

# Step 2: Update version in pyproject.toml
Write-Host "[2/6] Updating version to $Version..." -ForegroundColor Yellow
$pyprojectContent = Get-Content "pyproject.toml" -Raw
$pyprojectContent = $pyprojectContent -replace 'version = ".*"', "version = `"$Version`""
Set-Content "pyproject.toml" -Value $pyprojectContent
Write-Host "   Done - Updated pyproject.toml" -ForegroundColor Green
Write-Host ""

# Step 3: Build with PyInstaller
Write-Host "[3/6] Building with PyInstaller..." -ForegroundColor Yellow
if (Test-Path ".\build_env\Scripts\pyinstaller.exe") {
    & ".\build_env\Scripts\pyinstaller.exe" --clean blender-mcp.spec
} else {
    Write-Host "   ! PyInstaller not found in build_env, trying global..." -ForegroundColor Yellow
    pyinstaller --clean blender-mcp.spec
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "   ERROR - PyInstaller failed!" -ForegroundColor Red
    exit 1
}
Write-Host "   Done - Built blender-mcp.exe" -ForegroundColor Green
Write-Host ""

# Step 4: Copy addon.py and manifest to dist
Write-Host "[4/6] Copying files to dist..." -ForegroundColor Yellow
Copy-Item "addon.py" -Destination "dist\blender_mcp_addon.py" -Force
Copy-Item "dist\manifest.json" -Destination "dist\manifest_temp.json" -Force

# Update manifest.json version
$manifestContent = Get-Content "dist\manifest_temp.json" -Raw | ConvertFrom-Json
$manifestContent.version = $Version
$manifestContent | ConvertTo-Json -Depth 10 | Set-Content "dist\manifest.json"
Remove-Item "dist\manifest_temp.json"

Write-Host "   Done - Copied addon.py and updated manifest.json" -ForegroundColor Green
Write-Host ""

# Step 5: Create ZIP package
Write-Host "[5/6] Creating ZIP package..." -ForegroundColor Yellow
$zipName = "blender-mcp-v$Version-$Platform.zip"
$filesToZip = @(
    "dist\blender-mcp.exe",
    "dist\blender_mcp_addon.py",
    "dist\manifest.json"
)

Compress-Archive -Path $filesToZip -DestinationPath "dist\$zipName" -Force
Write-Host "   Done - Created dist\$zipName" -ForegroundColor Green

# Get file size
$zipSize = (Get-Item "dist\$zipName").Length
$zipSizeMB = [math]::Round($zipSize / 1MB, 2)
Write-Host "   Size: $zipSizeMB MB - $zipSize bytes" -ForegroundColor Cyan
Write-Host ""

# Step 6: Generate checksum
Write-Host "[6/6] Generating SHA256 checksum..." -ForegroundColor Yellow
$hash = (Get-FileHash "dist\$zipName" -Algorithm SHA256).Hash
Set-Content -Path "dist\$zipName.sha256" -Value "$hash  $zipName"
Write-Host "   Done - Checksum: $hash" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "BUILD COMPLETE!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Package: dist\$zipName" -ForegroundColor White
Write-Host "Size: $zipSizeMB MB - $zipSize bytes" -ForegroundColor White
Write-Host "Checksum: $hash" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Upload to Bunny CDN: https://onecontroller.b-cdn.net/mcps/creative/$zipName" -ForegroundColor White
Write-Host "2. Update Supabase with new version, checksum, and size" -ForegroundColor White
Write-Host "3. Test installation from OneController marketplace" -ForegroundColor White
Write-Host ""

# Generate Supabase UPDATE SQL
$sqlFile = "dist\UPDATE_SUPABASE_v$Version.sql"
$sqlContent = @"
-- Update blender-mcp to v$Version with AI Control System
-- Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

UPDATE mcp_servers
SET
    latest_version = '$Version',
    description = 'AI-powered 3D modeling with comprehensive Blender control via voice commands',
    long_description = 'Control Blender with natural voice commands and AI-powered automation:

- Full Context Layer: get_full_context, get_node_tree, get_modifier_stack, get_viewport_state
- UI Control: switch_editor, set_viewport_shading, set_view_angle
- Node Actions: create_material, add/remove nodes, connect_nodes
- Modifier Actions: add/remove/apply modifiers, set_modifier_settings
- Object Actions: select_object, set_mode, add_primitive, transform_object
- Animation: set_frame, keyframe management
- Action Sequencing: execute_action_sequence for multi-step operations

NEW in v1.6.0:
- AI Control System with 25+ new handlers
- Rich context awareness for AI
- Multi-step atomic operations
- Voice-controllable Blender

Requires Blender addon to be installed and running.',
    cdn_url = 'https://onecontroller.b-cdn.net/mcps/creative/$zipName',
    checksum = '$hash',
    size_bytes = $zipSize,
    updated_at = NOW()
WHERE slug = 'blender-mcp';

-- Verify update
SELECT
    slug,
    name,
    latest_version,
    size_bytes,
    checksum,
    updated_at
FROM mcp_servers
WHERE slug = 'blender-mcp';
"@

Set-Content -Path $sqlFile -Value $sqlContent
Write-Host "Generated Supabase update SQL: $sqlFile" -ForegroundColor Green
Write-Host ""

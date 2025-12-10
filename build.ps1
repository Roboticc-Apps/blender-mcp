# Build script for blender-mcp v1.5.0
# Builds the MCP server with enhanced context broadcasting

param(
    [string]$Version = "1.5.0",
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
Write-Host "   ✓ Cleaned" -ForegroundColor Green
Write-Host ""

# Step 2: Update version in pyproject.toml
Write-Host "[2/6] Updating version to $Version..." -ForegroundColor Yellow
$pyprojectContent = Get-Content "pyproject.toml" -Raw
$pyprojectContent = $pyprojectContent -replace 'version = ".*"', "version = `"$Version`""
Set-Content "pyproject.toml" -Value $pyprojectContent
Write-Host "   ✓ Updated pyproject.toml" -ForegroundColor Green
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
    Write-Host "   ✗ PyInstaller failed!" -ForegroundColor Red
    exit 1
}
Write-Host "   ✓ Built blender-mcp.exe" -ForegroundColor Green
Write-Host ""

# Step 4: Copy addon.py and manifest to dist
Write-Host "[4/6] Copying files to dist..." -ForegroundColor Yellow
Copy-Item "addon.py" -Destination "dist\blender_mcp_addon.py" -Force
Copy-Item "dist\manifest.json" -Destination "dist\manifest_temp.json" -Force

# Update manifest.json version
$manifestContent = Get-Content "dist\manifest_temp.json" -Raw | ConvertFrom-Json
$manifestContent.version = $Version
$manifestContent.tools[1].description = "Get comprehensive Blender scene information including ALL objects (unlimited), selection state, materials, cameras, lights, modifiers, and collections - enhanced for context-aware voice commands"
$manifestContent | ConvertTo-Json -Depth 10 | Set-Content "dist\manifest.json"
Remove-Item "dist\manifest_temp.json"

Write-Host "   ✓ Copied addon.py and updated manifest.json" -ForegroundColor Green
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
Write-Host "   ✓ Created dist\$zipName" -ForegroundColor Green

# Get file size
$zipSize = (Get-Item "dist\$zipName").Length
$zipSizeMB = [math]::Round($zipSize / 1MB, 2)
Write-Host "   Size: $zipSizeMB MB ($zipSize bytes)" -ForegroundColor Cyan
Write-Host ""

# Step 6: Generate checksum
Write-Host "[6/6] Generating SHA256 checksum..." -ForegroundColor Yellow
$hash = (Get-FileHash "dist\$zipName" -Algorithm SHA256).Hash
Set-Content -Path "dist\$zipName.sha256" -Value "$hash  $zipName"
Write-Host "   ✓ Checksum: $hash" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "BUILD COMPLETE!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Package: dist\$zipName" -ForegroundColor White
Write-Host "Size: $zipSizeMB MB ($zipSize bytes)" -ForegroundColor White
Write-Host "Checksum: $hash" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Upload to Bunny CDN: https://onecontroller.b-cdn.net/mcps/creative/$zipName" -ForegroundColor White
Write-Host "2. Update Supabase with new version, checksum, and size" -ForegroundColor White
Write-Host "3. Test installation from OneController marketplace" -ForegroundColor White
Write-Host ""

# Generate Supabase UPDATE SQL
$sqlFile = "dist\UPDATE_SUPABASE_v$Version.sql"
$sql = @"
-- Update blender-mcp to v$Version with enhanced context broadcasting
-- Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

UPDATE mcp_servers
SET
    latest_version = '$Version',
    description = '3D modeling with enhanced scene context awareness for voice commands',
    long_description = 'Control Blender with natural voice commands with full scene awareness:

• Enhanced context broadcasting - AI sees ALL objects (unlimited), selection state, modifiers
• Create and modify 3D objects with context-aware commands
• Apply materials and textures
• Set up lighting and cameras
• Download assets from Poly Haven
• Generate AI models with Hyper3D
• Execute any Blender Python code

NEW in v$Version:
✓ Comprehensive scene context (no more 10-object limit)
✓ Selection awareness (active + selected objects)
✓ Full object details (modifiers, materials, hierarchy)
✓ Material information with colors
✓ Scene metadata (mode, render engine, frame)

Requires Blender addon to be installed and running.',
    cdn_url = 'https://onecontroller.b-cdn.net/mcps/creative/$zipName',
    checksum = '$hash',
    size_bytes = $zipSize,
    manifest = jsonb_set(
        manifest,
        '{version}',
        '"$Version"'
    ),
    manifest = jsonb_set(
        manifest,
        '{tools,1,description}',
        '"Get comprehensive Blender scene information including ALL objects (unlimited), selection state, materials, cameras, lights, modifiers, and collections - enhanced for context-aware voice commands"'
    ),
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

Set-Content -Path $sqlFile -Value $sql
Write-Host "Generated Supabase update SQL: $sqlFile" -ForegroundColor Green
Write-Host ""

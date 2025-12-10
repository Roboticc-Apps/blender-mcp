# Build script for blender-mcp v1.5.0
param(
    [string]$Version = "1.5.0",
    [string]$Platform = "win32"
)

Write-Host "Building blender-mcp v$Version" -ForegroundColor Cyan
Set-Location $PSScriptRoot

# Step 1: Clean previous builds
Write-Host "[1/6] Cleaning..." -ForegroundColor Yellow
Remove-Item "build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "dist\blender-mcp.exe" -Force -ErrorAction SilentlyContinue
Write-Host "   Done" -ForegroundColor Green

# Step 2: Update version
Write-Host "[2/6] Updating version..." -ForegroundColor Yellow
$pyprojectContent = Get-Content "pyproject.toml" -Raw
$pyprojectContent = $pyprojectContent -replace 'version = ".*"', "version = `"$Version`""
Set-Content "pyproject.toml" -Value $pyprojectContent
Write-Host "   Done" -ForegroundColor Green

# Step 3: Build with PyInstaller
Write-Host "[3/6] Building..." -ForegroundColor Yellow
if (Test-Path ".\build_env\Scripts\pyinstaller.exe") {
    & ".\build_env\Scripts\pyinstaller.exe" --clean blender-mcp.spec
} else {
    pyinstaller --clean blender-mcp.spec
}
Write-Host "   Done" -ForegroundColor Green

# Step 4: Copy files
Write-Host "[4/6] Copying files..." -ForegroundColor Yellow
Copy-Item "addon.py" -Destination "dist\blender_mcp_addon.py" -Force

# Update manifest
$manifest = Get-Content "dist\manifest.json" -Raw | ConvertFrom-Json
$manifest.version = $Version
$manifest.tools[1].description = "Get comprehensive Blender scene information including ALL objects (unlimited), selection state, materials, cameras, lights, modifiers, and collections"
$manifest | ConvertTo-Json -Depth 10 | Set-Content "dist\manifest.json"
Write-Host "   Done" -ForegroundColor Green

# Step 5: Create ZIP
Write-Host "[5/6] Creating ZIP..." -ForegroundColor Yellow
$zipName = "blender-mcp-v$Version-$Platform.zip"
Compress-Archive -Path @("dist\blender-mcp.exe", "dist\blender_mcp_addon.py", "dist\manifest.json") -DestinationPath "dist\$zipName" -Force
$zipSize = (Get-Item "dist\$zipName").Length
Write-Host "   Done - Size: $zipSize bytes" -ForegroundColor Green

# Step 6: Generate checksum
Write-Host "[6/6] Generating checksum..." -ForegroundColor Yellow
$hash = (Get-FileHash "dist\$zipName" -Algorithm SHA256).Hash
Set-Content -Path "dist\$zipName.sha256" -Value "$hash  $zipName"
Write-Host "   Done" -ForegroundColor Green
Write-Host ""
Write-Host "BUILD COMPLETE!" -ForegroundColor Green
Write-Host "Package: dist\$zipName" -ForegroundColor White
Write-Host "Size: $zipSize bytes" -ForegroundColor White
Write-Host "Checksum: $hash" -ForegroundColor White

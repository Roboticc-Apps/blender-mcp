import zipfile
import os
import hashlib

zip_path = 'dist/blender-mcp-v1.7.4-win32.zip'
dist_dir = 'dist'

files_to_zip = ['blender-mcp.exe', 'blender_mcp_addon.py', 'manifest.json']

# Remove old ZIP if exists
if os.path.exists(zip_path):
    os.remove(zip_path)

print(f'Creating: {zip_path}')
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for filename in files_to_zip:
        file_path = os.path.join(dist_dir, filename)
        if os.path.exists(file_path):
            arcname = filename.replace('\\', '/')
            zf.write(file_path, arcname)
            size = os.path.getsize(file_path)
            print(f'  Added: {arcname} ({size:,} bytes)')
        else:
            print(f'  WARNING: {file_path} not found')

zip_size = os.path.getsize(zip_path)
print(f'ZIP created: {zip_path} ({zip_size:,} bytes)')

with open(zip_path, 'rb') as f:
    sha256 = hashlib.sha256(f.read()).hexdigest()
print(f'SHA-256: {sha256}')

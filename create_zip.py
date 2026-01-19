import zipfile
import os

zip_path = 'dist/blender-mcp-v1.7.3-win32.zip'
dist_dir = 'dist'

files_to_zip = ['blender-mcp.exe', 'blender_mcp_addon.py', 'manifest.json']

# Remove old ZIP if exists
if os.path.exists(zip_path):
    os.remove(zip_path)

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for filename in files_to_zip:
        file_path = os.path.join(dist_dir, filename)
        if os.path.exists(file_path):
            arcname = filename.replace('\\', '/')
            zf.write(file_path, arcname)
            print(f'  Added: {arcname}')
        else:
            print(f'  WARNING: {file_path} not found')

print(f'ZIP created: {zip_path}')

# Get file size
size = os.path.getsize(zip_path)
print(f'Size: {size} bytes ({size / 1024 / 1024:.2f} MB)')

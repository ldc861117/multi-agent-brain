# Quick validation of configuration structure

print("Validating configuration files...")

# Check if files exist and have basic structure
import os

files_to_check = [
    "/home/engine/project/.env.example",
    "/home/engine/project/utils/config_manager.py",
    "/home/engine/project/utils/openai_client.py",
    "/home/engine/project/config.yaml",
]

for file_path in files_to_check:
    if os.path.exists(file_path):
        print(f"✅ {file_path} exists")
        with open(file_path, 'r') as f:
            content = f.read()
            print(f"   Size: {len(content)} bytes")
    else:
        print(f"❌ {file_path} missing")

print("\nConfiguration structure validation complete!")
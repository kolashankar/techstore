import zipfile
import os
import shutil

zip_path = "techstore (1).zip"
extract_path = "/app"

try:
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    print("Extraction successful")
    
    # Check if there is a nested folder and move contents up if needed
    # (The bash command attempted to handle this: mv /app/techstore_temp/*/* /app/ )
    # Let's inspect structure after extraction first in the next step
    
except Exception as e:
    print(f"Error: {e}")

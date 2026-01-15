import zipfile
import os
import shutil

zip_path = "/app/techstore.zip"
extract_path = "/app/temp_extract"

if os.path.exists(extract_path):
    shutil.rmtree(extract_path)
os.makedirs(extract_path)

try:
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    print("Extraction successful")
    print("Files in extraction path:", os.listdir(extract_path))
    
    # Move files to /app
    # If the zip has a root folder (e.g. techstore/), move contents of that.
    # Otherwise move contents of extract_path.
    
    items = os.listdir(extract_path)
    source_dir = extract_path
    if len(items) == 1 and os.path.isdir(os.path.join(extract_path, items[0])):
        source_dir = os.path.join(extract_path, items[0])
        print(f"Detected nested folder: {items[0]}")
    
    for item in os.listdir(source_dir):
        s = os.path.join(source_dir, item)
        d = os.path.join("/app", item)
        if os.path.exists(d):
            if os.path.isdir(d):
                shutil.rmtree(d)
            else:
                os.remove(d)
        shutil.move(s, d)
    
    print("Files moved to /app")
    
except Exception as e:
    print(f"Error: {e}")

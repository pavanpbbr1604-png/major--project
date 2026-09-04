import os
import urllib.request
import zipfile
import shutil
import time

url = "https://www.dropbox.com/scl/fi/dkj5kulc9zj0rzesslck8/ShanghaiTech_Crowd_Counting_Dataset.zip?rlkey=ymbcj50ac04uvqn8p49j9af5f&dl=1"
temp_zip = os.path.join("scratch", "shanghaitech.zip")
target_dir = os.path.join("docs", "figures")
os.makedirs(target_dir, exist_ok=True)

print(f"1. Downloading dataset zip to {temp_zip}...")
start_time = time.time()
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

with urllib.request.urlopen(req) as resp, open(temp_zip, "wb") as out_f:
    total_size = int(resp.headers.get("Content-Length", 0))
    downloaded = 0
    chunk_size = 1024 * 1024 * 2 # 2MB
    last_print = time.time()
    while True:
        chunk = resp.read(chunk_size)
        if not chunk:
            break
        out_f.write(chunk)
        downloaded += len(chunk)
        now = time.time()
        if now - last_print > 3:
            percent = (downloaded / total_size * 100) if total_size else 0
            mb = downloaded / (1024 * 1024)
            print(f"Downloaded {mb:.1f} MB ({percent:.1f}%) in {now - start_time:.1f}s")
            last_print = now

print(f"Download complete in {time.time() - start_time:.1f}s.")

print("2. Inspecting zip and extracting 200 crowd images...")
with zipfile.ZipFile(temp_zip, 'r') as z:
    all_files = z.namelist()
    # Find all image files (.jpg, .png, .jpeg)
    image_names = [f for f in all_files if f.lower().endswith(('.jpg', '.png', '.jpeg')) and not f.startswith('__MACOSX')]
    print(f"Total images found in dataset: {len(image_names)}")
    
    # We select 200 images (from both part_A dense and part_B sparse/medium crowds for good variety)
    part_a = [f for f in image_names if 'part_A' in f]
    part_b = [f for f in image_names if 'part_B' in f]
    others = [f for f in image_names if 'part_A' not in f and 'part_B' not in f]
    
    selected = []
    # Take 100 from part_A (dense crowds) and 100 from part_B (moderate/perspective crowds)
    selected.extend(part_a[:100])
    selected.extend(part_b[:100])
    if len(selected) < 200:
        remaining = [f for f in image_names if f not in selected]
        selected.extend(remaining[:200 - len(selected)])
    
    print(f"Selected {len(selected)} images for extraction.")
    
    count = 0
    for idx, zip_path in enumerate(selected, 1):
        ext = os.path.splitext(zip_path)[1].lower()
        target_filename = f"crowd_{idx:03d}{ext}"
        target_path = os.path.join(target_dir, target_filename)
        
        with z.open(zip_path) as src_f, open(target_path, 'wb') as dst_f:
            shutil.copyfileobj(src_f, dst_f)
        count += 1

print(f"3. Successfully extracted {count} images into {target_dir}")

# Clean up temp zip to save disk space
if os.path.exists(temp_zip):
    os.remove(temp_zip)
    print("4. Cleaned up temporary zip file.")

print("All done!")

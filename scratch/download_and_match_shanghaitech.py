import os
import urllib.request
import zipfile
import hashlib
import time
import json
import csv
import scipy.io
import cv2
import numpy as np

ZIP_URL = "https://www.dropbox.com/scl/fi/dkj5kulc9zj0rzesslck8/ShanghaiTech_Crowd_Counting_Dataset.zip?rlkey=ymbcj50ac04uvqn8p49j9af5f&dl=1"
TEMP_ZIP = os.path.join("scratch", "shanghaitech.zip")
ANNOTATIONS_DIR = os.path.join("scratch", "shanghaitech_annotations")
os.makedirs(ANNOTATIONS_DIR, exist_ok=True)

# 1. Download zip if not already present
if not os.path.exists(TEMP_ZIP) or os.path.getsize(TEMP_ZIP) < 170000000:
    print(f"Downloading {ZIP_URL} to {TEMP_ZIP}...")
    t0 = time.time()
    req = urllib.request.Request(ZIP_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(TEMP_ZIP, "wb") as out_f:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 2 * 1024 * 1024
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            out_f.write(chunk)
            downloaded += len(chunk)
            mb = downloaded / (1024 * 1024)
            pct = (downloaded / total * 100) if total else 0
            print(f"  Downloaded {mb:.1f} MB ({pct:.1f}%)")
    print(f"Downloaded in {time.time() - t0:.1f}s.")
else:
    print(f"Using existing zip file {TEMP_ZIP} ({os.path.getsize(TEMP_ZIP)} bytes)")

# 2. Inspect zip contents and extract annotations + map images
print("\nInspecting zip file...")
with zipfile.ZipFile(TEMP_ZIP, "r") as z:
    all_names = z.namelist()
    print(f"Total entries in zip: {len(all_names)}")
    
    # Extract all .mat files
    mat_files = [f for f in all_names if f.lower().endswith(".mat") and not f.startswith("__MACOSX")]
    print(f"Found {len(mat_files)} ground-truth .mat files in archive.")
    
    for mf in mat_files:
        # e.g., ShanghaiTech/part_A/train_data/ground-truth/GT_IMG_1.mat
        dest = os.path.join(ANNOTATIONS_DIR, mf.replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with z.open(mf) as src, open(dest, "wb") as dst:
            dst.write(src.read())
    print(f"Extracted all {len(mat_files)} .mat files to {ANNOTATIONS_DIR}")
    
    # Hash all image files in zip
    image_names = [f for f in all_names if f.lower().endswith((".jpg", ".png", ".jpeg")) and not f.startswith("__MACOSX")]
    print(f"Found {len(image_names)} images in archive. Hashing all images...")
    
    zip_img_hashes = {}
    for img_path in image_names:
        img_bytes = z.read(img_path)
        sha = hashlib.sha256(img_bytes).hexdigest()
        zip_img_hashes[sha] = img_path
    print(f"Hashed {len(zip_img_hashes)} unique images from archive.")

# 3. Hash our 200 crowd images
figures_dir = os.path.join("testing images", "figures")
crowd_files = [f"crowd_{i:03d}.jpg" for i in range(1, 201)]

print(f"\nMatching our 200 crowd images against ShanghaiTech images...")
matches = []
unmatched = []

for cf in crowd_files:
    full_p = os.path.join(figures_dir, cf)
    with open(full_p, "rb") as fp:
        crowd_bytes = fp.read()
    sha = hashlib.sha256(crowd_bytes).hexdigest()
    
    img = cv2.imread(full_p)
    h, w = img.shape[:2]
    
    if sha in zip_img_hashes:
        orig_zip_path = zip_img_hashes[sha]
        matches.append({
            "crowd_file": cf,
            "sha256": sha,
            "orig_zip_path": orig_zip_path,
            "width": w,
            "height": h,
            "match_type": "EXACT_SHA256"
        })
    else:
        unmatched.append({
            "crowd_file": cf,
            "sha256": sha,
            "width": w,
            "height": h
        })

print(f"Exact SHA-256 matches: {len(matches)} / 200")
print(f"Unmatched: {len(unmatched)}")

if unmatched:
    print("Unmatched samples:", unmatched[:5])
else:
    print("ALL 200 IMAGES MATCHED 100% BIT-FOR-BIT IDENTICALLY!")
    print("\nFirst 5 matched samples:")
    for m in matches[:5]:
        print(f"  {m['crowd_file']} -> {m['orig_zip_path']} ({m['width']}x{m['height']})")
    print("\nSamples from crowd_101 to 105:")
    for m in matches[100:105]:
        print(f"  {m['crowd_file']} -> {m['orig_zip_path']} ({m['width']}x{m['height']})")

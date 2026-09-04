import os
import zipfile
import hashlib
import scipy.io
import json
import csv
import cv2

TEMP_ZIP = os.path.join("scratch", "shanghaitech.zip")
ANNOTATIONS_DIR = os.path.join("scratch", "shanghaitech_annotations")
figures_dir = os.path.join("testing images", "figures")

# Map zip image path to sha256
with zipfile.ZipFile(TEMP_ZIP, "r") as z:
    all_names = z.namelist()
    image_names = [f for f in all_names if f.lower().endswith((".jpg", ".png", ".jpeg")) and not f.startswith("__MACOSX")]
    zip_img_map = {}
    for img_path in image_names:
        img_bytes = z.read(img_path)
        sha = hashlib.sha256(img_bytes).hexdigest()
        zip_img_map[sha] = img_path

mapping_records = []
part_a_count = 0
part_b_count = 0
verified_count = 0
unverified_count = 0
missing_orig_count = 0
missing_gt_count = 0
ambiguous_count = 0
problematic_images = []

for i in range(1, 201):
    cf = f"crowd_{i:03d}.jpg"
    full_p = os.path.join(figures_dir, cf)
    with open(full_p, "rb") as fp:
        crowd_bytes = fp.read()
    sha = hashlib.sha256(crowd_bytes).hexdigest()
    
    img = cv2.imread(full_p)
    h, w = img.shape[:2]
    
    if sha not in zip_img_map:
        unverified_count += 1
        missing_orig_count += 1
        problematic_images.append(f"{cf}: Missing original image in archive")
        continue
        
    zip_path = zip_img_map[sha]
    parts = zip_path.replace("\\", "/").split("/")
    dataset_part = "ShanghaiTech Part A" if "part_A" in parts[0] else "ShanghaiTech Part B"
    split = "train" if "train_data" in parts[1] else "test"
    orig_filename = parts[-1]
    
    if "Part A" in dataset_part:
        part_a_count += 1
    else:
        part_b_count += 1
        
    base_name = os.path.splitext(orig_filename)[0]
    gt_filename = f"GT_{base_name}.mat"
    
    # Locate mat file
    mat_rel_dir = os.path.join(parts[0], parts[1], "ground_truth")
    mat_path = os.path.join(ANNOTATIONS_DIR, mat_rel_dir, gt_filename)
    if not os.path.exists(mat_path):
        mat_rel_dir2 = os.path.join(parts[0], parts[1], "ground-truth")
        mat_path2 = os.path.join(ANNOTATIONS_DIR, mat_rel_dir2, gt_filename)
        if os.path.exists(mat_path2):
            mat_path = mat_path2
            
    if not os.path.exists(mat_path):
        unverified_count += 1
        missing_gt_count += 1
        problematic_images.append(f"{cf}: Missing GT annotation {gt_filename}")
        continue
        
    # Read and verify mat
    try:
        mat = scipy.io.loadmat(mat_path)
        info = mat["image_info"]
        loc = info[0, 0]["location"][0, 0]
        num = int(info[0, 0]["number"][0, 0][0, 0])
        pts_count = len(loc)
        if pts_count != num:
            ambiguous_count += 1
            unverified_count += 1
            problematic_images.append(f"{cf}: Mismatch between location count ({pts_count}) and number field ({num})")
            continue
    except Exception as e:
        unverified_count += 1
        problematic_images.append(f"{cf}: Error loading mat {e}")
        continue
        
    verified_count += 1
    mapping_records.append({
        "Our_Filename": cf,
        "Original_Dataset": dataset_part,
        "Original_Split": split,
        "Original_Filename": orig_filename,
        "Ground_Truth_Annotation": gt_filename,
        "Ground_Truth_Count": num,
        "Image_Width": w,
        "Image_Height": h,
        "Image_Match_Method": "exact_sha256_hash",
        "Annotation_Match_Method": "official_mat_annotation",
        "Verification_Status": "VERIFIED",
        "Notes": "Exact bit-for-bit SHA-256 match to official dataset; zero cropping or modification",
        "mat_path": mat_path
    })

# 1. Write SHANGHAITECH_VERIFIED_MAPPING.csv
csv_fields = [
    "Our_Filename",
    "Original_Dataset",
    "Original_Split",
    "Original_Filename",
    "Ground_Truth_Annotation",
    "Ground_Truth_Count",
    "Image_Width",
    "Image_Height",
    "Image_Match_Method",
    "Annotation_Match_Method",
    "Verification_Status",
    "Notes"
]

with open("SHANGHAITECH_VERIFIED_MAPPING.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=csv_fields)
    writer.writeheader()
    for r in mapping_records:
        writer.writerow({k: r[k] for k in csv_fields})

# 2. Write SHANGHAITECH_VERIFIED_MAPPING.json
json_records = [{k: r[k] for k in csv_fields} for r in mapping_records]
with open("SHANGHAITECH_VERIFIED_MAPPING.json", "w", encoding="utf-8") as f:
    json.dump({
        "total_additional_images": len(mapping_records),
        "part_a_count": part_a_count,
        "part_b_count": part_b_count,
        "successfully_verified": verified_count,
        "unverified": unverified_count,
        "missing_original_image": missing_orig_count,
        "missing_gt_annotation": missing_gt_count,
        "ambiguous_matches": ambiguous_count,
        "records": json_records
    }, f, indent=2)

# 3. Write SHANGHAITECH_FINAL_DATASET_SUMMARY.csv
summary_fields = [
    "Our_Filename",
    "Dataset",
    "Split",
    "Original_Filename",
    "GT_File",
    "Ground_Truth_Count",
    "Resolution",
    "Verification_Status"
]

with open("SHANGHAITECH_FINAL_DATASET_SUMMARY.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=summary_fields)
    writer.writeheader()
    for r in mapping_records:
        writer.writerow({
            "Our_Filename": r["Our_Filename"],
            "Dataset": r["Original_Dataset"],
            "Split": r["Original_Split"],
            "Original_Filename": r["Original_Filename"],
            "GT_File": r["Ground_Truth_Annotation"],
            "Ground_Truth_Count": r["Ground_Truth_Count"],
            "Resolution": f"{r['Image_Width']}x{r['Image_Height']}",
            "Verification_Status": r["Verification_Status"]
        })

# 4. Write SHANGHAITECH_VERIFICATION_REPORT.txt
with open("SHANGHAITECH_VERIFICATION_REPORT.txt", "w", encoding="utf-8") as f:
    f.write("TOTAL ADDITIONAL IMAGES: 200\n\n")
    f.write("PART A:\n")
    f.write(f"count = {part_a_count}\n\n")
    f.write("PART B:\n")
    f.write(f"count = {part_b_count}\n\n")
    f.write(f"SUCCESSFULLY VERIFIED:\n{verified_count}\n\n")
    f.write(f"UNVERIFIED:\n{unverified_count}\n\n")
    f.write(f"MISSING ORIGINAL IMAGE:\n{missing_orig_count}\n\n")
    f.write(f"MISSING GT ANNOTATION:\n{missing_gt_count}\n\n")
    f.write(f"AMBIGUOUS MATCHES:\n{ambiguous_count}\n\n")
    f.write("PROBLEMATIC IMAGES:\n")
    if problematic_images:
        for p in problematic_images:
            f.write(f"  - {p}\n")
    else:
        f.write("  None (all 200 images successfully verified with 0 errors or ambiguities)\n")

print(f"Generated all 4 files successfully! Verified: {verified_count}/200")

"""
Verification Script for ShanghaiTech Ground-Truth Annotations
Compares SHANGHAITECH_VERIFIED_MAPPING.csv against official .mat annotation files.
"""

import os
import sys
import csv
import scipy.io

CSV_PATH = "SHANGHAITECH_VERIFIED_MAPPING.csv"
ANNOTATIONS_BASE = os.path.join("scratch", "shanghaitech_annotations")

def verify_ground_truth():
    if not os.path.exists(CSV_PATH):
        print(f"ERROR: {CSV_PATH} not found!")
        sys.exit(1)
        
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        
    total_images = len(reader)
    print(f"Loaded {total_images} records from {CSV_PATH}.")
    
    verified_count = 0
    mismatch_count = 0
    missing_annot_count = 0
    
    for idx, row in enumerate(reader, 1):
        our_fn = row["Our_Filename"]
        orig_ds = row["Original_Dataset"]
        orig_split = row["Original_Split"]
        gt_file = row["Ground_Truth_Annotation"]
        recorded_gt = int(row["Ground_Truth_Count"])
        
        # Build path to official .mat file
        part_dir = "part_A_final" if "Part A" in orig_ds else "part_B_final"
        split_dir = "train_data" if orig_split == "train" else "test_data"
        
        # Try both ground_truth and ground-truth subfolder conventions
        mat_path = os.path.join(ANNOTATIONS_BASE, part_dir, split_dir, "ground_truth", gt_file)
        if not os.path.exists(mat_path):
            mat_path = os.path.join(ANNOTATIONS_BASE, part_dir, split_dir, "ground-truth", gt_file)
            
        if not os.path.exists(mat_path):
            print(f"[{idx}/{total_images}] ERROR: Annotation file not found: {mat_path}")
            missing_annot_count += 1
            continue
            
        # Load official .mat file
        try:
            mat = scipy.io.loadmat(mat_path)
            info = mat["image_info"]
            loc = info[0, 0]["location"][0, 0]
            official_num = int(info[0, 0]["number"][0, 0][0, 0])
            actual_points = len(loc)
            
            # Sanity check within the .mat file itself
            if actual_points != official_num:
                print(f"[{idx}/{total_images}] WARNING in {gt_file}: point coordinates length ({actual_points}) != number field ({official_num})")
                
            # Compare against CSV recorded count
            if actual_points != recorded_gt:
                print(f"[{idx}/{total_images}] MISMATCH in {our_fn} ({gt_file}): CSV count={recorded_gt} vs .mat points={actual_points}")
                mismatch_count += 1
            else:
                verified_count += 1
                
        except Exception as e:
            print(f"[{idx}/{total_images}] ERROR reading {mat_path}: {e}")
            mismatch_count += 1

    print("\n" + "="*50)
    print("SHANGHAITECH GROUND TRUTH VERIFICATION AUDIT SUMMARY")
    print("="*50)
    print(f"Total Images Evaluated:   {total_images}")
    print(f"Verified Exact Matches:   {verified_count} / {total_images}")
    print(f"GT Count Mismatches:      {mismatch_count}")
    print(f"Missing Annotation Files: {missing_annot_count}")
    print("="*50)
    
    if verified_count == total_images and mismatch_count == 0 and missing_annot_count == 0:
        print("SUCCESS: Verified 200/200. GT count mismatches: 0.")
        return 0
    else:
        print("FAILURE: Ground truth verification detected errors or mismatches!")
        return 1

if __name__ == "__main__":
    sys.exit(verify_ground_truth())

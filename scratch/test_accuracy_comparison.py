import cv2
import numpy as np
import os
from utils.detection import CrowdDetector

def main():
    print("=== RUNNING POST-FIX DETECTION TEST ===")
    d = CrowdDetector()
    
    # Test on test_image1.jpg
    img1 = cv2.imread("test_image1.jpg")
    if img1 is not None:
        res1, _ = d.detect_hierarchical(img1, use_tiled=True)
        print(f"test_image1.jpg (1080p crowd) count: {len(res1)} people detected (Baseline before fix was 38)")
        # Annotate and save
        img1_draw = img1.copy()
        for det in res1:
            box = det["bbox"]
            cv2.rectangle(img1_draw, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (0, 255, 0), 2)
        os.makedirs("static/uploads/debug", exist_ok=True)
        cv2.imwrite("static/uploads/debug/test_image1_after_fix.jpg", img1_draw)
        print("Saved annotated test_image1 to static/uploads/debug/test_image1_after_fix.jpg")
    else:
        print("[ERROR] test_image1.jpg not found.")

    # Test on test_image2.jpg
    img2 = cv2.imread("test_image2.jpg")
    if img2 is not None:
        res2, _ = d.detect_hierarchical(img2, use_tiled=True)
        print(f"test_image2.jpg (1080p crowd) count: {len(res2)} people detected")
        img2_draw = img2.copy()
        for det in res2:
            box = det["bbox"]
            cv2.rectangle(img2_draw, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (0, 255, 0), 2)
        cv2.imwrite("static/uploads/debug/test_image2_after_fix.jpg", img2_draw)
        print("Saved annotated test_image2 to static/uploads/debug/test_image2_after_fix.jpg")
    else:
        print("[ERROR] test_image2.jpg not found.")

if __name__ == "__main__":
    main()

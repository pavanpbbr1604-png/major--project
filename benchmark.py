import os
import time
import cv2
import numpy as np
from utils.detection import CrowdDetector, DETECTOR_SETTINGS
from utils.preprocessing import adaptive_preprocess
from utils.reliability import analyze_reliability

def run_benchmark():
    print("=== STARTING CROWD PIPELINE ACCURACY BENCHMARK ===")
    
    # Initialize the detector
    detector = CrowdDetector("models/yolov8s.onnx")
    
    test_images = ["test_image1.jpg", "test_image2.jpg"]
    
    results = {}
    
    for img_path in test_images:
        if not os.path.exists(img_path):
            print(f"[ERROR] Test image {img_path} not found.")
            continue
            
        print(f"\nProcessing {img_path}...")
        image = cv2.imread(img_path)
        
        # Preprocessing (imgsz = 2560 for tiled sliding window)
        preprocessed_img, scale_factor = adaptive_preprocess(image, target_size=2560)
        yolo_input = (preprocessed_img * 255.0).astype(np.uint8)
        
        # --- PIPELINE 1: BEFORE (Fast standard single pass) ---
        t0 = time.time()
        # Enforce standard tiled forward only
        pass1_dets, consistency_score = detector.detect_tiled(
            yolo_input, 
            tile_size=640, 
            overlap=128, 
            conf_threshold=0.08
        )
        from utils.redundancy import apply_nms
        pass1_cleaned = apply_nms(pass1_dets, iou_threshold=0.50)
        t_before = (time.time() - t0) * 1000
        
        # --- PIPELINE 2: AFTER (Hierarchical Multi-Stage) ---
        t0 = time.time()
        # Call hierarchical pipeline which will trigger advanced recovery
        hierarchical_dets, consistency_score = detector.detect_hierarchical(
            yolo_input,
            imgsz=2560,
            conf_threshold=0.08,
            use_tiled=True,
            tile_size=640,
            tile_overlap=128
        )
        t_after = (time.time() - t0) * 1000
        
        # Calculate reliability
        rel_before = analyze_reliability(pass1_cleaned, yolo_input.shape, consistency_score=consistency_score)
        rel_after = analyze_reliability(hierarchical_dets, yolo_input.shape, consistency_score=consistency_score)
        
        print(f"[{img_path}] BEFORE count: {len(pass1_cleaned)} | AFTER count: {len(hierarchical_dets)}")
        print(f"[{img_path}] BEFORE time: {t_before:.1f}ms | AFTER time: {t_after:.1f}ms")
        
        results[img_path] = {
            "before_count": len(pass1_cleaned),
            "after_count": len(hierarchical_dets),
            "before_time_ms": t_before,
            "after_time_ms": t_after,
            "before_reliability": rel_before["reliability_score"],
            "after_reliability": rel_after["reliability_score"],
            "recovered_count": len(hierarchical_dets) - len(pass1_cleaned)
        }
        
    print("\n=== BENCHMARK COMPLETED ===")
    for img_path, res in results.items():
        print(f"\nResults for {img_path}:")
        print(f"  Standard count: {res['before_count']} people in {res['before_time_ms']:.1f}ms (Reliability: {res['before_reliability']:.4f})")
        print(f"  Hierarchical count: {res['after_count']} people in {res['after_time_ms']:.1f}ms (Reliability: {res['after_reliability']:.4f})")
        print(f"  Recovered people: +{res['recovered_count']}")

if __name__ == "__main__":
    run_benchmark()

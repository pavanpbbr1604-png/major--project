import time
import os
import cv2
import numpy as np
import psutil
from utils.detection import CrowdDetector, propose_regions, upscale_roi, validate_recovery_detections
from utils.preprocessing import adaptive_preprocess
from utils.redundancy import apply_nms, weighted_box_fusion
from utils.reliability import analyze_reliability
from utils.database import save_analysis

def profile():
    process = psutil.Process(os.getpid())
    print("=== STARTING PIPELINE PROFILING ===")
    
    # Measure memory before
    mem_before = process.memory_info().rss / (1024 * 1024)
    cpu_before = psutil.cpu_percent(interval=0.5)
    
    # 1. Load detector
    detector = CrowdDetector("models/yolov8s.onnx")
    
    image = cv2.imread("test_image1.jpg")
    
    # Start profiling
    t_start = time.perf_counter()
    
    # --- Preprocessing ---
    t0 = time.perf_counter()
    preprocessed_img, scale_factor = adaptive_preprocess(image, target_size=2560)
    yolo_input = (preprocessed_img * 255.0).astype(np.uint8)
    t_prep = (time.perf_counter() - t0) * 1000
    
    # --- Sliding Window ---
    t0 = time.perf_counter()
    pass1_dets, consistency_score = detector.detect_tiled(
        yolo_input, 
        tile_size=640, 
        overlap=128, 
        conf_threshold=0.08
    )
    t_sliding = (time.perf_counter() - t0) * 1000
    
    # --- ROI Proposal ---
    t0 = time.perf_counter()
    rois, max_block_score, global_edge_density = propose_regions(yolo_input, pass1_dets)
    t_proposal = (time.perf_counter() - t0) * 1000
    
    # --- Recovery ---
    t0 = time.perf_counter()
    recovered = []
    running_dets = list(pass1_dets)
    
    # Profile sub-steps of recovery
    t_crop = 0.0
    t_upscale = 0.0
    t_yolo_rec = 0.0
    t_map_validate = 0.0
    
    # We do 1 iteration for profiling
    for roi in rois:
        # Crop
        tc = time.perf_counter()
        x1, y1, x2, y2 = roi
        crop = yolo_input[y1:y2, x1:x2]
        t_crop += (time.perf_counter() - tc) * 1000
        
        if crop.size == 0:
            continue
            
        # Upscale
        tu = time.perf_counter()
        upscaled = upscale_roi(crop)
        t_upscale += (time.perf_counter() - tu) * 1000
        
        # YOLO Recovery
        ty = time.perf_counter()
        roi_dets = detector.detect_standard(upscaled, imgsz=640, conf_threshold=0.05)
        t_yolo_rec += (time.perf_counter() - ty) * 1000
        
        # Map & Validate
        tmv = time.perf_counter()
        mapped = []
        for rd in roi_dets:
            rbox = rd["bbox"]
            gx1 = rbox[0] / 2.0 + x1
            gy1 = rbox[1] / 2.0 + y1
            gx2 = rbox[2] / 2.0 + x1
            gy2 = rbox[3] / 2.0 + y1
            mapped.append({"bbox": [gx1, gy1, gx2, gy2], "confidence": rd["confidence"]})
        valid = validate_recovery_detections(mapped, roi, yolo_input.shape, running_dets)
        recovered.extend(valid)
        t_map_validate += (time.perf_counter() - tmv) * 1000
        
    t_recovery = (time.perf_counter() - t0) * 1000
    
    # --- WBF ---
    t0 = time.perf_counter()
    combined_dets = running_dets + recovered
    fused_wbf = weighted_box_fusion(combined_dets, iou_threshold=0.60)
    t_wbf = (time.perf_counter() - t0) * 1000
    
    # --- NMS ---
    t0 = time.perf_counter()
    final_dets = apply_nms(fused_wbf, iou_threshold=0.75)
    t_nms = (time.perf_counter() - t0) * 1000
    
    # --- SQLite ---
    t0 = time.perf_counter()
    # Mock save to database
    save_analysis(
        analysis_id=f"profile-test-uuid-{time.time()}",
        uploaded_image_names=["test_image1.jpg"],
        count=len(final_dets),
        density=0.15,
        crowd_level="Medium",
        reliability_score=0.85,
        fusion_count=len(final_dets),
        per_image_details={"details": []}
    )
    t_sql = (time.perf_counter() - t0) * 1000
    
    # --- Response Generation ---
    t0 = time.perf_counter()
    # Mock JSON formatting
    response = {
        "status": "success",
        "count": len(final_dets),
        "detections": final_dets,
        "runtime_ms": (time.perf_counter() - t_start) * 1000
    }
    t_resp = (time.perf_counter() - t0) * 1000
    
    t_total = (time.perf_counter() - t_start) * 1000
    
    mem_after = process.memory_info().rss / (1024 * 1024)
    cpu_after = psutil.cpu_percent(interval=0.5)
    
    print("\n=== PROFILE RESULTS ===")
    print(f"Preprocessing: {t_prep:.2f} ms")
    print(f"Sliding Window: {t_sliding:.2f} ms")
    print(f"ROI Proposal: {t_proposal:.2f} ms")
    print(f"Recovery (Total): {t_recovery:.2f} ms")
    print(f"  - Crop: {t_crop:.2f} ms")
    print(f"  - Upscale: {t_upscale:.2f} ms")
    print(f"  - YOLO Inference: {t_yolo_rec:.2f} ms")
    print(f"  - Map & Validate: {t_map_validate:.2f} ms")
    print(f"WBF: {t_wbf:.2f} ms")
    print(f"NMS: {t_nms:.2f} ms")
    print(f"SQLite Write: {t_sql:.2f} ms")
    print(f"Response Gen: {t_resp:.2f} ms")
    print(f"Total Latency: {t_total:.2f} ms")
    print(f"Memory RSS Usage: Before={mem_before:.1f}MB, After={mem_after:.1f}MB, Delta={mem_after-mem_before:.1f}MB")
    print(f"CPU Usage: Before={cpu_before:.1f}%, After={cpu_after:.1f}%")

if __name__ == "__main__":
    profile()

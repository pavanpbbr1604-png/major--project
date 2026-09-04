import os
import time
import cv2
import numpy as np
from utils.detection import CrowdDetector, DETECTOR_SETTINGS, propose_regions, upscale_roi, validate_recovery_detections
from utils.preprocessing import adaptive_preprocess
from utils.redundancy import apply_nms, weighted_box_fusion, compute_iou

def annotate_and_save(image, detections, filename):
    img_copy = image.copy()
    for d in detections:
        box = d["bbox"]
        # Draw red box for recovery detections or standard
        cv2.rectangle(img_copy, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (0, 0, 255), 2)
    os.makedirs("static/uploads/debug", exist_ok=True)
    cv2.imwrite(os.path.join("static/uploads/debug", filename), img_copy)

def run_experiment():
    print("=== STARTING FALSE POSITIVE ISOLATION STUDY ===")
    
    # Load detector
    detector = CrowdDetector("models/yolov8s.onnx")
    
    img_path = "test_image1.jpg"
    if not os.path.exists(img_path):
        print(f"[ERROR] {img_path} not found.")
        return
        
    image = cv2.imread(img_path)
    h, w = image.shape[:2]
    
    # Preprocess
    preprocessed_img, scale_factor = adaptive_preprocess(image, target_size=2560)
    yolo_input = (preprocessed_img * 255.0).astype(np.uint8)
    
    results = {}
    
    # ==========================================
    # Configuration 1: YOLO only
    # ==========================================
    print("\nRunning Configuration 1: YOLO only...")
    t0 = time.time()
    raw1 = detector.detect_standard(yolo_input, imgsz=2560, conf_threshold=0.08)
    # Apply standard NMS
    final1 = apply_nms(raw1, iou_threshold=0.50)
    dt1 = (time.time() - t0) * 1000
    
    avg_conf1 = np.mean([d["confidence"] for d in final1]) if final1 else 0.0
    removed_nms1 = len(raw1) - len(final1)
    
    results["1. YOLO only"] = {
        "count": len(final1),
        "avg_conf": avg_conf1,
        "runtime_ms": dt1,
        "added": len(raw1),
        "removed_wbf": 0,
        "removed_nms": removed_nms1
    }
    annotate_and_save(yolo_input, final1, "isolate_config1.jpg")
    
    # ==========================================
    # Configuration 2: YOLO + Sliding Window
    # ==========================================
    print("Running Configuration 2: YOLO + Sliding Window...")
    t0 = time.time()
    raw2, _ = detector.detect_tiled(yolo_input, tile_size=640, overlap=128, conf_threshold=0.08)
    final2 = apply_nms(raw2, iou_threshold=0.50)
    dt2 = (time.time() - t0) * 1000
    
    avg_conf2 = np.mean([d["confidence"] for d in final2]) if final2 else 0.0
    removed_nms2 = len(raw2) - len(final2)
    
    results["2. YOLO + Sliding Window"] = {
        "count": len(final2),
        "avg_conf": avg_conf2,
        "runtime_ms": dt2,
        "added": len(raw2) - len(raw1),
        "removed_wbf": 0,
        "removed_nms": removed_nms2
    }
    annotate_and_save(yolo_input, final2, "isolate_config2.jpg")
    
    # ==========================================
    # Configuration 3: YOLO + Sliding Window + ROI Proposal (No recovery)
    # ==========================================
    print("Running Configuration 3: YOLO + Sliding Window + ROI Proposal...")
    t0 = time.time()
    raw3, _ = detector.detect_tiled(yolo_input, tile_size=640, overlap=128, conf_threshold=0.08)
    # Calculate proposed ROIs to log, but do not recover
    rois3, _, _ = propose_regions(yolo_input, raw3)
    final3 = apply_nms(raw3, iou_threshold=0.50)
    dt3 = (time.time() - t0) * 1000
    
    avg_conf3 = np.mean([d["confidence"] for d in final3]) if final3 else 0.0
    removed_nms3 = len(raw3) - len(final3)
    
    results["3. YOLO + Sliding Window + ROI Proposal"] = {
        "count": len(final3),
        "avg_conf": avg_conf3,
        "runtime_ms": dt3,
        "added": 0,
        "removed_wbf": 0,
        "removed_nms": removed_nms3
    }
    annotate_and_save(yolo_input, final3, "isolate_config3.jpg")
    
    # ==========================================
    # Configuration 4: YOLO + ROI Proposal + Recovery
    # ==========================================
    print("Running Configuration 4: YOLO + ROI Proposal + Recovery...")
    t0 = time.time()
    # Baseline is standard YOLO (not tiled)
    pass1_4 = detector.detect_standard(yolo_input, imgsz=2560, conf_threshold=0.08)
    rois4, _, _ = propose_regions(yolo_input, pass1_4)
    
    recovered4 = []
    for roi in rois4:
        x1, y1, x2, y2 = roi
        crop = yolo_input[y1:y2, x1:x2]
        if crop.size == 0:
            continue
        upscaled = upscale_roi(crop)
        roi_dets = detector.detect_standard(upscaled, imgsz=640, conf_threshold=0.05)
        mapped = []
        for rd in roi_dets:
            rbox = rd["bbox"]
            gx1 = rbox[0] / 2.0 + x1
            gy1 = rbox[1] / 2.0 + y1
            gx2 = rbox[2] / 2.0 + x1
            gy2 = rbox[3] / 2.0 + y1
            mapped.append({"bbox": [gx1, gy1, gx2, gy2], "confidence": rd["confidence"]})
        valid = validate_recovery_detections(mapped, roi, yolo_input.shape, pass1_4)
        recovered4.extend(valid)
        
    combined4 = pass1_4 + recovered4
    fused_wbf4 = weighted_box_fusion(combined4, iou_threshold=0.60)
    final4 = apply_nms(fused_wbf4, iou_threshold=0.75)
    dt4 = (time.time() - t0) * 1000
    
    avg_conf4 = np.mean([d["confidence"] for d in final4]) if final4 else 0.0
    removed_wbf4 = len(combined4) - len(fused_wbf4)
    removed_nms4 = len(fused_wbf4) - len(final4)
    
    results["4. YOLO + ROI Proposal + Recovery"] = {
        "count": len(final4),
        "avg_conf": avg_conf4,
        "runtime_ms": dt4,
        "added": len(recovered4),
        "removed_wbf": removed_wbf4,
        "removed_nms": removed_nms4
    }
    annotate_and_save(yolo_input, final4, "isolate_config4.jpg")
    
    # ==========================================
    # Configuration 5: Full Pipeline
    # ==========================================
    print("Running Configuration 5: Full Pipeline...")
    t0 = time.time()
    # Baseline is tiled YOLO
    pass1_5, consistency_score = detector.detect_tiled(yolo_input, tile_size=640, overlap=128, conf_threshold=0.08)
    rois5, _, _ = propose_regions(yolo_input, pass1_5)
    
    recovered5 = []
    # 2 iterations maximum
    running_dets5 = list(pass1_5)
    processed_rois5 = []
    
    for iteration in range(1, 3):
        iter_rois, _, _ = propose_regions(yolo_input, running_dets5)
        new_rois = []
        for r_new in iter_rois:
            duplicate = False
            for r_old in processed_rois5:
                inter_x1 = max(r_new[0], r_old[0])
                inter_y1 = max(r_new[1], r_old[1])
                inter_x2 = min(r_new[2], r_old[2])
                inter_y2 = min(r_new[3], r_old[3])
                if inter_x2 > inter_x1 and inter_y2 > inter_y1:
                    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
                    new_area = (r_new[2] - r_new[0]) * (r_new[3] - r_new[1])
                    if inter_area > 0.70 * new_area:
                        duplicate = True
                        break
            if not duplicate:
                new_rois.append(r_new)
                
        if not new_rois:
            break
            
        iter_recovered = []
        for roi in new_rois:
            processed_rois5.append(roi)
            x1, y1, x2, y2 = roi
            crop = yolo_input[y1:y2, x1:x2]
            if crop.size == 0:
                continue
            upscaled = upscale_roi(crop)
            roi_dets = detector.detect_standard(upscaled, imgsz=640, conf_threshold=0.05)
            mapped = []
            for rd in roi_dets:
                rbox = rd["bbox"]
                gx1 = rbox[0] / 2.0 + x1
                gy1 = rbox[1] / 2.0 + y1
                gx2 = rbox[2] / 2.0 + x1
                gy2 = rbox[3] / 2.0 + y1
                mapped.append({"bbox": [gx1, gy1, gx2, gy2], "confidence": rd["confidence"]})
            valid = validate_recovery_detections(mapped, roi, yolo_input.shape, running_dets5)
            iter_recovered.extend(valid)
            
        if not iter_recovered:
            break
            
        recovered5.extend(iter_recovered)
        combined5 = running_dets5 + iter_recovered
        running_dets5 = weighted_box_fusion(combined5, iou_threshold=0.60)
        running_dets5 = apply_nms(running_dets5, iou_threshold=0.75)
        
    final5 = running_dets5
    dt5 = (time.time() - t0) * 1000
    
    avg_conf5 = np.mean([d["confidence"] for d in final5]) if final5 else 0.0
    
    # Calculate WBF / NMS metrics for full run
    combined_total = pass1_5 + recovered5
    fused_total = weighted_box_fusion(combined_total, iou_threshold=0.60)
    final_total = apply_nms(fused_total, iou_threshold=0.75)
    
    removed_wbf5 = len(combined_total) - len(fused_total)
    removed_nms5 = len(fused_total) - len(final_total)
    
    results["5. Full Pipeline"] = {
        "count": len(final5),
        "avg_conf": avg_conf5,
        "runtime_ms": dt5,
        "added": len(recovered5),
        "removed_wbf": removed_wbf5,
        "removed_nms": removed_nms5
    }
    annotate_and_save(yolo_input, final5, "isolate_config5.jpg")
    
    print("\n=== ISOLATION STUDY COMPLETED ===")
    print(f"| Configuration | Count | Avg Conf | Runtime (ms) | Added | Removed WBF | Removed NMS |")
    print(f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for name, res in results.items():
        print(f"| {name} | {res['count']} | {res['avg_conf']:.4f} | {res['runtime_ms']:.1f} | {res['added']} | {res['removed_wbf']} | {res['removed_nms']} |")

if __name__ == "__main__":
    run_experiment()

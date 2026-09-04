import os
import time
import cv2
import numpy as np
from utils.detection import CrowdDetector, propose_regions, upscale_roi, validate_recovery_detections
from utils.preprocessing import adaptive_preprocess
from utils.redundancy import apply_nms, weighted_box_fusion

def analyze_and_draw(image, detections, stage_name, base_img_shape=None):
    """
    Computes all stage metrics and draws boxes on a copy of the image.
    """
    img_draw = image.copy()
    h_img, w_img = image.shape[:2]
    
    count = len(detections)
    if count == 0:
        print(f"\n--- {stage_name} ---")
        print("Detection Count: 0")
        os.makedirs("static/uploads/debug_stages", exist_ok=True)
        cv2.imwrite(f"static/uploads/debug_stages/{stage_name.lower().replace(' ', '_')}.jpg", img_draw)
        return {
            "count": 0, "avg_conf": 0.0, "min_conf": 0.0, "max_conf": 0.0,
            "avg_w": 0.0, "avg_h": 0.0, "avg_aspect": 0.0, "person_count": 0, "rejected_count": 0
        }
        
    confidences = [d["confidence"] for d in detections]
    widths = []
    heights = []
    aspects = []
    person_count = 0
    rejected_count = 0
    
    for d in detections:
        box = d["bbox"]
        conf = d["confidence"]
        
        # Scale coordinates back to current image if they are in different scale
        # (detections are usually in preprocessed image coordinates, i.e., 2560x1920)
        x1, y1, x2, y2 = box
        bw = x2 - x1
        bh = y2 - y1
        widths.append(bw)
        heights.append(bh)
        aspects.append(bw / bh if bh > 0 else 0)
        
        # Draw box
        # Convert to int coordinates for drawing
        ix1, iy1, ix2, iy2 = int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))
        cv2.rectangle(img_draw, (ix1, iy1), (ix2, iy2), (0, 255, 0), 2)
        cv2.putText(img_draw, f"{conf:.2f}", (ix1, max(0, iy1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        
        person_count += 1 # in our case we filter class = 0
        
    avg_conf = np.mean(confidences)
    min_conf = np.min(confidences)
    max_conf = np.max(confidences)
    avg_w = np.mean(widths)
    avg_h = np.mean(heights)
    avg_aspect = np.mean(aspects)
    
    print(f"\n--- {stage_name} ---")
    print(f"Detection Count: {count}")
    print(f"Average Confidence: {avg_conf:.4f}")
    print(f"Minimum Confidence: {min_conf:.4f}")
    print(f"Maximum Confidence: {max_conf:.4f}")
    print(f"Average Bounding Box Width: {avg_w:.1f} px")
    print(f"Average Bounding Box Height: {avg_h:.1f} px")
    print(f"Average Aspect Ratio: {avg_aspect:.4f}")
    print(f"Person Detections (Class 0): {person_count}")
    print(f"Rejected Detections (Class != 0): {rejected_count}")
    
    os.makedirs("static/uploads/debug_stages", exist_ok=True)
    cv2.imwrite(f"static/uploads/debug_stages/{stage_name.lower().replace(' ', '_')}.jpg", img_draw)
    
    return {
        "count": count, "avg_conf": avg_conf, "min_conf": min_conf, "max_conf": max_conf,
        "avg_w": avg_w, "avg_h": avg_h, "avg_aspect": avg_aspect, "person_count": person_count, "rejected_count": rejected_count
    }

def run_debug_pipeline(img_path):
    print(f"\n===========================================================")
    print(f"DEBUGGING PIPELINE FOR IMAGE: {img_path}")
    print(f"===========================================================")
    
    image = cv2.imread(img_path)
    detector = CrowdDetector("models/yolov8s.onnx")
    
    # Stage 1: Raw YOLO detections on original image
    # Note: detect_standard expects images normalized/scaled appropriately.
    # To run raw YOLO on original image, we pass original image to detect_standard.
    t0 = time.time()
    raw_original_dets = detector.detect_standard(image, imgsz=640, conf_threshold=0.08)
    analyze_and_draw(image, raw_original_dets, "Stage 1 Raw YOLO on Original")
    
    # Stage 2: After preprocessing
    # Preprocess image to 2560 target size
    preprocessed_img, scale_factor = adaptive_preprocess(image, target_size=2560)
    yolo_input = (preprocessed_img * 255.0).astype(np.uint8)
    
    # Run raw YOLO on preprocessed image (Stage 2 Raw YOLO)
    raw_preproc_dets = detector.detect_standard(yolo_input, imgsz=640, conf_threshold=0.08)
    analyze_and_draw(yolo_input, raw_preproc_dets, "Stage 2 Raw YOLO after Preprocessing")
    
    # Stage 3: After sliding window inference
    from utils.tiling import run_tiled_inference
    tiled_dets, consistency_score = run_tiled_inference(yolo_input, detector, "cpu", tile_size=640, overlap=128, conf_threshold=0.08)
    analyze_and_draw(yolo_input, tiled_dets, "Stage 3 Sliding Window Tiled Detections")
    
    # Stage 4: After tile coordinate remapping and dual-stream fusion
    combined = tiled_dets + raw_preproc_dets
    pass1_dets = weighted_box_fusion(combined, iou_threshold=0.60)
    pass1_dets = apply_nms(pass1_dets, iou_threshold=0.75)
    analyze_and_draw(yolo_input, pass1_dets, "Stage 4 Tiled and Standard Stream Fusion")
    
    # Stage 5: After ROI proposal
    rois, max_block_score, global_edge_density = propose_regions(yolo_input, pass1_dets)
    print(f"\n--- Stage 5 ROI Proposals ---")
    print(f"Number of proposed ROIs: {len(rois)}")
    print(f"Max Block Score: {max_block_score:.4f}, Global Edge Density: {global_edge_density:.4f}")
    
    # Stage 6: After ROI recovery
    running_dets = list(pass1_dets)
    processed_rois = []
    recovered_in_iter = []
    
    # Run iteration 1
    iter_rois = rois
    upscaled_crops = []
    valid_roi_indices = []
    for idx, roi in enumerate(iter_rois):
        processed_rois.append(roi)
        x1, y1, x2, y2 = roi
        crop = yolo_input[y1:y2, x1:x2]
        if crop.size == 0:
            continue
        upscaled = upscale_roi(crop)
        upscaled_crops.append(upscaled)
        valid_roi_indices.append((idx, roi))
        
    batch_roi_dets = detector.detect_batch(upscaled_crops, imgsz=640, conf_threshold=0.05)
    
    for i, (idx, roi) in enumerate(valid_roi_indices):
        x1, y1, x2, y2 = roi
        roi_dets = batch_roi_dets[i]
        mapped_roi_dets = []
        for rd in roi_dets:
            rbox = rd["bbox"]
            gx1 = rbox[0] / 2.0 + x1
            gy1 = rbox[1] / 2.0 + y1
            gx2 = rbox[2] / 2.0 + x1
            gy2 = rbox[3] / 2.0 + y1
            mapped_roi_dets.append({"bbox": [gx1, gy1, gx2, gy2], "confidence": rd["confidence"]})
        valid_roi_dets = validate_recovery_detections(mapped_roi_dets, roi, yolo_input.shape, running_dets)
        recovered_in_iter.extend(valid_roi_dets)
        
    analyze_and_draw(yolo_input, recovered_in_iter, "Stage 6 Recovered Detections")
    
    # Stage 7: After Weighted Box Fusion
    combined_dets = running_dets + recovered_in_iter
    fused_wbf = weighted_box_fusion(combined_dets, iou_threshold=0.60)
    analyze_and_draw(yolo_input, fused_wbf, "Stage 7 After Weighted Box Fusion")
    
    # Stage 8: After Non Maximum Suppression
    final_dets = apply_nms(fused_wbf, iou_threshold=0.75)
    analyze_and_draw(yolo_input, final_dets, "Stage 8 After Non Maximum Suppression")
    
    # Stage 9: Final output scaled back to original image
    final_scaled = []
    for det in final_dets:
        bbox = det["bbox"]
        scaled_bbox = [
            bbox[0] / scale_factor,
            bbox[1] / scale_factor,
            bbox[2] / scale_factor,
            bbox[3] / scale_factor
        ]
        final_scaled.append({"bbox": scaled_bbox, "confidence": det["confidence"]})
    analyze_and_draw(image, final_scaled, "Stage 9 Final Output scaled to Original")

if __name__ == "__main__":
    run_debug_pipeline("test_image1.jpg")
    run_debug_pipeline("test_image2.jpg")

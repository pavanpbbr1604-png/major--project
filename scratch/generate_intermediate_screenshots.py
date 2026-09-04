import os
import sys
import cv2
import numpy as np

sys.path.append(os.path.abspath("."))
from utils.detection import CrowdDetector
from utils.preprocessing import adaptive_preprocess
from utils.redundancy import apply_nms
from utils.density import estimate_density

def create_intermediate_outputs():
    output_dir = os.path.join("docs", "figures", "intermediate")
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Load Raw Image
    raw_path = os.path.join("testing images", "train 1.png")
    if not os.path.exists(raw_path):
        raw_path = "test_image1.jpg"
        
    image = cv2.imread(raw_path)
    h, w = image.shape[:2]
    
    # Save Stage 1: Raw Input
    cv2.imwrite(os.path.join(output_dir, "1_raw_input.jpg"), image)
    print("[INFO] Saved Stage 1: 1_raw_input.jpg")
    
    # Save Stage 2: Preprocessed Image
    preprocessed_img, scale_factor = adaptive_preprocess(image, target_size=2560, is_crowded=True)
    preprocessed_uint8 = (preprocessed_img * 255.0).astype(np.uint8)
    cv2.imwrite(os.path.join(output_dir, "2_preprocessed.jpg"), preprocessed_uint8)
    print("[INFO] Saved Stage 2: 2_preprocessed.jpg")
    
    # Stage 3: Detect Raw Boxes
    detector = CrowdDetector("models/yolov8s.onnx")
    raw_dets, consistency_score = detector.detect_hierarchical(
        preprocessed_uint8,
        imgsz=2560,
        conf_threshold=0.25,
        use_tiled=True,
        tile_size=640,
        tile_overlap=128
    )
    
    # Scale boxes back
    scaled_dets = []
    for det in raw_dets:
        bbox = det["bbox"]
        scaled_dets.append({
            "bbox": [bbox[0]/scale_factor, bbox[1]/scale_factor, bbox[2]/scale_factor, bbox[3]/scale_factor],
            "confidence": det["confidence"]
        })
        
    # Stage 3A: Standard NMS (BEFORE - Shows duplicates & fragment splits)
    before_img = image.copy()
    # Simple naive NMS (IoU only)
    boxes_only = np.array([d["bbox"] for d in scaled_dets])
    scores_only = np.array([d["confidence"] for d in scaled_dets])
    indices = cv2.dnn.NMSBoxes(boxes_only.tolist(), scores_only.tolist(), 0.25, 0.45)
    
    if len(indices) > 0:
        for i in indices.flatten():
            box = boxes_only[i].astype(int)
            cv2.rectangle(before_img, (box[0], box[1]), (box[2], box[3]), (0, 0, 255), 2) # Red boxes for unrefined
    cv2.imwrite(os.path.join(output_dir, "3_before_custom_nms.jpg"), before_img)
    print("[INFO] Saved Stage 3A (BEFORE): 3_before_custom_nms.jpg")
    
    # Stage 3B: Custom Containment & Fragment-Aware NMS (AFTER - Merged full body boxes)
    final_dets = apply_nms(scaled_dets, iou_threshold=0.50, iom_threshold=0.70)
    after_img = image.copy()
    for det in final_dets:
        box = np.array(det["bbox"]).astype(int)
        cv2.rectangle(after_img, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2) # Green boxes for refined
        cv2.putText(after_img, f"{det['confidence']:.2f}", (box[0], max(15, box[1]-5)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    cv2.imwrite(os.path.join(output_dir, "4_after_custom_nms.jpg"), after_img)
    print("[INFO] Saved Stage 3B (AFTER): 4_after_custom_nms.jpg")
    
    # Stage 4: Subsampled Binary Occupancy Grid
    scale = 8
    sh, sw = max(1, h // scale), max(1, w // scale)
    grid_mask = np.zeros((sh, sw, 3), dtype=np.uint8)
    
    for det in final_dets:
        bbox = det["bbox"]
        x1 = max(0, int(round(bbox[0] / scale)))
        y1 = max(0, int(round(bbox[1] / scale)))
        x2 = min(sw, int(round(bbox[2] / scale)))
        y2 = min(sh, int(round(bbox[3] / scale)))
        if x2 > x1 and y2 > y1:
            grid_mask[y1:y2, x1:x2] = [0, 255, 0] # Green for occupied cells
            
    # Resize grid mask to match original image height/width for clear viewing
    grid_visual = cv2.resize(grid_mask, (w, h), interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(os.path.join(output_dir, "5_binary_occupancy_grid.jpg"), grid_visual)
    print("[INFO] Saved Stage 4: 5_binary_occupancy_grid.jpg")
    
    print("\n=== ALL INTERMEDIATE SCREENSHOTS GENERATED SUCCESSFULLY ===")
    print(f"Directory: {output_dir}")

if __name__ == "__main__":
    create_intermediate_outputs()

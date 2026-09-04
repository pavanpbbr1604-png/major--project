import cv2
import time
import os
import numpy as np
from utils.detection import CrowdDetector
from utils.preprocessing import adaptive_preprocess

def run_annotated_validation():
    print("=== STARTING DIRECT BACKEND VALIDATION ===")
    
    # Load detector
    detector = CrowdDetector("models/yolov8s.onnx")
    
    # Load image
    img_path = "test_image1.jpg"
    if not os.path.exists(img_path):
        print(f"[ERROR] Source image '{img_path}' not found!")
        return
        
    image = cv2.imread(img_path)
    print(f"Loaded image size: {image.shape}")
    
    t0 = time.time()
    
    # 1. Run adaptive preprocessing with is_crowded=True (as tiling is active)
    preprocessed_img, scale_factor = adaptive_preprocess(image, target_size=2560, is_crowded=True)
    yolo_input = (preprocessed_img * 255.0).astype(np.uint8)
    
    # 2. Run hierarchical detection pipeline
    # This matches the query configuration tiled=true, imgsz=2560
    detections, consistency_score = detector.detect_hierarchical(
        yolo_input,
        imgsz=2560,
        conf_threshold=0.08,
        use_tiled=True,
        tile_size=640,
        tile_overlap=128
    )
    
    # 3. Scale coordinates back to original image space
    scaled_detections = []
    for det in detections:
        bbox = det["bbox"]
        scaled_bbox = [
            bbox[0] / scale_factor,
            bbox[1] / scale_factor,
            bbox[2] / scale_factor,
            bbox[3] / scale_factor
        ]
        scaled_detections.append({
            "bbox": scaled_bbox,
            "confidence": det["confidence"]
        })
        
    # 4. Draw detections on the original image
    annotated = image.copy()
    for det in scaled_detections:
        bbox = det["bbox"]
        conf = det["confidence"]
        x1, y1, x2, y2 = int(round(bbox[0])), int(round(bbox[1])), int(round(bbox[2])), int(round(bbox[3]))
        # Draw bounding box (green)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        # Draw confidence label
        label = f"{conf:.2f}"
        cv2.putText(annotated, label, (x1, max(y1 - 5, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
    # Create target directories
    os.makedirs(os.path.join("static", "uploads"), exist_ok=True)
    out_path = os.path.join("static", "uploads", "verification_output.jpg")
    cv2.imwrite(out_path, annotated)
    
    print(f"Detections count: {len(scaled_detections)}")
    print(f"Annotated image saved successfully to: {out_path}")
    print(f"Total time elapsed: {time.time() - t0:.2f}s")
    print("=== BACKEND VALIDATION COMPLETED ===")

if __name__ == "__main__":
    run_annotated_validation()

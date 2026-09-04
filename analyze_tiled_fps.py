import os
import cv2
import numpy as np
from utils.detection import CrowdDetector
from utils.preprocessing import adaptive_preprocess
from utils.redundancy import apply_nms, compute_iou

def analyze():
    detector = CrowdDetector("models/yolov8s.onnx")
    img_path = "test_image1.jpg"
    image = cv2.imread(img_path)
    h, w = image.shape[:2]
    
    preprocessed_img, scale_factor = adaptive_preprocess(image, target_size=2560)
    yolo_input = (preprocessed_img * 255.0).astype(np.uint8)
    
    # Run standard (yolo only)
    raw1 = detector.detect_standard(yolo_input, imgsz=2560, conf_threshold=0.08)
    final1 = apply_nms(raw1, iou_threshold=0.50)
    
    # Run tiled (sliding window)
    raw2, _ = detector.detect_tiled(yolo_input, tile_size=640, overlap=128, conf_threshold=0.08)
    final2 = apply_nms(raw2, iou_threshold=0.50)
    
    print(f"Standard detections: {len(final1)}")
    print(f"Tiled detections: {len(final2)}")
    
    # Find new detections introduced by sliding window (have low IoU with standard detections)
    new_dets = []
    for d2 in final2:
        box2 = d2["bbox"]
        matched = False
        for d1 in final1:
            if compute_iou(box2, d1["bbox"]) > 0.30:
                matched = True
                break
        if not matched:
            new_dets.append(d2)
            
    print(f"New detections introduced: {len(new_dets)}")
    
    # Analyze and print characteristics of new detections
    for i, d in enumerate(new_dets):
        box = d["bbox"]
        bx_w = box[2] - box[0]
        bx_h = box[3] - box[1]
        ratio = bx_w / bx_h if bx_h > 0 else 0
        area = bx_w * bx_h
        cy = (box[1] + box[3]) / 2.0
        cx = (box[0] + box[2]) / 2.0
        
        # Categorize roughly based on coordinates in test_image1 (width=2560, height=1440 or scaled)
        # Standard scaled target size is 2560 (so max dimension is 2560).
        # Let's print out features
        print(f"Det {i}: bbox=[{box[0]:.1f}, {box[1]:.1f}, {box[2]:.1f}, {box[3]:.1f}] | conf={d['confidence']:.3f} | aspect={ratio:.3f} | center=({cx:.1f}, {cy:.1f})")

if __name__ == "__main__":
    analyze()

import os
import time
import cv2
import numpy as np

import sys
sys.path.append(os.path.abspath("."))

from utils.detection import CrowdDetector, DETECTOR_SETTINGS
from utils.preprocessing import adaptive_preprocess
from utils.redundancy import apply_nms
from utils.density import estimate_density
from utils.reliability import analyze_reliability
from utils.classification import classify_crowd
from utils.counting import count_people

DETECTOR_SETTINGS["DEBUG_MODE"] = False
detector = CrowdDetector("models/yolov8s.onnx")

img_path = os.path.join("testing images", "figures", "test_image1.jpg")
img = cv2.imread(img_path)
t0 = time.time()
prep_img, scale = adaptive_preprocess(img, target_size=2560, is_crowded=True)
yolo_input = (prep_img * 255.0).astype(np.uint8)
raw_dets, consistency = detector.detect_hierarchical(
    yolo_input, imgsz=2560, conf_threshold=0.25, use_tiled=True, tile_size=640, tile_overlap=128
)
scaled_dets = [
    {
        "bbox": [d["bbox"][0] / scale, d["bbox"][1] / scale, d["bbox"][2] / scale, d["bbox"][3] / scale],
        "confidence": d["confidence"]
    }
    for d in raw_dets
]
final_dets = apply_nms(scaled_dets, iou_threshold=0.50, iom_threshold=0.70)
t1 = time.time()

density = estimate_density(final_dets, img.shape)
rel = analyze_reliability(final_dets, yolo_input.shape, consistency_score=consistency)
cls = classify_crowd(density["density_percentage"], len(final_dets), density["crowd_density_score"])

print(f"Done in {t1 - t0:.2f}s!")
print(f"Detections: {len(final_dets)} (raw {len(raw_dets)})")
print(f"Density: {density['density_percentage']:.2f}%")
print(f"Reliability: {rel['reliability_score']:.4f}")
print(f"Level: {cls['crowd_level']}")

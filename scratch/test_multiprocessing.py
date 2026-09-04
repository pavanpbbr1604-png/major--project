import os
import sys
import time
import cv2
import numpy as np
from concurrent.futures import ProcessPoolExecutor

sys.path.append(os.path.abspath("."))
from utils.detection import CrowdDetector, DETECTOR_SETTINGS
from utils.preprocessing import adaptive_preprocess
from utils.redundancy import apply_nms

def evaluate_image_task(img_name):
    DETECTOR_SETTINGS["DEBUG_MODE"] = False
    detector = CrowdDetector("models/yolov8s.onnx")
    img_path = os.path.join("testing images", "figures", img_name)
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
    return img_name, len(final_dets), t1 - t0

def main():
    t_start = time.time()
    images = ["train 1.png", "train 2.png"]
    with ProcessPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(evaluate_image_task, images))
    print("Parallel results:", results)
    print(f"Total elapsed: {time.time() - t_start:.2f}s")

if __name__ == "__main__":
    main()

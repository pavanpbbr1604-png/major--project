import os
import time
import urllib.request
import cv2
import numpy as np
from utils.detection import CrowdDetector
from utils.preprocessing import adaptive_preprocess
from utils.reliability import analyze_reliability

# Images representing empirical edge cases
ROBUSTNESS_IMAGES = [
    {
        "name": "test_image1.jpg",
        "url": None,
        "scenario": "Railway Station / Moderate Crowd",
        "conf_threshold": 0.08,
        "use_tiled": True
    },
    {
        "name": "test_image2.jpg",
        "url": None,
        "scenario": "Railway Station / Dense Crowd",
        "conf_threshold": 0.08,
        "use_tiled": True
    },
    {
        "name": "bus.jpg",
        "url": "https://raw.githubusercontent.com/ultralytics/yolov5/master/data/images/bus.jpg",
        "scenario": "Sparse Crowd / Outdoor Daylight",
        "conf_threshold": 0.25,
        "use_tiled": False
    },
    {
        "name": "zidane.jpg",
        "url": "https://raw.githubusercontent.com/ultralytics/yolov5/master/data/images/zidane.jpg",
        "scenario": "Indoor / Occlusion / Individual",
        "conf_threshold": 0.25,
        "use_tiled": False
    },
    {
        "name": "basketball2.png",
        "url": "https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/basketball2.png",
        "scenario": "Motion Blur / High Occlusion",
        "conf_threshold": 0.25,
        "use_tiled": False
    }
]

def download_assets():
    print("[INFO] Setting up robustness test assets...")
    for img in ROBUSTNESS_IMAGES:
        if img["url"] and not os.path.exists(img["name"]):
            try:
                print(f"Downloading {img['name']}...")
                headers = {'User-Agent': 'Mozilla/5.0'}
                req = urllib.request.Request(img["url"], headers=headers)
                with urllib.request.urlopen(req) as response, open(img["name"], "wb") as out:
                    out.write(response.read())
            except Exception as e:
                print(f"[WARNING] Could not download {img['name']} ({e})")

def run_tests():
    download_assets()
    
    detector = CrowdDetector("models/yolov8s.onnx")
    print("\n=== RUNNING ROBUSTNESS EVALUATION ===")
    
    for img_data in ROBUSTNESS_IMAGES:
        name = img_data["name"]
        scenario = img_data["scenario"]
        
        if not os.path.exists(name):
            print(f"[WARNING] Skipped missing image: {name}")
            continue
            
        image = cv2.imread(name)
        h, w = image.shape[:2]
        
        t0 = time.time()
        # Run preprocessor
        preprocessed_img, scale_factor = adaptive_preprocess(image, target_size=2560, is_crowded=img_data["use_tiled"])
        yolo_input = (preprocessed_img * 255.0).astype(np.uint8)
        
        # Run detector
        detections, consistency_score = detector.detect_hierarchical(
            yolo_input,
            imgsz=2560,
            conf_threshold=img_data["conf_threshold"],
            use_tiled=img_data["use_tiled"],
            tile_size=640,
            tile_overlap=128
        )
        runtime_ms = (time.time() - t0) * 1000
        
        # Compute reliability
        rel_data = analyze_reliability(detections, yolo_input.shape, consistency_score=consistency_score)
        
        print(f"\nScenario: {scenario} ({name})")
        print(f"  Shape: {w}x{h}")
        print(f"  Detections: {len(detections)}")
        print(f"  Reliability Score: {rel_data['reliability_score']:.4f}")
        print(f"  Avg Confidence: {rel_data['average_confidence']:.4f}")
        print(f"  Runtime: {runtime_ms:.1f} ms")

if __name__ == "__main__":
    run_tests()

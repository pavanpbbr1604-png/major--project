import cv2
import numpy as np
from utils.detection import CrowdDetector
from utils.preprocessing import adaptive_preprocess
from utils.redundancy import apply_nms

detector = CrowdDetector("models/yolov8s.onnx")
image = cv2.imread("test_image2.jpg")
preprocessed_img, scale_factor = adaptive_preprocess(image, target_size=2560)
yolo_input = (preprocessed_img * 255.0).astype(np.uint8)

# Run raw tiled inference to check counts
raw_dets, _ = detector.detect_tiled(yolo_input, tile_size=640, overlap=128, conf_threshold=0.08)
clean_dets = apply_nms(raw_dets, iou_threshold=0.50)

print("Number of detections returned by detect_tiled (with filters):", len(clean_dets))
# Print out details of some detections to inspect aspect ratios
for i, d in enumerate(clean_dets[:20]):
    box = d["bbox"]
    w = box[2] - box[0]
    h = box[3] - box[1]
    aspect = w / h if h > 0 else 0
    print(f"Det {i}: bbox=[{box[0]:.1f}, {box[1]:.1f}, {box[2]:.1f}, {box[3]:.1f}] | conf={d['confidence']:.3f} | aspect={aspect:.3f}")

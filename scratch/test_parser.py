import cv2
import numpy as np
import os
from utils.detection import CrowdDetector

def test():
    # Make sure scratch directory exists
    os.makedirs("scratch", exist_ok=True)
    
    detector = CrowdDetector("models/yolov8s.onnx")
    image = cv2.imread("test_image1.jpg")
    
    from utils.preprocessing import adaptive_preprocess
    preprocessed_img, scale_factor = adaptive_preprocess(image, target_size=2560)
    yolo_input = (preprocessed_img * 255.0).astype(np.uint8)
    
    img_h, img_w = yolo_input.shape[:2]
    blob = cv2.dnn.blobFromImage(yolo_input, 1.0, (640, 640), swapRB=True, crop=False)
    detector.net.setInput(blob)
    outputs = np.squeeze(detector.net.forward()).T # shape: (8400, 84)
    
    # Current logic
    current_dets = []
    for row in outputs:
        confidence = float(row[4])
        if confidence >= 0.08:
            xc, yc, w, h = row[0], row[1], row[2], row[3]
            current_dets.append({"bbox": [xc, yc, w, h], "confidence": confidence})
            
    # Corrected logic
    corrected_dets = []
    for row in outputs:
        scores = row[4:]
        class_id = np.argmax(scores)
        confidence = float(scores[class_id])
        if class_id == 0 and confidence >= 0.08:
            xc, yc, w, h = row[0], row[1], row[2], row[3]
            corrected_dets.append({"bbox": [xc, yc, w, h], "confidence": confidence, "class_id": class_id})
            
    print(f"Upscaled image size: {img_w}x{img_h}")
    print(f"Current parsing logic count (conf >= 0.08): {len(current_dets)}")
    print(f"Corrected class-argmax logic count (conf >= 0.08 & class == person): {len(corrected_dets)}")
    
    # Let's count how many non-person classes had row[4] >= 0.08
    contaminations = {}
    for row in outputs:
        person_conf = float(row[4])
        if person_conf >= 0.08:
            scores = row[4:]
            class_id = np.argmax(scores)
            if class_id != 0:
                class_name = f"Class {class_id}"
                contaminations[class_name] = contaminations.get(class_name, 0) + 1
                
    print("Contamination class breakdown (objects misclassified as person):")
    for cls, count in sorted(contaminations.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cls}: {count} occurrences")

if __name__ == "__main__":
    test()

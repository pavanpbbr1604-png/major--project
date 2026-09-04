import cv2
import numpy as np
import os

def main():
    net = cv2.dnn.readNetFromONNX("models/yolov8s.onnx")
    img = cv2.imread("test_image1.jpg")
    h, w = img.shape[:2]
    
    # Preprocess
    blob = cv2.dnn.blobFromImage(img, 1.0, (640, 640), swapRB=True, crop=False)
    net.setInput(blob)
    outputs = net.forward()
    
    outputs = np.squeeze(outputs).T # shape: (8400, 84)
    x_factor = w / 640.0
    y_factor = h / 640.0
    
    raw_dets = []
    for row in outputs:
        # Check person class directly at index 4 (class 0)
        conf = float(row[4])
        if conf >= 0.25:
            xc, yc, box_w, box_h = row[0], row[1], row[2], row[3]
            x1 = int((xc - box_w/2) * x_factor)
            y1 = int((yc - box_h/2) * y_factor)
            x2 = int((xc + box_w/2) * x_factor)
            y2 = int((yc + box_h/2) * y_factor)
            
            raw_dets.append({
                "bbox": [x1, y1, x2, y2],
                "confidence": conf
            })
            
    # Apply standard NMS
    bboxes = [d["bbox"] for d in raw_dets]
    confs = [d["confidence"] for d in raw_dets]
    indices = cv2.dnn.NMSBoxes(bboxes, confs, 0.25, 0.45)
    
    print(f"Total raw detections (conf >= 0.25): {len(raw_dets)}")
    print(f"Total NMS detections: {len(indices)}")
    
    # Annotate and save
    img_draw = img.copy()
    for idx in indices:
        if isinstance(idx, (list, np.ndarray)):
            idx = idx[0]
        box = bboxes[idx]
        cv2.rectangle(img_draw, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
        cv2.putText(img_draw, f"{confs[idx]:.2f}", (box[0], box[1]-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
    os.makedirs("static/uploads/debug", exist_ok=True)
    cv2.imwrite("static/uploads/debug/test_opencv_raw.jpg", img_draw)
    print("Saved annotated image to static/uploads/debug/test_opencv_raw.jpg")

if __name__ == "__main__":
    main()

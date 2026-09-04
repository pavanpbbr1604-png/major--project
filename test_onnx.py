import cv2
import numpy as np
import os

net = cv2.dnn.readNetFromONNX("models/yolov8s.onnx")
image = cv2.imread("test_image1.jpg")
h, w = image.shape[:2]

# YOLOv8 expect 640x640
blob = cv2.dnn.blobFromImage(image, 1.0, (640, 640), swapRB=True, crop=False)
net.setInput(blob)
outputs = net.forward()

print("Output shape:", outputs.shape)
outputs = np.squeeze(outputs).T # shape (8400, 84)

# Print top confidences at index 4
person_confs = outputs[:, 4]
print("Max person confidence:", person_confs.max())
print("Number of boxes above 0.01:", np.sum(person_confs > 0.01))
print("Number of boxes above 0.05:", np.sum(person_confs > 0.05))
print("Number of boxes above 0.10:", np.sum(person_confs > 0.10))
print("Number of boxes above 0.25:", np.sum(person_confs > 0.25))

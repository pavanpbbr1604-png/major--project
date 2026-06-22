import numpy as np
from ultralytics import YOLO
import torch
from .tiling import run_tiled_inference

class CrowdDetector:
    def __init__(self, model_path: str = "yolov8x.pt"):
        """
        Initializes the YOLOv8x detector.
        If GPU is available, loads the model to CUDA.
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = YOLO(model_path)
        self.model.to(self.device)

    def detect_standard(self, image: np.ndarray, imgsz: int = 1280, conf_threshold: float = 0.25, use_tta: bool = False) -> list[dict]:
        """
        Performs standard detection on the entire image using high resolution (1280, 1536, 1920).
        Supports Test Time Augmentation (TTA) via augment=True.
        """
        results = self.model.predict(
            source=image,
            imgsz=imgsz,
            conf=conf_threshold,
            classes=[0],  # Class 0 is 'person' in COCO
            augment=use_tta,
            device=self.device,
            verbose=False
        )
        
        detections = []
        if len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                detections.append({
                    "bbox": [float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])],
                    "confidence": conf
                })
        return detections

    def detect_tiled(self, image: np.ndarray, tile_size: int = 640, overlap: int = 128, conf_threshold: float = 0.25) -> tuple[list[dict], float]:
        """
        Delegates tiled inference to tiling.py.
        Returns global mapped detections and overlap consistency score.
        """
        return run_tiled_inference(
            image=image,
            model=self.model,
            device=self.device,
            tile_size=tile_size,
            overlap=overlap,
            conf_threshold=conf_threshold
        )

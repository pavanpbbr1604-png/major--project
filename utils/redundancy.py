import numpy as np

def compute_iou(box1: list[float], box2: list[float]) -> float:
    """
    Computes Intersection over Union (IoU) between two bounding boxes [x1, y1, x2, y2].
    """
    x1_max = max(box1[0], box2[0])
    y1_max = max(box1[1], box2[1])
    x2_min = min(box1[2], box2[2])
    y2_min = min(box1[3], box2[3])

    inter_width = max(0.0, x2_min - x1_max)
    inter_height = max(0.0, y2_min - y1_max)
    inter_area = inter_width * inter_height

    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union_area = area1 + area2 - inter_area

    if union_area <= 0:
        return 0.0
    return inter_area / union_area

def apply_nms(detections: list[dict], iou_threshold: float = 0.5) -> list[dict]:
    """
    Applies Non-Maximum Suppression (NMS) to eliminate overlapping bounding boxes.
    Keeps boxes with higher confidence.
    Args:
        detections: list of dicts with keys "bbox" and "confidence".
        iou_threshold: Overlap limit above which redundant boxes are suppressed.
    """
    if not detections:
        return []

    # Sort detections by confidence descending
    sorted_dets = sorted(detections, key=lambda x: x["confidence"], reverse=True)
    
    kept_detections = []
    
    while sorted_dets:
        best_det = sorted_dets.pop(0)
        kept_detections.append(best_det)
        
        # Filter remaining boxes
        sorted_dets = [
            det for det in sorted_dets 
            if compute_iou(best_det["bbox"], det["bbox"]) < iou_threshold
        ]
        
    return kept_detections

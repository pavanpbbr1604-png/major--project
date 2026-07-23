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

def apply_nms(detections: list[dict], iou_threshold: float = 0.5, iom_threshold: float = 0.80) -> list[dict]:
    """
    Applies Non-Maximum Suppression (NMS) to eliminate overlapping bounding boxes.
    Keeps boxes with higher confidence. Checks both standard IoU and containment IoM.
    Optimized using NumPy vectorization.
    """
    if not detections:
        return []

    # Convert detections to numpy arrays for fast vectorized operations
    bboxes = np.array([d["bbox"] for d in detections], dtype=np.float32)
    scores = np.array([d["confidence"] for d in detections], dtype=np.float32)

    x1 = bboxes[:, 0]
    y1 = bboxes[:, 1]
    x2 = bboxes[:, 2]
    y2 = bboxes[:, 3]

    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h

        union = areas[i] + areas[order[1:]] - inter
        iou = np.zeros_like(inter)
        np.divide(inter, union, out=iou, where=union > 0)

        # Intersection over Minimum Area (IoM) to check containment
        min_areas = np.minimum(areas[i], areas[order[1:]])
        iom = np.zeros_like(inter)
        np.divide(inter, min_areas, out=iom, where=min_areas > 0)

        # Suppress if IoU is high (overlapping) OR IoM is high (contained)
        inds = np.where((iou < iou_threshold) & (iom < iom_threshold))[0]
        order = order[inds + 1]

    return [detections[idx] for idx in keep]

def weighted_box_fusion(detections: list[dict], iou_threshold: float = 0.55) -> list[dict]:
    """
    Applies Weighted Box Fusion (WBF) to combine overlapping detections.
    For boxes that have IoU >= iou_threshold, we blend their coordinates 
    weighted by their confidence scores, keeping the highest confidence in the group.
    
    Args:
        detections: List of dicts with keys 'bbox' [x1, y1, x2, y2] and 'confidence'.
        iou_threshold: IoU threshold above which boxes are considered duplicates and fused.
        
    Returns:
        List of fused/blended detections.
    """
    if not detections:
        return []
        
    # Sort detections by confidence descending
    sorted_dets = sorted(detections, key=lambda x: x["confidence"], reverse=True)
    
    fused_groups = []
    
    for det in sorted_dets:
        box = det["bbox"]
        
        # Check if this detection matches any existing fused group
        matched = False
        for group in fused_groups:
            # We compare with the current averaged box of the group
            group_box = group["bbox"]
            iou = compute_iou(box, group_box)
            if iou >= iou_threshold:
                # Add detection to this group
                group["detections"].append(det)
                matched = True
                break
                
        if not matched:
            # Create a new group
            fused_groups.append({
                "bbox": list(box),
                "detections": [det]
            })
            
    # Recompute averaged coordinates and confidences for each group
    final_detections = []
    for group in fused_groups:
        dets = group["detections"]
        
        # Weighted average of coordinates
        total_weight = sum(d["confidence"] for d in dets)
        
        x1_fused = sum(d["bbox"][0] * d["confidence"] for d in dets) / total_weight
        y1_fused = sum(d["bbox"][1] * d["confidence"] for d in dets) / total_weight
        x2_fused = sum(d["bbox"][2] * d["confidence"] for d in dets) / total_weight
        y2_fused = sum(d["bbox"][3] * d["confidence"] for d in dets) / total_weight
        
        # Keep maximum confidence as the score for the fused box
        max_conf = max(d["confidence"] for d in dets)
        
        final_detections.append({
            "bbox": [float(x1_fused), float(y1_fused), float(x2_fused), float(y2_fused)],
            "confidence": float(max_conf)
        })
        
    return final_detections


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

def apply_nms(detections: list[dict], iou_threshold: float = 0.5, iom_threshold: float = 0.70, return_stats: bool = False) -> list[dict] | tuple[list[dict], dict]:
    """
    Applies Non-Maximum Suppression (NMS) to eliminate overlapping bounding boxes.
    Keeps boxes with higher confidence. Checks both standard IoU and containment IoM.
    Optimized using NumPy vectorization.
    """
    if not detections:
        return ([], {"iou_removed": 0, "iom_removed": 0, "total_removed": 0}) if return_stats else []

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
    iou_removed_count = 0
    iom_removed_count = 0

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

        # Track breakdown of suppression mechanisms
        iou_suppressed_mask = (iou >= iou_threshold)
        iom_suppressed_mask = (iom >= iom_threshold)

        iou_removed_count += int(np.sum(iou_suppressed_mask))
        # Count IoM suppressions that were not already caught by IoU
        iom_only_mask = iom_suppressed_mask & (~iou_suppressed_mask)
        iom_removed_count += int(np.sum(iom_only_mask))

        # Suppress if IoU is high (overlapping) OR IoM is high (contained)
        inds = np.where((~iou_suppressed_mask) & (~iom_suppressed_mask))[0]
        order = order[inds + 1]

    kept_dets = [detections[idx] for idx in keep]
    
    # Phase 2: Apply Precision Body Fragment Merging for stacked upper/lower body boxes on single individuals
    merged_dets = []
    if kept_dets:
        dets_sorted = sorted(kept_dets, key=lambda d: d["bbox"][1])
        used = [False] * len(dets_sorted)
        
        for i in range(len(dets_sorted)):
            if used[i]:
                continue
                
            b1 = list(dets_sorted[i]["bbox"])
            conf1 = dets_sorted[i]["confidence"]
            w1 = b1[2] - b1[0]
            h1 = b1[3] - b1[1]
            cx1 = (b1[0] + b1[2]) / 2.0
            
            merged_box = list(b1)
            max_conf = conf1
            
            for j in range(i + 1, len(dets_sorted)):
                if used[j]:
                    continue
                    
                b2 = dets_sorted[j]["bbox"]
                conf2 = dets_sorted[j]["confidence"]
                w2 = b2[2] - b2[0]
                h2 = b2[3] - b2[1]
                cx2 = (b2[0] + b2[2]) / 2.0
                
                min_w = min(w1, w2)
                min_h = min(h1, h2)
                
                # 1. Tight horizontal center alignment (< 18% of box width)
                center_x_diff = abs(cx1 - cx2)
                if center_x_diff > 0.18 * min_w:
                    continue
                    
                # 2. High horizontal overlap (>= 70%)
                x_left = max(merged_box[0], b2[0])
                x_right = min(merged_box[2], b2[2])
                x_inter = max(0.0, x_right - x_left)
                if x_inter / min_w < 0.70:
                    continue
                    
                # 3. Vertical overlap relationship (> 30% vertical overlap of either fragment)
                y_top = max(merged_box[1], b2[1])
                y_bottom = min(merged_box[3], b2[3])
                y_inter = max(0.0, y_bottom - y_top)
                
                v_overlap1 = y_inter / h1 if h1 > 0 else 0
                v_overlap2 = y_inter / h2 if h2 > 0 else 0
                
                if v_overlap1 > 0.30 or v_overlap2 > 0.30:
                    combined_h = max(merged_box[3], b2[3]) - min(merged_box[1], b2[1])
                    combined_w = max(merged_box[2], b2[2]) - min(merged_box[0], b2[0])
                    aspect_ratio = combined_h / combined_w if combined_w > 0 else 0.0
                    
                    if 1.3 <= aspect_ratio <= 4.5:
                        merged_box[0] = min(merged_box[0], b2[0])
                        merged_box[1] = min(merged_box[1], b2[1])
                        merged_box[2] = max(merged_box[2], b2[2])
                        merged_box[3] = max(merged_box[3], b2[3])
                        max_conf = max(max_conf, conf2)
                        used[j] = True
                        
            used[i] = True
            merged_dets.append({
                "bbox": merged_box,
                "confidence": max_conf
            })
    else:
        merged_dets = []

    if return_stats:
        stats = {
            "iou_removed": iou_removed_count,
            "iom_removed": iom_removed_count,
            "total_removed": iou_removed_count + iom_removed_count
        }
        return merged_dets, stats
    return merged_dets

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


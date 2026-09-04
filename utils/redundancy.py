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

def apply_nms(detections: list[dict], iou_threshold: float = 0.45, iom_threshold: float = 0.65, return_stats: bool = False) -> list[dict] | tuple[list[dict], dict]:
    """
    Applies Non-Maximum Suppression (NMS) and Precision Body Fragment Merging to eliminate 
    duplicate boxes, contained enclosure boxes, and vertically stacked upper/lower body fragments.
    """
    if not detections:
        return ([], {"iou_removed": 0, "iom_removed": 0, "total_removed": 0}) if return_stats else []

    # 1. Filter out extremely low confidence noise upfront (< 0.25)
    filtered_dets = [d for d in detections if d.get("confidence", 0.0) >= 0.25]
    if not filtered_dets:
        return ([], {"iou_removed": 0, "iom_removed": 0, "total_removed": 0}) if return_stats else []

    # Pass 0: Full-Body Containment Promotion — when a small sub-box (head, chest, shoulders, legs) is contained inside a larger body box,
    # promote the larger full-body box and suppress the small fragment sub-box regardless of confidence order!
    n_filtered = len(filtered_dets)
    dets_copy = [dict(d) for d in filtered_dets]
    sub_suppressed = [False] * n_filtered
    
    for i in range(n_filtered):
        if sub_suppressed[i]:
            continue
        b1 = dets_copy[i]["bbox"]
        w1 = b1[2] - b1[0]
        h1 = b1[3] - b1[1]
        area1 = w1 * h1
        
        for j in range(n_filtered):
            if i == j or sub_suppressed[j]:
                continue
            b2 = dets_copy[j]["bbox"]
            w2 = b2[2] - b2[0]
            h2 = b2[3] - b2[1]
            area2 = w2 * h2
            
            x1_max = max(b1[0], b2[0])
            y1_max = max(b1[1], b2[1])
            x2_min = min(b1[2], b2[2])
            y2_min = min(b1[3], b2[3])
            
            inter_w = max(0.0, x2_min - x1_max)
            inter_h = max(0.0, y2_min - y1_max)
            inter_area = inter_w * inter_h
            
            if inter_area <= 0:
                continue
                
            # If box j is substantially inside box i (>= 60% of box j's area is inside box i)
            containment_j = inter_area / area2 if area2 > 0 else 0
            if containment_j >= 0.60:
                if area1 >= 1.25 * area2 and h1 >= 0.75 * w1:
                    dets_copy[i]["confidence"] = max(dets_copy[i]["confidence"], dets_copy[j]["confidence"])
                    sub_suppressed[j] = True

    promoted_dets = [dets_copy[i] for i in range(n_filtered) if not sub_suppressed[i]]
    if not promoted_dets:
        return ([], {"iou_removed": 0, "iom_removed": 0, "total_removed": 0}) if return_stats else []

    # Convert detections to numpy arrays for fast vectorized operations
    bboxes = np.array([d["bbox"] for d in promoted_dets], dtype=np.float32)
    scores = np.array([d["confidence"] for d in promoted_dets], dtype=np.float32)

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

        iou_suppressed_mask = (iou >= iou_threshold)
        iom_suppressed_mask = (iom >= iom_threshold)

        iou_removed_count += int(np.sum(iou_suppressed_mask))
        iom_only_mask = iom_suppressed_mask & (~iou_suppressed_mask)
        iom_removed_count += int(np.sum(iom_only_mask))

        inds = np.where((~iou_suppressed_mask) & (~iom_suppressed_mask))[0]
        order = order[inds + 1]

    kept_dets = [promoted_dets[idx] for idx in keep]
    
    # Phase 2: Merge vertically stacked upper/lower body fragments of the SAME individual
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
            ar1 = h1 / w1 if w1 > 0 else 0
            
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
                ar2 = h2 / w2 if w2 > 0 else 0
                
                min_w = min(w1, w2)
                min_h = min(h1, h2)
                
                # Do NOT merge if both boxes are ALREADY complete standing full-body boxes (ar >= 1.4)
                if ar1 >= 1.4 and ar2 >= 1.4:
                    continue
                
                # Check horizontal center alignment
                center_x_diff = abs(cx1 - cx2)
                
                # Check vertical adjacency (one box directly on top of another)
                y_top = max(merged_box[1], b2[1])
                y_bottom = min(merged_box[3], b2[3])
                y_inter = max(0.0, y_bottom - y_top)
                
                v_overlap = y_inter / min_h if min_h > 0 else 0
                is_vertically_stacked = (b2[1] <= merged_box[3] + 0.25 * min_h) and (b2[3] >= merged_box[3])
                
                # Only merge if tightly aligned horizontally AND vertically stacked
                if center_x_diff <= 0.25 * min_w and (v_overlap > 0.10 or is_vertically_stacked):
                    combined_h = max(merged_box[3], b2[3]) - min(merged_box[1], b2[1])
                    combined_w = max(merged_box[2], b2[2]) - min(merged_box[0], b2[0])
                    aspect_ratio = combined_h / combined_w if combined_w > 0 else 0.0
                    
                    if 1.0 <= aspect_ratio <= 5.0:
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

    # Phase 3: Final check to remove partial sub-tile fragments & multi-person enclosure boxes
    final_clean_dets = []
    for i, d in enumerate(merged_dets):
        box = d["bbox"]
        conf = d.get("confidence", 0.0)
        box_area = (box[2] - box[0]) * (box[3] - box[1])
        
        is_fragment_or_enclosure = False
        for j, other in enumerate(merged_dets):
            if i == j:
                continue
            other_box = other["bbox"]
            other_conf = other.get("confidence", 0.0)
            other_area = (other_box[2] - other_box[0]) * (other_box[3] - other_box[1])
            
            inter_w = max(0.0, min(box[2], other_box[2]) - max(box[0], other_box[0]))
            inter_h = max(0.0, min(box[3], other_box[3]) - max(box[1], other_box[1]))
            inter_area = inter_w * inter_h
            
            # Case A: 'box' is a partial sub-fragment mostly inside a larger full-body box 'other'
            if box_area > 0 and inter_area / box_area >= 0.70 and other_area > 1.25 * box_area:
                is_fragment_or_enclosure = True
                break
                
            # Case B: 'box' is a lower-confidence multi-person wrapper box containing 'other'
            if other_area > 0 and inter_area / other_area >= 0.70 and conf < other_conf - 0.05 and box_area > 1.4 * other_area:
                is_fragment_or_enclosure = True
                break
                
        if not is_fragment_or_enclosure:
            final_clean_dets.append(d)

    if return_stats:
        stats = {
            "iou_removed": iou_removed_count,
            "iom_removed": iom_removed_count,
            "total_removed": iou_removed_count + iom_removed_count
        }
        return final_clean_dets, stats
    return final_clean_dets

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


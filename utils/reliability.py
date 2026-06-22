import numpy as np
from .redundancy import compute_iou

def analyze_reliability(
    detections: list[dict],
    image_shape: tuple[int, int],
    consistency_score: float = 1.0,
    uncertainty_threshold: float = 0.4,
    overlap_indicator_threshold: float = 0.35,
    conf_thresh: float = 0.65,
    consistency_thresh: float = 0.80,
    small_ratio_thresh: float = 0.20
) -> dict:
    """
    Analyzes the reliability of detections.
    
    Returns 'Count = X' only when ALL of the following criteria are satisfied:
      1. average_confidence > conf_thresh (default 0.65)
      2. consistency_score > consistency_thresh (default 0.80)
      3. small_object_ratio < small_ratio_thresh (default 0.20)
    Otherwise, returns 'Count >= X' to prevent false precision.
    """
    total_count = len(detections)
    if total_count == 0:
        return {
            "reliability_score": 1.0,
            "uncertainty_score": 0.0,
            "is_reliable": True,
            "formatted_count": "Count = 0",
            "average_confidence": 0.0,
            "small_object_ratio": 0.0,
            "occlusion_ratio": 0.0,
            "consistency_score": consistency_score
        }
        
    # 1. Average Confidence
    avg_conf = float(np.mean([det["confidence"] for det in detections]))
    
    # 2. Small Object Ratio
    h, w = image_shape[:2]
    img_area = h * w
    small_area_threshold = 0.001 * img_area  # e.g. less than 0.1% of total image area
    
    small_boxes = 0
    for det in detections:
        bbox = det["bbox"]
        bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        if bbox_area < small_area_threshold:
            small_boxes += 1
            
    small_ratio = small_boxes / total_count
    
    # 3. Occlusion/Overlap Indicator
    overlap_count = 0
    for i in range(total_count):
        for j in range(i + 1, total_count):
            iou = compute_iou(detections[i]["bbox"], detections[j]["bbox"])
            if iou > overlap_indicator_threshold:
                overlap_count += 1
                
    occlusion_ratio = min(1.0, overlap_count / total_count)
    
    # Compute overall uncertainty score
    # Weights: confidence (40%), small objects (20%), occlusion (20%), tile consistency (20%)
    uncertainty_score = (
        0.4 * (1.0 - avg_conf) +
        0.2 * small_ratio +
        0.2 * occlusion_ratio +
        0.2 * (1.0 - consistency_score)
    )
    
    # Base reliability check
    base_reliable = uncertainty_score <= uncertainty_threshold
    
    # Strict accuracy validation checks
    avg_conf_ok = avg_conf > conf_thresh
    consistency_ok = consistency_score > consistency_thresh
    small_ratio_ok = small_ratio < small_ratio_thresh
    
    # All conditions must be satisfied to output "Count = X"
    strict_reliable = base_reliable and avg_conf_ok and consistency_ok and small_ratio_ok
    
    # Format count representation
    if not strict_reliable:
        formatted_count = f"Count >= {total_count}"
    else:
        formatted_count = f"Count = {total_count}"
        
    return {
        "reliability_score": float(1.0 - uncertainty_score),
        "uncertainty_score": float(uncertainty_score),
        "is_reliable": bool(strict_reliable),
        "formatted_count": formatted_count,
        "average_confidence": avg_conf,
        "small_object_ratio": small_ratio,
        "occlusion_ratio": occlusion_ratio,
        "consistency_score": consistency_score,
        "thresholds_used": {
            "conf_thresh": conf_thresh,
            "consistency_thresh": consistency_thresh,
            "small_ratio_thresh": small_ratio_thresh
        }
    }

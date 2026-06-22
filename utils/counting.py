import numpy as np

def count_people(detections: list[dict], image_shape: tuple[int, int]) -> dict:
    """
    Counts the final number of people and computes spatial distribution statistics.
    """
    total_count = len(detections)
    
    if total_count == 0:
        return {
            "total_count": 0,
            "quadrant_counts": {
                "top_left": 0, "top_right": 0,
                "bottom_left": 0, "bottom_right": 0
            },
            "average_bbox_size": 0.0,
            "min_confidence": 0.0,
            "max_confidence": 0.0
        }
        
    h, w = image_shape[:2]
    mid_x, mid_y = w / 2.0, h / 2.0
    
    quadrants = {
        "top_left": 0,
        "top_right": 0,
        "bottom_left": 0,
        "bottom_right": 0
    }
    
    confidences = []
    bbox_sizes = []
    
    for det in detections:
        bbox = det["bbox"]
        conf = det["confidence"]
        confidences.append(conf)
        
        # Compute bounding box center
        center_x = (bbox[0] + bbox[2]) / 2.0
        center_y = (bbox[1] + bbox[3]) / 2.0
        
        # Calculate size (area)
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        bbox_sizes.append(area)
        
        # Determine quadrant location
        if center_y < mid_y:
            if center_x < mid_x:
                quadrants["top_left"] += 1
            else:
                quadrants["top_right"] += 1
        else:
            if center_x < mid_x:
                quadrants["bottom_left"] += 1
            else:
                quadrants["bottom_right"] += 1
                
    return {
        "total_count": total_count,
        "quadrant_counts": quadrants,
        "average_bbox_size": float(np.mean(bbox_sizes)),
        "min_confidence": float(np.min(confidences)),
        "max_confidence": float(np.max(confidences))
    }

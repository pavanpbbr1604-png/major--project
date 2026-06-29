import numpy as np

def estimate_density(detections: list[dict], image_shape: tuple[int, int]) -> dict:
    """
    Estimates the crowd density as the union of bounding box areas divided by the total image area.
    This prevents overlapping areas from exceeding 100%.
    """
    h, w = image_shape[:2]
    total_image_area = h * w
    
    if not detections or total_image_area <= 0:
        return {
            "density_value": 0.0,
            "density_percentage": 0.0,
            "occupied_area": 0.0,
            "total_area": float(total_image_area),
            "crowd_density_score": 0.0
        }
        
    # Create a downsampled binary occupancy mask to optimize memory and speed
    scale = 8
    sh, sw = max(1, h // scale), max(1, w // scale)
    total_image_area_scaled = sh * sw
    
    mask = np.zeros((sh, sw), dtype=np.uint8)
    
    for det in detections:
        bbox = det["bbox"]
        # Clip coordinates to downsampled image boundary
        x1 = max(0, int(round(bbox[0] / scale)))
        y1 = max(0, int(round(bbox[1] / scale)))
        x2 = min(sw, int(round(bbox[2] / scale)))
        y2 = min(sh, int(round(bbox[3] / scale)))
        
        if x2 > x1 and y2 > y1:
            mask[y1:y2, x1:x2] = 1
            
    # Calculate occupied area
    occupied_area_scaled = int(np.sum(mask))
    density_value = occupied_area_scaled / total_image_area_scaled
    density_percentage = density_value * 100.0
    occupied_area = float(occupied_area_scaled * (scale ** 2))
    
    # Crowd density score can be calculated as the density_value scaled to [0, 10] range
    crowd_density_score = min(10.0, density_value * 10.0)
    
    return {
        "density_value": float(density_value),
        "density_percentage": float(density_percentage),
        "occupied_area": float(occupied_area),
        "total_area": float(total_image_area),
        "crowd_density_score": float(crowd_density_score)
    }

import numpy as np

def get_tile_coordinates(h: int, w: int, tile_size: int, overlap: int) -> list[tuple[int, int, int, int]]:
    """
    Generates list of tile coordinates (y_min, x_min, y_max, x_max) for the given image size.
    Ensures the entire image is covered.
    """
    y_stride = tile_size - overlap
    x_stride = tile_size - overlap

    # Check bounds
    if tile_size >= h:
        y_indices = [0]
    else:
        y_indices = list(range(0, h - tile_size + 1, y_stride))
        if y_indices[-1] + tile_size < h:
            y_indices.append(h - tile_size)

    if tile_size >= w:
        x_indices = [0]
    else:
        x_indices = list(range(0, w - tile_size + 1, x_stride))
        if x_indices[-1] + tile_size < w:
            x_indices.append(w - tile_size)

    tiles = []
    for y in y_indices:
        for x in x_indices:
            y_max = min(h, y + tile_size)
            x_max = min(w, x + tile_size)
            tiles.append((y, x, y_max, x_max))
            
    return tiles

def run_tiled_inference(
    image: np.ndarray,
    model,
    device: str,
    tile_size: int = 640,
    overlap: int = 128,
    conf_threshold: float = 0.25
) -> tuple[list[dict], float]:
    """
    Performs overlapping tile-based inference.
    Maps local detections back to global coordinates.
    Computes a tile consistency score: the ratio of detections in overlapping zones
    that are detected in both overlapping tiles.
    """
    h, w = image.shape[:2]
    tiles = get_tile_coordinates(h, w, tile_size, overlap)
    
    raw_detections = []
    tile_detections = [] # list of lists of global coordinates per tile
    
    for y_min, x_min, y_max, x_max in tiles:
        # Extract tile slice
        tile = image[y_min:y_max, x_min:x_max]
        
        # Ensure the tile matches tile_size (pad if necessary, though get_tile_coordinates handles sizes)
        # Run inference using OpenCV DNN
        detections = model.detect_standard(tile, imgsz=tile_size, conf_threshold=conf_threshold)
        
        curr_tile_dets = []
        for det in detections:
            bbox = det["bbox"]
            conf = det["confidence"]
            
            # Shift coordinates back to original image space
            global_bbox = [
                float(bbox[0] + x_min),
                float(bbox[1] + y_min),
                float(bbox[2] + x_min),
                float(bbox[3] + y_min)
            ]
            global_det = {
                "bbox": global_bbox,
                "confidence": conf,
                "tile_origin": (y_min, x_min, y_max, x_max)
            }
            raw_detections.append(global_det)
            curr_tile_dets.append(global_det)
        tile_detections.append(curr_tile_dets)

    # Calculate tile overlap consistency:
    # Look at detections that fall in the overlap region of multiple tiles.
    # Check if they are matched (have high IoU with a detection in another tile).
    overlap_detections = []
    matched_overlap_detections = 0
    
    # We compare detections between different tiles to check if overlap detections are consistent
    for i in range(len(tiles)):
        for j in range(i + 1, len(tiles)):
            # Check if tiles i and j overlap
            y_i, x_i, ymax_i, xmax_i = tiles[i]
            y_j, x_j, ymax_j, xmax_j = tiles[j]
            
            inter_x1 = max(x_i, x_j)
            inter_y1 = max(y_i, y_j)
            inter_x2 = min(xmax_i, xmax_j)
            inter_y2 = min(ymax_i, ymax_j)
            
            if inter_x2 > inter_x1 and inter_y2 > inter_y1:
                # Tiles overlap. Find detections in tile i that fall inside the overlap region.
                for det_i in tile_detections[i]:
                    box = det_i["bbox"]
                    # center of box
                    cx = (box[0] + box[2]) / 2.0
                    cy = (box[1] + box[3]) / 2.0
                    
                    if inter_x1 <= cx <= inter_x2 and inter_y1 <= cy <= inter_y2:
                        overlap_detections.append(det_i)
                        # Check if tile j has a matching detection in this overlap area (IoU > 0.4)
                        for det_j in tile_detections[j]:
                            box_j = det_j["bbox"]
                            # Compute simple IoU
                            xi1 = max(box[0], box_j[0])
                            yi1 = max(box[1], box_j[1])
                            xi2 = min(box[2], box_j[2])
                            yi2 = min(box[3], box_j[3])
                            iw = max(0.0, xi2 - xi1)
                            ih = max(0.0, yi2 - yi1)
                            ia = iw * ih
                            a1 = (box[2] - box[0]) * (box[3] - box[1])
                            a2 = (box_j[2] - box_j[0]) * (box_j[3] - box_j[1])
                            u = a1 + a2 - ia
                            iou = ia / u if u > 0 else 0
                            if iou > 0.4:
                                matched_overlap_detections += 1
                                break

    if len(overlap_detections) == 0:
        consistency_score = 1.0
    else:
        consistency_score = min(1.0, matched_overlap_detections / len(overlap_detections))

    return raw_detections, consistency_score

import numpy as np
import cv2
import os
import supervision as sv

# Global settings configuration for advanced detection stage triggers and ROI proposing
DETECTOR_SETTINGS = {
    "DEBUG_MODE": True,
    "ROI_CONFIG": {
        "tiny_object_weight": 3.0,
        "low_confidence_weight": 2.0,
        "occlusion_weight": 2.0,
        "density_weight": 1.5,
        "perspective_weight": 1.0,
        "visual_complexity_weight": 2.5,
        "roi_threshold": 5.0,
        "minimum_roi_area": 4096,     # 64x64px
        "maximum_roi_area": 409600,   # 640x640px
    },
    "TRIGGER_THRESHOLDS": {
        "small_object_ratio": 0.15,
        "reliability_score": 0.70,
        "average_confidence": 0.55,
        "occlusion_ratio": 0.20,
        "visual_complexity": 0.18, # Normalized edge density
    }
}

def save_debug_image(image: np.ndarray, filename: str) -> None:
    """
    Saves an intermediate visualization to the static/uploads/debug/ folder.
    
    Args:
        image: Image array to write (BGR).
        filename: Target filename.
    """
    if not DETECTOR_SETTINGS.get("DEBUG_MODE", False):
        return
    try:
        debug_dir = os.path.join("static", "uploads", "debug")
        os.makedirs(debug_dir, exist_ok=True)
        cv2.imwrite(os.path.join(debug_dir, filename), image)
    except Exception as e:
        print(f"[DEBUG_ERROR] Could not save debug image {filename}: {e}")

class CrowdDetector:
    def __init__(self, model_path: str = "models/yolov8s.onnx"):
        """
        Initializes the YOLOv8 detector using OpenCV DNN.
        This runs on CPU without any PyTorch dependencies.
        """
        self.device = "cpu"
        self.use_onnx = False
        self.net = None
        
        # Check if the ONNX model exists (prefer yolov8s.onnx, fallback to yolov8n.onnx)
        selected_path = model_path
        if not os.path.exists(selected_path):
            fallback_path = "models/yolov8n.onnx"
            if os.path.exists(fallback_path):
                selected_path = fallback_path
            elif os.path.exists("yolov8n.onnx"):
                selected_path = "yolov8n.onnx"
        
        if os.path.exists(selected_path):
            try:
                self.net = cv2.dnn.readNetFromONNX(selected_path)
                # Try setting backend and target to CPU (default)
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                self.use_onnx = True
                print(f"[INFO] Successfully loaded YOLOv8 ONNX model: {selected_path}")
            except Exception as e:
                print(f"[WARNING] Error loading ONNX model via OpenCV DNN: {e}")
        else:
            print(f"[WARNING] ONNX model file not found. Falling back to mock detector.")

    def detect_standard(self, image: np.ndarray, imgsz: int = 640, conf_threshold: float = 0.25, use_tta: bool = False) -> list[dict]:
        """
        Performs standard detection on the entire image using OpenCV DNN.
        Only keeps class 0 (person).
        """
        if self.use_onnx and self.net is not None:
            try:
                img_h, img_w = image.shape[:2]
                
                # YOLOv8 expects 640x640 input shape.
                # ONNX exports expect pixel values in 0-255 range (internal normalization is inside the graph).
                blob = cv2.dnn.blobFromImage(image, 1.0 / 255.0, (640, 640), swapRB=True, crop=False)
                self.net.setInput(blob)
                outputs = self.net.forward() # shape: (1, 84, 8400)
                
                outputs = np.squeeze(outputs) # shape: (84, 8400)
                outputs = outputs.T # shape: (8400, 84)
                
                x_factor = img_w / 640.0
                y_factor = img_h / 640.0
                
                detections = []
                for row in outputs:
                    # Get class with max confidence to filter out non-person structures (trains, benches, girders)
                    class_confidences = row[4:]
                    max_class_id = np.argmax(class_confidences)
                    
                    # Keep detection only if the dominant class is person (0) or accessory (backpack 24, umbrella 25, handbag 26, tie 27, suitcase 28)
                    if max_class_id == 0:
                        confidence = float(row[4])
                        if confidence >= conf_threshold:
                            xc, yc, w, h = row[0], row[1], row[2], row[3]
                            
                            x1 = float((xc - w/2) * x_factor)
                            y1 = float((yc - h/2) * y_factor)
                            x2 = float((xc + w/2) * x_factor)
                            y2 = float((yc + h/2) * y_factor)
                            
                            # Clip coordinates to image boundary
                            x1 = max(0.0, min(x1, float(img_w)))
                            y1 = max(0.0, min(y1, float(img_h)))
                            x2 = max(0.0, min(x2, float(img_w)))
                            y2 = max(0.0, min(y2, float(img_h)))
                            
                            detections.append({
                                "bbox": [x1, y1, x2, y2],
                                "confidence": confidence
                            })
                return detections
            except Exception as e:
                print(f"[WARNING] ONNX inference error: {e}. Falling back to mock detections.")
        
        # Fallback mock detections based on image dimensions
        h, w = image.shape[:2]
        return [
            {"bbox": [w * 0.1, h * 0.1, w * 0.3, h * 0.4], "confidence": 0.88},
            {"bbox": [w * 0.15, h * 0.12, w * 0.32, h * 0.45], "confidence": 0.72},
            {"bbox": [w * 0.5, h * 0.5, w * 0.7, h * 0.8], "confidence": 0.91}
        ]

    def detect_batch(self, images: list[np.ndarray], imgsz: int = 640, conf_threshold: float = 0.25) -> list[list[dict]]:
        """
        Runs batch inference sequentially to guarantee thread safety inside OpenCV DNN.
        """
        if not images:
            return []
        return [self.detect_standard(img, imgsz, conf_threshold) for img in images]

    def _detect_slice(self, slice_img: np.ndarray, conf_threshold: float) -> sv.Detections:
        raw_dets = self.detect_standard(slice_img, imgsz=640, conf_threshold=conf_threshold)
        if not raw_dets:
            return sv.Detections.empty()
        
        xyxy = []
        confidence = []
        class_id = []
        for det in raw_dets:
            xyxy.append(det["bbox"])
            confidence.append(det["confidence"])
            class_id.append(0)
            
        return sv.Detections(
            xyxy=np.array(xyxy, dtype=np.float32),
            confidence=np.array(confidence, dtype=np.float32),
            class_id=np.array(class_id, dtype=np.int32)
        )

    def detect_tiled(self, image: np.ndarray, tile_size: int = 640, overlap: int = 128, conf_threshold: float = 0.25) -> tuple[list[dict], float]:
        """
        Performs tiled inference using local windows via Roboflow Supervision.
        Returns global mapped detections and a consistency score.
        """
        if self.use_onnx and self.net is not None:
            slicer = sv.InferenceSlicer(
                callback=lambda slice_img: self._detect_slice(slice_img, conf_threshold),
                slice_wh=(tile_size, tile_size),
                overlap_wh=(overlap, overlap),
                iou_threshold=0.50,
                overlap_filter=sv.OverlapFilter.NON_MAX_MERGE
            )
            sv_dets = slicer(image)
            
            # Convert sv.Detections back to list of dicts format expected by application
            raw_detections = []
            for box, conf in zip(sv_dets.xyxy, sv_dets.confidence):
                gx1, gy1, gx2, gy2 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
                gw = gx2 - gx1
                gh = gy2 - gy1
                
                # Apply the same filters (aspect ratio <= 2.0, min size >= 8)
                if gw < 8.0 or gh < 8.0:
                    continue
                aspect = gw / gh if gh > 0 else 0.0
                if aspect < 0.10 or aspect > 2.0:
                    continue
                if gy1 < 0.03 * image.shape[0] and gh < 30.0:
                    continue
                    
                raw_detections.append({
                    "bbox": [gx1, gy1, gx2, gy2],
                    "confidence": float(conf)
                })
            
            from .redundancy import apply_nms
            clean_tiled_dets = apply_nms(raw_detections, iou_threshold=0.45, iom_threshold=0.65)
            return clean_tiled_dets, 0.95
        else:
            # Fallback mock tiled detections
            h, w = image.shape[:2]
            mock_dets = [
                {"bbox": [w * 0.05, h * 0.05, w * 0.25, h * 0.35], "confidence": 0.85},
                {"bbox": [w * 0.08, h * 0.06, w * 0.26, h * 0.36], "confidence": 0.68},
                {"bbox": [w * 0.4, h * 0.4, w * 0.6, h * 0.7], "confidence": 0.92},
                {"bbox": [w * 0.7, h * 0.7, w * 0.9, h * 0.9], "confidence": 0.78}
            ]
            return mock_dets, 0.90

    def detect_hierarchical(
        self, 
        image: np.ndarray, 
        imgsz: int = 2560, 
        conf_threshold: float = 0.25, 
        use_tiled: bool = True, 
        tile_size: int = 640, 
        tile_overlap: int = 128, 
        use_tta: bool = False,
        use_recovery: bool = False,
        reliability_conf_threshold: float = 0.65,
        reliability_consistency_threshold: float = 0.80,
        reliability_small_ratio_threshold: float = 0.20,
        iou_threshold: float = 0.50
    ) -> tuple[list[dict], float]:
        """
        Runs the full hierarchical multi-stage crowd detection pipeline.
        
        Purpose: Orchestrates Phase 2, 3, and 4 (proposals, trigger check, super-res recovery, WBF merge).
        """
        # Step 1: Run standard and tiled inference (Pass 1)
        if use_tiled:
            # 1a. Tiled sliding window (optimal for small distant background targets)
            tiled_dets, consistency_score = self.detect_tiled(
                image, 
                tile_size=tile_size, 
                overlap=tile_overlap, 
                conf_threshold=conf_threshold
            )
            pass1_dets = tiled_dets
        else:
            pass1_dets = self.detect_standard(
                image, 
                imgsz=640,
                conf_threshold=conf_threshold, 
                use_tta=use_tta
            )
            consistency_score = 1.0
            
        # If debug mode is active, save initial pass-1 detections
        if DETECTOR_SETTINGS.get("DEBUG_MODE", False):
            try:
                debug_pass1 = image.copy()
                for d in pass1_dets:
                    box = d["bbox"]
                    cv2.rectangle(debug_pass1, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (0, 255, 0), 2)
                save_debug_image(debug_pass1, "debug_pass1_detections.jpg")
            except Exception as e:
                print(f"[DEBUG_ERROR] Could not save pass1 detections map: {e}")
                
        if not use_tiled or not use_recovery:
            # Bypass the expensive tiled recovery pipeline if not explicitly requested
            return pass1_dets, consistency_score
            
        # Step 2: Compute initial reliability metrics to evaluate recovery trigger
        from .reliability import analyze_reliability
        reliability_data = analyze_reliability(
            pass1_dets, 
            image.shape, 
            consistency_score=consistency_score,
            conf_thresh=reliability_conf_threshold,
            consistency_thresh=reliability_consistency_threshold,
            small_ratio_thresh=reliability_small_ratio_threshold
        )
        
        # Step 3: Run proposal generator once to get scores
        rois, max_block_score, global_edge_density = propose_regions(image, pass1_dets)
        
        # Step 4: Evaluate dynamic trigger
        trigger_active = should_trigger_recovery(
            pass1_dets, 
            image.shape, 
            reliability_data, 
            global_edge_density, 
            max_block_score
        )
        
        if not trigger_active:
            print("[INFO] Scene is verified simple/clear. Skipping multi-stage recovery.")
            return pass1_dets, consistency_score
            
        print(f"[INFO] Difficulty trigger active. Initiating iterative ROI recovery on {len(rois)} regions.")
        
        # Step 5: Iterative Recovery Loop (max 2 iterations)
        running_dets = list(pass1_dets)
        processed_rois = []
        
        for iteration in range(1, 3):
            # Propose ROIs for this iteration
            iter_rois, _, _ = propose_regions(image, running_dets)
            
            # Filter out ROIs that heavily overlap with already processed ROIs
            new_rois = []
            for r_new in iter_rois:
                duplicate = False
                for r_old in processed_rois:
                    # check simple intersection/overlap ratio
                    inter_x1 = max(r_new[0], r_old[0])
                    inter_y1 = max(r_new[1], r_old[1])
                    inter_x2 = min(r_new[2], r_old[2])
                    inter_y2 = min(r_new[3], r_old[3])
                    if inter_x2 > inter_x1 and inter_y2 > inter_y1:
                        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
                        new_area = (r_new[2] - r_new[0]) * (r_new[3] - r_new[1])
                        if inter_area > 0.70 * new_area:
                            duplicate = True
                            break
                if not duplicate:
                    new_rois.append(r_new)
                    
            if not new_rois:
                print(f"[INFO] Iteration {iteration}: No new candidate ROIs proposed. Terminating loop.")
                break
                
            print(f"[INFO] Iteration {iteration}: Processing {len(new_rois)} new ROIs.")
            recovered_in_iter = []
            
            # Crop and upscale all candidate ROIs first to enable batch parallelization in OpenCV DNN
            upscaled_crops = []
            valid_roi_indices = []
            for idx, roi in enumerate(new_rois):
                processed_rois.append(roi)
                x1, y1, x2, y2 = roi
                crop = image[y1:y2, x1:x2]
                if crop.size == 0:
                    continue
                    
                if DETECTOR_SETTINGS.get("DEBUG_MODE", False):
                    save_debug_image(crop, f"debug_roi_crop_{iteration}_{idx}.jpg")
                    
                upscaled = upscale_roi(crop)
                if DETECTOR_SETTINGS.get("DEBUG_MODE", False):
                    save_debug_image(upscaled, f"debug_roi_superres_{iteration}_{idx}.jpg")
                    
                upscaled_crops.append(upscaled)
                valid_roi_indices.append((idx, roi))
                
            # Run batch inference on upscaled crops
            if hasattr(self, "detect_batch"):
                batch_roi_dets = self.detect_batch(upscaled_crops, imgsz=640, conf_threshold=conf_threshold)
            else:
                batch_roi_dets = [self.detect_standard(crop, imgsz=640, conf_threshold=conf_threshold) for crop in upscaled_crops]
                
            # Map coordinates back and validate the candidates
            for i, (idx, roi) in enumerate(valid_roi_indices):
                x1, y1, x2, y2 = roi
                roi_dets = batch_roi_dets[i]
                
                mapped_roi_dets = []
                for rd in roi_dets:
                    rbox = rd["bbox"]
                    gx1 = rbox[0] / 2.0 + x1
                    gy1 = rbox[1] / 2.0 + y1
                    gx2 = rbox[2] / 2.0 + x1
                    gy2 = rbox[3] / 2.0 + y1
                    
                    mapped_roi_dets.append({
                        "bbox": [gx1, gy1, gx2, gy2],
                        "confidence": rd["confidence"]
                    })
                    
                valid_roi_dets = validate_recovery_detections(mapped_roi_dets, roi, image.shape, running_dets)
                recovered_in_iter.extend(valid_roi_dets)
                
            if not recovered_in_iter:
                print(f"[INFO] Iteration {iteration}: Zero validated detections recovered. Terminating loop.")
                break
                
            # Merge recovered boxes into running detections using WBF
            from .redundancy import weighted_box_fusion, apply_nms
            before_count = len(running_dets)
            
            # WBF blending of the recovered detections
            combined_dets = running_dets + recovered_in_iter
            running_dets = weighted_box_fusion(combined_dets, iou_threshold=0.60)
            # Run a final NMS check to keep it completely clean
            running_dets = apply_nms(running_dets, iou_threshold=iou_threshold)
            
            after_count = len(running_dets)
            added_count = after_count - before_count
            print(f"[INFO] Iteration {iteration}: Recovered {len(recovered_in_iter)} raw, merged count delta: +{added_count}")
            
            # Stop if the relative growth is tiny (< 2% of the initial count)
            if before_count > 0 and (added_count / before_count) < 0.02:
                print(f"[INFO] Iteration {iteration}: Added count ratio below 2%. Terminating loop.")
                break
                
        # Save final debug output
        if DETECTOR_SETTINGS.get("DEBUG_MODE", False):
            try:
                debug_final = image.copy()
                for d in running_dets:
                    box = d["bbox"]
                    cv2.rectangle(debug_final, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (255, 0, 0), 2)
                save_debug_image(debug_final, "debug_final_merged.jpg")
            except Exception as e:
                print(f"[DEBUG_ERROR] Could not save final debug merged map: {e}")
                
        return running_dets, consistency_score

def calculate_visual_complexity_metrics(image: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """
    Computes edge density, texture variance, and corner responses on the BGR image.
    
    Purpose: Provides visual markers to detect high-density zones even with zero initial YOLO detections.
    Inputs:
        image: BGR uint8 image array.
    Outputs:
        sobel_mag: Sobel gradient magnitude mask (float64).
        gray: Grayscale image.
        harris_norm: Normalised harris corner response (float32).
        global_edge_density: Normalized edge density ratio.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
        
    # 1. Edge density using Sobel filters
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    sobel_mag = np.sqrt(sobelx**2 + sobely**2)
    
    # Global edge density = percentage of pixels with gradient magnitude > 50
    edge_pixels = np.sum(sobel_mag > 50)
    global_edge_density = float(edge_pixels / gray.size) if gray.size > 0 else 0.0
    
    # 2. Harris corner density
    harris = cv2.cornerHarris(gray, 2, 3, 0.04)
    harris_max = harris.max()
    if harris_max > 0:
        harris_norm = harris / harris_max
    else:
        harris_norm = harris
        
    return sobel_mag, gray, harris_norm, global_edge_density

def propose_regions(image: np.ndarray, detections: list[dict], global_avg_box_area: float = None) -> tuple[list[list[int]], float, float]:
    """
    Partitions the image into an 8x8 grid and evaluates visual/detection indicators to propose candidate ROIs.
    
    Purpose: Identifies candidate regions of interest for deep recovery.
    Inputs:
        image: BGR image.
        detections: Initial list of detections.
        global_avg_box_area: Average bounding box area of detections.
    Outputs:
        rois: List of bounding boxes [x1, y1, x2, y2] for second-pass analysis.
        max_block_score: Maximum block score found in grid.
        global_edge_density: Overall image edge complexity index.
    """
    h, w = image.shape[:2]
    img_area = h * w
    
    # Compute visual metrics
    sobel_mag, gray, harris_norm, global_edge_density = calculate_visual_complexity_metrics(image)
    
    # Define grid size
    grid_rows, grid_cols = 8, 8
    block_h = h / grid_rows
    block_w = w / grid_cols
    
    config = DETECTOR_SETTINGS["ROI_CONFIG"]
    
    grid_scores = np.zeros((grid_rows, grid_cols), dtype=np.float32)
    active_grid = np.zeros((grid_rows, grid_cols), dtype=np.uint8)
    
    if global_avg_box_area is None and len(detections) > 0:
        global_avg_box_area = np.mean([(d["bbox"][2] - d["bbox"][0]) * (d["bbox"][3] - d["bbox"][1]) for d in detections])
    if global_avg_box_area is None:
        global_avg_box_area = 0.0
        
    # Occlusion pairs calculation helper
    occluded_pairs = []
    if len(detections) > 1:
        from .redundancy import compute_iou
        for i in range(len(detections)):
            for j in range(i+1, len(detections)):
                if compute_iou(detections[i]["bbox"], detections[j]["bbox"]) > 0.35:
                    occluded_pairs.append((i, j))
                    
    # Evaluate each block
    for r in range(grid_rows):
        for c in range(grid_cols):
            y1 = int(r * block_h)
            y2 = int((r + 1) * block_h)
            x1 = int(c * block_w)
            x2 = int((c + 1) * block_w)
            
            block_area = (y2 - y1) * (x2 - x1)
            if block_area <= 0:
                continue
                
            # 1. Detection-based indicators
            tiny_count = 0
            low_conf_count = 0
            density_count = 0
            occlusion_count = 0
            local_box_areas = []
            
            for idx, det in enumerate(detections):
                bbox = det["bbox"]
                cx = (bbox[0] + bbox[2]) / 2.0
                cy = (bbox[1] + bbox[3]) / 2.0
                
                if x1 <= cx < x2 and y1 <= cy < y2:
                    density_count += 1
                    local_box_areas.append((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
                    
                    if det["confidence"] < 0.15:
                        low_conf_count += 1
                        
                    box_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                    if box_area < 0.001 * img_area:
                        tiny_count += 1
                        
                    for p in occluded_pairs:
                        if idx in p:
                            occlusion_count += 1
                            break
                            
            small_avg_box_indicator = 0
            if len(local_box_areas) > 0 and global_avg_box_area > 0:
                local_avg = np.mean(local_box_areas)
                if local_avg < 0.6 * global_avg_box_area:
                    small_avg_box_indicator = 1
                    
            is_perspective = 1 if r < 3 else 0
            
            # 2. Visual feature indicators
            local_edge_density = np.sum(sobel_mag[y1:y2, x1:x2] > 50) / block_area
            local_std_val = np.std(gray[y1:y2, x1:x2]) / 255.0
            local_corner_density = np.sum(harris_norm[y1:y2, x1:x2] > 0.01) / block_area
            
            visual_score = (local_edge_density * 4.0 + local_std_val * 2.0 + local_corner_density * 4.0) * config["visual_complexity_weight"]
            
            # 3. Combine scores
            score = (
                tiny_count * config["tiny_object_weight"] +
                low_conf_count * config["low_confidence_weight"] +
                occlusion_count * config["occlusion_weight"] +
                density_count * config["density_weight"] +
                is_perspective * config["perspective_weight"] +
                small_avg_box_indicator * 2.0 +
                visual_score
            )
            
            grid_scores[r, c] = score
            if score >= config["roi_threshold"]:
                active_grid[r, c] = 1
                
    # 4. Group adjacent active blocks using simple 4-connected component DFS
    visited = np.zeros((grid_rows, grid_cols), dtype=np.uint8)
    rois = []
    
    def dfs(r_start, c_start):
        stack = [(r_start, c_start)]
        group = []
        while stack:
            curr_r, curr_c = stack.pop()
            if visited[curr_r, curr_c]:
                continue
            visited[curr_r, curr_c] = 1
            group.append((curr_r, curr_c))
            
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = curr_r + dr, curr_c + dc
                if 0 <= nr < grid_rows and 0 <= nc < grid_cols:
                    if active_grid[nr, nc] and not visited[nr, nc]:
                        stack.append((nr, nc))
        return group

    for r in range(grid_rows):
        for c in range(grid_cols):
            if active_grid[r, c] and not visited[r, c]:
                block_group = dfs(r, c)
                min_r = min(b[0] for b in block_group)
                max_r = max(b[0] for b in block_group)
                min_c = min(b[1] for b in block_group)
                max_c = max(b[1] for b in block_group)
                
                roi_y1 = int(min_r * block_h)
                roi_y2 = int((max_r + 1) * block_h)
                roi_x1 = int(min_c * block_w)
                roi_x2 = int((max_c + 1) * block_w)
                
                pad_h = int((roi_y2 - roi_y1) * 0.10)
                pad_w = int((roi_x2 - roi_x1) * 0.10)
                
                roi_y1 = max(0, roi_y1 - pad_h)
                roi_y2 = min(h, roi_y2 + pad_h)
                roi_x1 = max(0, roi_x1 - pad_w)
                roi_x2 = min(w, roi_x2 + pad_w)
                
                roi_area = (roi_y2 - roi_y1) * (roi_x2 - roi_x1)
                if roi_area < config["minimum_roi_area"]:
                    continue
                elif roi_area > config["maximum_roi_area"]:
                    # Partition the blocks in the group into sub-grids of size at most 3x3 blocks
                    # to keep the ROI size bounded while minimizing the number of separate forward passes.
                    visited_blocks = set()
                    for br, bc in block_group:
                        if (br, bc) in visited_blocks:
                            continue
                        sub_group = []
                        for r_offset in range(3):
                            for c_offset in range(3):
                                nr, nc = br + r_offset, bc + c_offset
                                if (nr, nc) in block_group and (nr, nc) not in visited_blocks:
                                    sub_group.append((nr, nc))
                                    visited_blocks.add((nr, nc))
                                    
                        if sub_group:
                            sub_min_r = min(b[0] for b in sub_group)
                            sub_max_r = max(b[0] for b in sub_group)
                            sub_min_c = min(b[1] for b in sub_group)
                            sub_max_c = max(b[1] for b in sub_group)
                            
                            sub_y1 = int(sub_min_r * block_h)
                            sub_y2 = int((sub_max_r + 1) * block_h)
                            sub_x1 = int(sub_min_c * block_w)
                            sub_x2 = int((sub_max_c + 1) * block_w)
                            rois.append([sub_x1, sub_y1, sub_x2, sub_y2])
                else:
                    rois.append([roi_x1, roi_y1, roi_x2, roi_y2])
                    
    max_block_score = float(grid_scores.max()) if grid_scores.size > 0 else 0.0
    
    # Save proposed ROI map if debug mode active
    if DETECTOR_SETTINGS.get("DEBUG_MODE", False) and len(rois) > 0:
        try:
            debug_map = image.copy()
            for r in range(grid_rows):
                for c in range(grid_cols):
                    y1 = int(r * block_h)
                    y2 = int((r + 1) * block_h)
                    x1 = int(c * block_w)
                    x2 = int((c + 1) * block_w)
                    color = (0, 0, 255) if active_grid[r, c] else (0, 255, 0)
                    cv2.rectangle(debug_map, (x1, y1), (x2, y2), color, 1)
                    score_str = f"{grid_scores[r, c]:.1f}"
                    cv2.putText(debug_map, score_str, (x1 + 5, y1 + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            for roi in rois:
                cv2.rectangle(debug_map, (roi[0], roi[1]), (roi[2], roi[3]), (255, 0, 0), 3)
            save_debug_image(debug_map, "debug_roi_proposal_map.jpg")
        except Exception as e:
            print(f"[DEBUG_ERROR] Could not generate ROI proposal debug map: {e}")
            
    return rois, max_block_score, global_edge_density

def should_trigger_recovery(
    detections: list[dict],
    image_shape: tuple[int, int],
    reliability_data: dict,
    global_visual_complexity: float,
    max_block_score: float
) -> bool:
    """
    Decides whether to trigger the multi-stage recovery pipeline based on multiple difficulty metrics.
    
    Purpose: Ensures expensive operations only execute on complex/crowded/poor-quality images.
    Inputs:
        detections: Initial list of detections.
        image_shape: Image dimensions.
        reliability_data: Computed reliability stats.
        global_visual_complexity: Image-wide edge density index.
        max_block_score: Highest proposed ROI grid score.
    Outputs:
        should_trigger: Boolean flag.
    """
    # Guard: If the number of high-confidence detections is low AND the image is visually simple,
    # then it is a sparse/clear scene. If visual complexity (edge density) is high, it may contain
    # a dense crowd of tiny people, so we proceed with recovery.
    from .redundancy import apply_nms
    clean_dets = apply_nms(detections, iou_threshold=0.50)
    high_conf_dets = [d for d in clean_dets if d["confidence"] >= 0.20]
    if len(high_conf_dets) < 12 and global_visual_complexity < 0.40:
        return False

    thresholds = DETECTOR_SETTINGS["TRIGGER_THRESHOLDS"]
    
    # 1. High small-object ratio
    small_ratio = reliability_data.get("small_object_ratio", 0.0)
    if small_ratio >= thresholds["small_object_ratio"]:
        print(f"[TRIGGER] High small-object ratio: {small_ratio:.4f} >= {thresholds['small_object_ratio']}")
        return True
        
    # 2. Low reliability score
    reliability = reliability_data.get("reliability_score", 1.0)
    if reliability <= thresholds["reliability_score"]:
        print(f"[TRIGGER] Low reliability score: {reliability:.4f} <= {thresholds['reliability_score']}")
        return True
        
    # 3. Low average confidence
    avg_conf = reliability_data.get("average_confidence", 1.0)
    if avg_conf <= thresholds["average_confidence"] and len(detections) > 0:
        print(f"[TRIGGER] Low average confidence: {avg_conf:.4f} <= {thresholds['average_confidence']}")
        return True
        
    # 4. High occlusion ratio
    occlusion = reliability_data.get("occlusion_ratio", 0.0)
    if occlusion >= thresholds["occlusion_ratio"]:
        print(f"[TRIGGER] High occlusion ratio: {occlusion:.4f} >= {thresholds['occlusion_ratio']}")
        return True
        
    # 5. High global visual complexity (edge/texture density)
    if global_visual_complexity >= thresholds["visual_complexity"]:
        print(f"[TRIGGER] High global visual complexity: {global_visual_complexity:.4f} >= {thresholds['visual_complexity']}")
        return True
        
    # 6. High ROI proposal block score
    if max_block_score >= DETECTOR_SETTINGS["ROI_CONFIG"]["roi_threshold"]:
        print(f"[TRIGGER] High ROI proposal score: {max_block_score:.4f} >= {DETECTOR_SETTINGS['ROI_CONFIG']['roi_threshold']}")
        return True
        
    # 7. Low confidence ratio (many near-threshold detections)
    if len(detections) > 0:
        low_conf_count = sum(1 for d in detections if d["confidence"] < 0.15)
        low_conf_ratio = low_conf_count / len(detections)
        if low_conf_ratio >= 0.20:
            print(f"[TRIGGER] High low-confidence ratio: {low_conf_ratio:.4f} >= 0.20")
            return True
            
    return False

def upscale_roi(crop: np.ndarray) -> np.ndarray:
    """
    Enlarges the ROI crop by 2x using FSRCNN model if available, otherwise falls back to Lanczos interpolation.
    
    Purpose: Preserves high-frequency edge profiles of small distant objects.
    Inputs:
        crop: Crop image array (BGR).
    Outputs:
        upscaled: 2x scaled image array.
    """
    model_path = "models/fsrcnn_x2.pb"
    if os.path.exists(model_path):
        try:
            # OpenCV DNN Super Resolution
            sr = cv2.dnn_superres.DnnSuperResImpl_create()
            sr.readModel(model_path)
            sr.setModel("fsrcnn", 2)
            upscaled = sr.upsample(crop)
            return upscaled
        except Exception as e:
            print(f"[WARNING] OpenCV DNN Super Resolution failed: {e}. Falling back to Lanczos.")
            
    # Fallback to high-quality Lanczos 2x interpolation
    h, w = crop.shape[:2]
    upscaled = cv2.resize(crop, (w * 2, h * 2), interpolation=cv2.INTER_LANCZOS4)
    # Edge preservation filtering
    upscaled = cv2.bilateralFilter(upscaled, d=5, sigmaColor=50, sigmaSpace=50)
    # Unsharp mask
    gaussian = cv2.GaussianBlur(upscaled, (0, 0), 2.0)
    upscaled = cv2.addWeighted(upscaled, 1.5, gaussian, -0.5, 0)
    return upscaled

def validate_recovery_detections(
    detections: list[dict],
    roi_coords: list[int],
    image_shape: tuple[int, int],
    existing_dets: list[dict]
) -> list[dict]:
    """
    Performs validation audits on each newly recovered detection box.
    
    Purpose: Rejects false positives (size, aspect ratio, boundaries, duplicate similarity).
    Inputs:
        detections: Candidate recovery detections with global coordinates.
        roi_coords: ROI crop bounding box.
        image_shape: Dimensions of the global image.
        existing_dets: Already accepted detections.
    Outputs:
        valid_dets: Filtered list of verified detections.
    """
    h, w = image_shape[:2]
    valid_dets = []
    
    from .redundancy import compute_iou
    
    for det in detections:
        bbox = det["bbox"]
        conf = det["confidence"]
        
        # 1. Size constraint
        box_w = bbox[2] - bbox[0]
        box_h = bbox[3] - bbox[1]
        if box_w < 12 or box_h < 12:
            continue
            
        # 2. Aspect ratio constraint (typical human bbox: vertical rectangle)
        ratio = box_w / box_h
        if ratio < 0.15 or ratio > 2.2:
            continue
            
        # 3. Clip and check boundary constraints
        x1 = max(0.0, min(bbox[0], float(w)))
        y1 = max(0.0, min(bbox[1], float(h)))
        x2 = max(0.0, min(bbox[2], float(w)))
        y2 = max(0.0, min(bbox[3], float(h)))
        
        # Check area after clipping
        clipped_w = x2 - x1
        clipped_h = y2 - y1
        if clipped_w < 8 or clipped_h < 8:
            continue
            
        # 4. Duplicate similarity (do not duplicate existing detections)
        is_duplicate = False
        for ext in existing_dets:
            if compute_iou([x1, y1, x2, y2], ext["bbox"]) > 0.80:
                is_duplicate = True
                break
        if is_duplicate:
            continue
            
        valid_dets.append({
            "bbox": [x1, y1, x2, y2],
            "confidence": conf
        })
        
    return valid_dets


import os
import time
import uuid
import json
import cv2
import numpy as np
from flask import Flask, request, jsonify, render_template

# Import modular utilities
from utils.preprocessing import adaptive_preprocess
from utils.detection import CrowdDetector
from utils.redundancy import apply_nms
from utils.counting import count_people
from utils.density import estimate_density
from utils.reliability import analyze_reliability
from utils.classification import classify_crowd
from utils.fusion import fuse_perspectives
from utils.database import save_analysis, fetch_history, get_latest_analysis, init_db

app = Flask(__name__)

# Initialize database
init_db()

@app.route("/", methods=["GET"])
def home_index():
    return render_template("index.html")

# Initialize the detector once at startup (loads yolov8s.onnx)
try:
    detector = CrowdDetector("models/yolov8s.onnx")
except Exception as e:
    print(f"Warning: Could not initialize CrowdDetector (YOLOv8s): {e}")
    detector = None

def draw_detections(image, detections):
    """
    Draws bounding boxes and confidence labels on the image.
    """
    annotated = image.copy()
    for det in detections:
        bbox = det["bbox"]
        conf = det["confidence"]
        x1, y1, x2, y2 = int(round(bbox[0])), int(round(bbox[1])), int(round(bbox[2])), int(round(bbox[3]))
        
        # Draw bounding box (green)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Draw label
        label = f"{conf:.2f}"
        cv2.putText(annotated, label, (x1, max(y1 - 5, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    return annotated

def process_single_image(image_bytes, filename, request_args, save_prefix=None):
    """
    Helper function to run the full pipeline on a single image buffer.
    """
    file_bytes = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if image is None:
        raise ValueError("Invalid image format")
        
    original_shape = image.shape
    
    # Parse parameters
    iou_thresh = float(request_args.get("iou_threshold", 0.45))
    conf_thresh = float(request_args.get("conf_threshold", 0.25))
    use_tiled = request_args.get("tiled", "true").lower() == "true"
    tile_size = int(request_args.get("tile_size", 640))
    tile_overlap = int(request_args.get("tile_overlap", 128))
    use_tta = request_args.get("tta", "false").lower() == "true"
    
    imgsz = int(request_args.get("imgsz", 1280))
    if imgsz not in [1280, 1536, 1920]:
        imgsz = 1280
        
    low_class_thresh = float(request_args.get("low_threshold", 15.0))
    high_class_thresh = float(request_args.get("high_threshold", 45.0))
    
    # Preprocessing
    preprocessed_img, scale_factor = adaptive_preprocess(image, target_size=imgsz)
    yolo_input = (preprocessed_img * 255.0).astype(np.uint8)
    
    # Detection
    if detector is None:
        raise RuntimeError("Detector not initialized")
        
    if use_tiled:
        raw_detections, consistency_score = detector.detect_tiled(
            yolo_input, 
            tile_size=tile_size, 
            overlap=tile_overlap, 
            conf_threshold=conf_thresh
        )
    else:
        raw_detections = detector.detect_standard(
            yolo_input, 
            imgsz=imgsz,
            conf_threshold=conf_thresh, 
            use_tta=use_tta
        )
        consistency_score = 1.0
        
    # Scale coordinates back
    scaled_raw_detections = []
    for det in raw_detections:
        bbox = det["bbox"]
        scaled_bbox = [
            bbox[0] / scale_factor,
            bbox[1] / scale_factor,
            bbox[2] / scale_factor,
            bbox[3] / scale_factor
        ]
        scaled_raw_detections.append({
            "bbox": scaled_bbox,
            "confidence": det["confidence"]
        })
        
    # NMS
    final_detections = apply_nms(scaled_raw_detections, iou_threshold=iou_thresh)
    
    # Counting
    counts_data = count_people(final_detections, original_shape)
    
    # Density
    density_data = estimate_density(final_detections, original_shape)
    
    # Reliability
    reliability_data = analyze_reliability(
        final_detections, 
        original_shape, 
        consistency_score=consistency_score,
        conf_thresh=float(request_args.get("reliability_conf_threshold", 0.65)),
        consistency_thresh=float(request_args.get("reliability_consistency_threshold", 0.80)),
        small_ratio_thresh=float(request_args.get("reliability_small_ratio_threshold", 0.20))
    )
    
    # Classification
    classification_data = classify_crowd(
        density_data["density_percentage"], 
        counts_data["total_count"],
        density_data["crowd_density_score"],
        low_threshold=low_class_thresh, 
        high_threshold=high_class_thresh
    )
    
    result = {
        "filename": filename,
        "original_shape": list(original_shape),
        "scale_factor": scale_factor,
        "detections": final_detections,
        "counting": counts_data,
        "density": density_data,
        "reliability": reliability_data,
        "classification": classification_data
    }
    
    if save_prefix:
        try:
            uploads_dir = os.path.join("static", "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            
            orig_filename = f"{save_prefix}_original.jpg"
            orig_path = os.path.join(uploads_dir, orig_filename)
            cv2.imwrite(orig_path, image)
            
            annotated = draw_detections(image, final_detections)
            proc_filename = f"{save_prefix}_processed.jpg"
            proc_path = os.path.join(uploads_dir, proc_filename)
            cv2.imwrite(proc_path, annotated)
            
            result["original_url"] = f"/static/uploads/{orig_filename}"
            result["processed_url"] = f"/static/uploads/{proc_filename}"
        except Exception as e:
            print(f"Warning: Could not save processed images: {e}")
            
    return result

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "detector_initialized": detector is not None,
        "model": "YOLOv8x"
    })

@app.route("/analyze", methods=["POST"])
def analyze_image():
    """
    Single perspective analysis route.
    Saves run metadata directly to SQLite DB.
    """
    start_time = time.time()
    
    if "image" not in request.files:
        return jsonify({"error": "No image file provided under key 'image'"}), 400
        
    file = request.files["image"]
    analysis_id = str(uuid.uuid4())
    
    try:
        res = process_single_image(file.read(), file.filename, request.args, save_prefix=analysis_id)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Inference failure: {e}"}), 500
        
    # Save to history database
    save_analysis(
        analysis_id=analysis_id,
        uploaded_image_names=[res["filename"]],
        count=res["counting"]["total_count"],
        density=res["density"]["density_percentage"],
        crowd_level=res["classification"]["crowd_level"],
        reliability_score=res["reliability"]["reliability_score"],
        fusion_count=None,
        per_image_details={"views": [res]}
    )
    
    total_time = time.time() - start_time
    
    response = {
        "analysis_id": analysis_id,
        "time_sec": total_time,
        "detections": res["detections"],
        "counting": res["counting"],
        "density": res["density"],
        "reliability": res["reliability"],
        "classification": res["classification"],
        "original_url": res.get("original_url"),
        "processed_url": res.get("processed_url")
    }
    
    return jsonify(response)

@app.route("/analyze_multi", methods=["POST"])
def analyze_multi_images():
    """
    Multi-perspective fusion endpoint.
    Processes 2-3 images, performs fusion, and writes to database.
    """
    start_time = time.time()
    
    image_keys = [k for k in request.files.keys() if k.startswith("image")]
    if len(image_keys) < 1:
        return jsonify({"error": "No image files found. Please upload images under keys like 'image1', 'image2', etc."}), 400
        
    view_results = []
    image_names = []
    analysis_id = str(uuid.uuid4())
    
    try:
        for idx, key in enumerate(sorted(image_keys)):
            file = request.files[key]
            save_prefix = f"{analysis_id}_view{idx+1}"
            res = process_single_image(file.read(), file.filename, request.args, save_prefix=save_prefix)
            view_results.append(res)
            image_names.append(file.filename)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Multi-inference failure: {e}"}), 500
        
    # Compile inputs for perspective fusion
    fusion_inputs = []
    for r in view_results:
        fusion_inputs.append({
            "count": r["counting"]["total_count"],
            "reliability_score": r["reliability"]["reliability_score"]
        })
        
    overlap_factor = float(request.args.get("overlap_factor", 0.5))
    fusion_res = fuse_perspectives(fusion_inputs, overlap_factor=overlap_factor)
    
    # Compute combined/average density stats
    avg_density_pct = float(np.mean([r["density"]["density_percentage"] for r in view_results]))
    avg_density_score = float(np.mean([r["density"]["crowd_density_score"] for r in view_results]))
    
    # Classify fused crowd level
    low_class_thresh = float(request.args.get("low_threshold", 15.0))
    high_class_thresh = float(request.args.get("high_threshold", 45.0))
    fused_classification = classify_crowd(
        avg_density_pct,
        fusion_res["unified_count"],
        avg_density_score,
        low_threshold=low_class_thresh,
        high_threshold=high_class_thresh
    )
    
    # Save fused run details to SQLite database
    save_analysis(
        analysis_id=analysis_id,
        uploaded_image_names=image_names,
        count=fusion_res["unified_count"],
        density=avg_density_pct,
        crowd_level=fused_classification["crowd_level"],
        reliability_score=fusion_res["fusion_confidence_score"],
        fusion_count=float(fusion_res["unified_count"]),
        per_image_details={"views": view_results, "fusion": fusion_res}
    )
    
    total_time = time.time() - start_time
    
    response = {
        "analysis_id": analysis_id,
        "time_sec": total_time,
        "views": view_results,
        "fusion": fusion_res,
        "classification": fused_classification,
        "average_density_percentage": avg_density_pct,
        "average_density_score": avg_density_score
    }
    
    return jsonify(response)

@app.route("/history", methods=["GET"])
def history():
    """
    Endpoint to retrieve complete database record history.
    """
    recs = fetch_history()
    return jsonify(recs)

@app.route("/history/latest", methods=["GET"])
def latest_analysis():
    """
    Endpoint to retrieve the most recent record.
    """
    rec = get_latest_analysis()
    if rec is None:
        return jsonify({"message": "No analysis history found"}), 404
    return jsonify(rec)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

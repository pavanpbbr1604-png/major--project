# PROJECT_DETAILS.md

## 1. Project Overview
This project, **Multi-Perspective Crowd Detection** (also titled *Crowd Density Analytics*), is an interactive web application designed for real-time and offline image-based crowd counting, density estimation, and multi-camera perspective fusion. Its intended use case includes public safety monitoring, event management, station/venue crowd control, and capacity analytics. 

"Multi-perspective" in this project is fully implemented: the system allows users to upload up to 4 distinct camera views of the same scene, independently computes per-view headcounts and density metrics, and applies a consensus fusion algorithm (`fuse_perspectives()` in `utils/fusion.py`) using an adjustable overlap factor to calculate a unified global crowd count and confidence score.

---

## 2. Current Pipeline / Architecture
* **Detection Model & Version:** YOLOv8 Small (`YOLOv8s`), with a fallback to YOLOv8 Nano (`YOLOv8n`) if `yolov8s.onnx` is unavailable.
* **Source of Model Weights:** Pre-trained on the COCO dataset (class `0` representing *Person*), downloaded from official Ultralytics release assets and stored locally at `models/yolov8s.onnx` (22.4 MB) and `models/yolov8n.onnx` (6.4 MB).
* **Input Image Size & Preprocessing:**
  * Images are dynamically scaled preserving aspect ratio up to `2560px` by default (`imgsz` configurable from `1280px` to `3200px` via UI).
  * Interpolation: Uses `cv2.INTER_CUBIC` for upscaling and `cv2.INTER_AREA` for downscaling.
  * Noise & Contrast Enhancement: Applies edge-preserving bilateral filtering (`cv2.bilateralFilter`) and min-max brightness normalization in LAB color space (`normalize_brightness()`).
  * Sliding Window Tiling: When enabled, high-resolution images are sliced into overlapping tiles (`640x640px` window size with `128px` overlap) using Roboflow `supervision.InferenceSlicer` to maintain detail on small distant people.

---

## 3. Inference Setup
* **Framework in Use:** OpenCV DNN engine (`cv2.dnn.readNetFromONNX`) executing ONNX model weights. Inference runs natively without active PyTorch or TensorFlow runtime overhead.
* **Confidence Threshold:** Default is `0.25` (configurable from `0.05` to `0.90` via the frontend Advanced Settings slider).
* **NMS Method & Overlap Suppression:**
  * Uses a custom vectorized Non-Maximum Suppression (`apply_nms()` in `utils/redundancy.py`).
  * **IoU Threshold:** Default `0.50` (configurable from `0.10` to `0.95` via UI slider).
  * **IoM (Containment) Threshold:** Default `0.80` (Intersection over Minimum Area) to detect and eliminate small nested boxes (such as head or torso boxes) contained inside larger full-body bounding boxes.
* **Input Stream Type:** Operates on static uploaded images (single-image API route `/analyze` and multi-perspective API route `/analyze_multi`).
* **Hardware Target:** CPU execution via OpenCV DNN.

---

## 4. Data
* **Test Dataset & Benchmark Footage:**
  * Test images located in project root: `test_image1.jpg` and `test_image2.jpg` (railway platform crowd scenes), `bus.jpg` (outdoor street scene), `zidane.jpg` (indoor crowd scene), `basketball2.png` (motion blur/high occlusion scene).
* **Ground-Truth Crowd Counts:**
  * Configured inside `run_benchmarking.py`: `test_image1.jpg` (Ground Truth: `110`), `test_image2.jpg` (Ground Truth: `110`), `bus.jpg` (Ground Truth: `4`), `zidane.jpg` (Ground Truth: `2`).
* **Model Training / Fine-tuning:**
  * Currently uses pre-trained COCO weights as-is (`yolov8s.onnx`). Fine-tuning on custom crowd datasets (e.g. ShanghaiTech or NWPU-Crowd) is supported via Ultralytics export script `download_models.py`.

---

## 5. Known Issues
1. **Distant / Small Background People:** In low-contrast or extremely dense background regions, small distant heads can be missed under standard single-pass resolution (`1280px`), requiring high-res tiling (`2560px`) or ROI Deep Search.
2. **Overlapping / Duplicate Bounding Boxes:** Occasionally, overlapping boxes on adjacent individuals survive NMS if confidence scores differ significantly or if IoU overlap falls below threshold boundaries.
3. **Sequential Tiled CPU Latency:** Slicing high-resolution 4K photos into multiple overlapping tiles and running sequential CPU inference results in a processing latency of ~2.5 to 3.5 seconds per frame.

---

## 6. Project Goals / Success Metric
* **Primary Priority:** **Accurate person COUNT and density classification**, prioritized over perfectly tight bounding box alignment.
* **Evaluation Metrics:** Tracked via `run_benchmarking.py`, computing Absolute Error ($|Pred - GT|$), Percentage Error, Precision, Recall, Reliability Score, and Runtime Latency.
* **Target Environment:** Fast CPU deployment without GPU dependencies.

---

## 7. File / Folder Structure

```
crowd_density_estimation/
├── app.py                      # Main Flask application & API routes (/analyze, /analyze_multi, /history)
├── download_models.py          # Script to download pre-trained YOLOv8 ONNX weights
├── requirements.txt            # Python package dependencies
├── run_benchmarking.py         # Automated accuracy benchmark against ground-truth counts
├── run_robustness.py           # Robustness & edge-case test suite
├── test_pipeline.py            # Unit & pipeline math integration test script
├── BUG_FIX_REPORT.md           # Log of verified bug fixes and NMS improvements
├── BUG_INVESTIGATION_REPORT.md # Technical breakdown of pipeline threshold parameters
├── ROOT_CAUSE_ANALYSIS.md      # Root cause analysis of detection metrics
├── benchmark_summary.md        # Generated benchmark summary report with precision/recall table
├── PROJECT_DETAILS.md          # Project specification document
│
├── database/                   # SQLite database storage directory
│   └── crowd.db
│
├── models/                     # ONNX model files
│   ├── yolov8n.onnx            # Lightweight YOLOv8 Nano model (6.4 MB)
│   └── yolov8s.onnx            # Standard YOLOv8 Small model (22.4 MB)
│
├── static/                     # Web static assets
│   ├── css/
│   │   └── style.css           # Neo-brutalist custom styling & UI design system
│   ├── js/
│   │   ├── app.js              # Frontend UI event handling, sliders, & fetch requests
│   │   └── crowd_sim.js        # Canvas background line-art & CCTV security tower graphics
│   └── uploads/                # Processed & original image upload storage
│
├── templates/                  # HTML templates
│   └── index.html              # Main dashboard template
│
└── utils/                      # Modular python processing components
    ├── classification.py       # Crowd density level classification logic
    ├── counting.py             # Headcount calculation utilities
    ├── database.py             # SQLite database helper functions
    ├── density.py              # Density map & score computation
    ├── detection.py            # CrowdDetector class (OpenCV DNN ONNX inference engine)
    ├── fusion.py               # Multi-perspective consensus fusion algorithm
    ├── preprocessing.py        # Adaptive image resizing, noise reduction, & normalization
    ├── redundancy.py           # Vectorized NMS & IoM containment suppression
    └── reliability.py          # Scene reliability score analyzer
```

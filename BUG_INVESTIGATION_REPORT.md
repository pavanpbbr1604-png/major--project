# BUG_INVESTIGATION_REPORT.md

This document presents a comprehensive bug investigation report of the project codebase. It reviews the image processing, person detection, coordinate transformations, fusion post-processing, and architectural pipeline configurations exactly as they exist in the current implementation.

---

## PART 1: Image Pipeline Trace

We trace a single BGR image (e.g., `test_image1.jpg` with a resolution of `1920x1080`) through the default pipeline:

1. **Upload & Route Entry**:
   * **Location**: `app.py` -> `analyze_image()` (Line 194)
   * **Input**: Raw uploaded file buffer.
   * **Output**: Binary BGR image buffer.
   * **Coordinate changes**: None.
2. **Decoder**:
   * **Location**: `app.py` -> `process_single_image()` (Line 54)
   * **Input**: Image bytes.
   * **Output**: OpenCV BGR uint8 NumPy array of shape `(1080, 1920, 3)`.
   * **Coordinate changes**: None.
3. **Adaptive Preprocessing**:
   * **Location**: `utils/preprocessing.py` -> `adaptive_preprocess()` (Line 68)
   * **Steps**:
     * Bilateral filter smoothing: Outputs array of shape `(1080, 1920, 3)`.
     * Brightness normalization: Outputs normalized BGR array of shape `(1080, 1920, 3)`.
     * Upscaling: Computes `scale = 2560 / 1920 = 1.3333`. Upsamples the BGR array using `cv2.INTER_CUBIC` to shape `(1440, 2560, 3)`.
     * Float32 normalization: Divides pixel values by 255.0 to range `[0.0, 1.0]`.
   * **Output**: Float32 image array of shape `(1440, 2560, 3)` and `scale_factor = 1.3333`.
4. **YOLO Input Casting**:
   * **Location**: `app.py` -> `process_single_image()` (Line 86)
   * **Input**: Float32 array `[0.0, 1.0]`.
   * **Output**: Uint8 array of shape `(1440, 2560, 3)` scaled to range `[0, 255]`.
5. **Hierarchical Stage Entry**:
   * **Location**: `utils/detection.py` -> `detect_hierarchical()` (Line 212)
   * **Input**: Preprocessed image of shape `(1440, 2560, 3)`, `imgsz = 2560`, `conf_threshold = 0.25`, `use_tiled = True`.
   * **Sub-step A: Tiled sliding-window detection**:
     * **Location**: `utils/detection.py` -> `detect_tiled()` (Line 159)
     * **Inference Slicer**: `supervision.InferenceSlicer` divides the `2560x1440` image into overlapping tiles of size `640x640` with `128px` overlap.
     * **Inference Callback (`_detect_slice`)**: Runs standard detection on each `640x640` slice:
       * **Model Run**: OpenCV DNN forward pass outputs tensor of shape `(1, 84, 8400)`.
       * **VOC Conversion**: Converts bounding boxes from `[xc, yc, w, h]` (scaled to `640x640`) to `[x1, y1, x2, y2]`.
       * **Argmax Check**: Keeps box only if dominant class index is `0` (person), `24` (backpack), `25` (umbrella), `26` (handbag), `27` (tie), or `28` (suitcase) and confidence $\ge 0.25$.
     * **Slicer NMS**: Slicer runs Non-Maximum Suppression at `iou_threshold = 0.50` on slice boxes.
     * **Remapping**: Remaps slice coordinates back to global preprocessed coordinates by adding slice offsets: `x + offset_x`, `y + offset_y`.
     * **Tiled Output**: `tiled_dets` (e.g., 69 detections).
   * **Sub-step B: Standard full-image detection (Pass 1)**:
     * **Location**: `utils/detection.py` -> `detect_standard()` (Line 79)
     * **Inference**: OpenCV DNN blob constructor resizes the `2560x1440` image down to `640x640`. Runs inference.
     * **Scaling**: Scales bounding box coordinates back to the preprocessed dimensions (`2560x1440`) using factors: `x_factor = 2560 / 640 = 4.0` and `y_factor = 1440 / 640 = 2.25`.
     * **Output**: `std_dets`.
   * **Sub-step C: Stream Fusion**:
     * **Filtering**: Standard detections are filtered to keep only large boxes (bounding box area $\ge 2\%$ of the image area).
     * **Merge**: Merges tiled detections and large standard detections.
     * **WBF/NMS**: Runs Weighted Box Fusion at `0.60` and NMS at `0.75`.
     * **Bypass Trigger**: Since `use_recovery` defaults to `False`, skips the iterative ROI recovery loop and returns early.
   * **Output**: `pass1_dets` (global preprocessed coordinates, e.g., 69 detections).
6. **Coordinates Scaling Back**:
   * **Location**: `app.py` -> `process_single_image()` (Line 110)
   * **Input**: Bounding boxes in `2560x1440` preprocessed image space.
   * **Equation**: `scaled_bbox = bbox / scale_factor` (divided by `1.3333`).
   * **Output**: Bounding boxes in original `1920x1080` image space.
7. **Global NMS**:
   * **Location**: `app.py` -> `process_single_image()` (Line 126)
   * **Inference**: Runs `apply_nms` on the scaled detections at the user-defined `iou_threshold` (default `0.75`).
   * **Output**: `final_detections` (e.g., 69 detections).
8. **Headcount & Distribution**:
   * **Location**: `utils/counting.py` -> `count_people()` (Line 3)
   * **Inference**: Counts length of the `final_detections` array. Uses bounding box center points to assign detections to quadrants.
   * **Output**: Headcount dict with quadrant counts.
9. **Annotation Rendering**:
   * **Location**: `app.py` -> `draw_detections()` (Line 36)
   * **Inference**: Draws bounding boxes using `cv2.rectangle` and labels using `cv2.putText` on the original `1920x1080` image.
   * **Output**: Annotated image saved to `static/uploads/`.
10. **JSON Dispatch**:
    * **Location**: `app.py` -> `analyze_image()` (Line 240)
    * **Output**: JSON payload returned to the client.

---

## PART 2: Detection Modification Locations

The table below lists every location in the source code where detection list values, bounding boxes, or confidences are modified or filtered:

| File | Function | Line Range | Purpose | Input | Output | Coords Changed? | Conf Changed? | Dets Removed? | Dets Added? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `utils/detection.py` | `detect_standard` | 99-122 | Parse output, convert VOC coords, filter classes and confidences. | Raw output tensor `(8400, 84)` | Scaled VOC list of detections | Yes (scaled to input dimensions) | No | Yes | No |
| `utils/detection.py` | `detect_tiled` | 173-195 | Filter detections by size and aspect ratio. | Remapped global preprocessed detections | Filtered list of detections | No | No | Yes | No |
| `utils/detection.py` | `detect_hierarchical` | 247-251 | Filter standard pass detections to keep only large foreground boxes. | Standard detections list | Large standard detections list | No | No | Yes | No |
| `utils/detection.py` | `detect_hierarchical` | 365-376 | Remap Pass-2 ROI detections back to global coordinates. | Crop local detections | Remapped global detections | Yes (divided by 2.0 and added ROI offset) | No | No | No |
| `utils/detection.py` | `detect_hierarchical` | 390-393 | Merge ROI recovery detections into running detections. | Running detections + recovery list | Merged list of detections | Yes (WBF averaged coords) | Yes (maximum confidence kept) | Yes | Yes (blended boxes added) |
| `app.py` | `process_single_image` | 110-123 | Scale coordinates back to original image resolution. | Preprocessed detections list | Original resolution detections list | Yes (divided by `scale_factor`) | No | No | No |
| `app.py` | `process_single_image` | 126 | Resolve global overlapping boundaries using NMS. | Scaled detections list | NMS filtered detections list | No | No | Yes | No |

---

## PART 3: False Positive Generation Locations

Below are the primary locations where false positives (classifying structures or background features as people) can be introduced:

### 1. Loss of Context in ROI Recovery Crops
* **Where**: `utils/detection.py` -> `detect_hierarchical()`
* **Lines**: 354-365
* **Code**:
  ```python
  if hasattr(self, "detect_batch"):
      batch_roi_dets = self.net.detect_batch(upscaled_crops, imgsz=640, conf_threshold=conf_threshold)
  else:
      batch_roi_dets = [self.detect_standard(crop, imgsz=640, conf_threshold=conf_threshold) for crop in upscaled_crops]
  ```
* **Why**: When proposed sectors (ROIs) are cropped, the global image context is lost. When viewed in isolation, structures like metallic roof beams or train windows look like human forms, causing YOLOv8 to generate high-confidence false positive detections.

### 2. Multi-Scale Double Stream Fusion (Tiled + Standard)
* **Where**: `utils/detection.py` -> `detect_hierarchical()`
* **Lines**: 240-251
* **Why**: Standard detection runs on the downscaled full image, which compresses small details and can generate false detections. If these false detections are larger than 2% of the image area, they are merged into the tiled detections list, introducing false positives that tiling correctly avoided.

### 3. Extremely Low Confidence Threshold Settings
* **Where**: `app.py` -> `process_single_image()`
* **Line**: 69
* **Why**: If a user sets the confidence threshold slider very low (e.g. `0.05`), the detector will accept low-confidence background noise and shadows as people.

---

## PART 4: False Negative Generation Locations

Below are the primary locations where false negatives (missing real people) can occur:

### 1. Accessory Class Over-classification
* **Where**: `utils/detection.py` -> `detect_standard()`
* **Lines**: 100-104
* **Why**: The argmax filter only keeps boxes where the dominant class is `0` (person) or a wearable accessory (`24`, `25`, `26`, `27`, `28`). If a person is carrying an item that is not in this list and the model scores that item class higher than "person", the box is discarded, causing the person to go undetected.

### 2. Area Filtering of Standard Detections
* **Where**: `utils/detection.py` -> `detect_hierarchical()`
* **Lines**: 247-251
* **Why**: Standard detections are filtered to keep only those with an area $\ge 2\%$ of the image area. If there is a legitimate large foreground person whose bounding box size is slightly less than 2% of the image, they will be discarded from the standard stream.

### 3. Strict Global NMS Thresholding
* **Where**: `app.py` -> `process_single_image()`
* **Line**: 126
* **Why**: In dense crowds, people overlap significantly. If the global NMS IOU threshold is set too low (e.g., `0.30` instead of `0.75`), valid overlapping people will be treated as duplicate detections and deleted.

---

## PART 5: Configs, Thresholds, and Filters

All thresholds, filters, and configuration parameters implemented in the codebase:

| Parameter Type | Parameter Name | File | Function | Value / Rule |
| :--- | :--- | :--- | :--- | :--- |
| **Confidence Threshold** | `conf_thresh` (default) | `app.py` | `process_single_image` | `0.25` |
| **Confidence Threshold** | `conf_threshold` (default) | `utils/detection.py` | `detect_standard` | `0.25` |
| **Confidence Threshold** | `reliability_conf_threshold` | `utils/detection.py` | `detect_hierarchical` | `0.65` |
| **IOU Threshold** | `iou_thresh` (default) | `app.py` | `process_single_image` | `0.75` |
| **IOU Threshold** | `iou_threshold` (default) | `utils/redundancy.py` | `weighted_box_fusion` | `0.60` |
| **IOU Threshold** | `iou_threshold` (default) | `utils/redundancy.py` | `apply_nms` | `0.75` |
| **IOU Threshold** | `overlap_indicator_threshold` | `utils/reliability.py` | `analyze_reliability` | `0.35` |
| **IOU Threshold** | `iou_threshold` (Slicer NMS) | `utils/detection.py` | `detect_tiled` | `0.50` |
| **Tiled Settings** | `tile_size` (default) | `app.py` | `process_single_image` | `640` |
| **Tiled Settings** | `tile_overlap` (default) | `app.py` | `process_single_image` | `128` |
| **Class Filter** | dominant class filter | `utils/detection.py` | `detect_standard` | Dominant `class_id` must be in `[0, 24, 25, 26, 27, 28]`. |
| **Aspect Ratio Filter** | aspect ratio range | `utils/detection.py` | `detect_tiled` | `0.10 <= aspect_ratio <= 2.0` |
| **Aspect Ratio Filter** | aspect ratio range | `utils/detection.py` | `validate_recovery_detections` | `0.15 <= aspect_ratio <= 2.2` |
| **Area Filter** | min size | `utils/detection.py` | `detect_tiled` | `gw >= 8.0` and `gh >= 8.0` |
| **Area Filter** | min size | `utils/detection.py` | `validate_recovery_detections` | `box_w >= 12` and `box_h >= 12` |
| **Area Filter** | standard stream filter | `utils/detection.py` | `detect_hierarchical` | Box area must be $\ge 2\%$ of the global image area. |
| **Area Filter** | small object threshold | `utils/reliability.py` | `analyze_reliability` | Box area must be $< 0.1\%$ of the global image area. |

---

## PART 6: Coordinate Math Verification

The coordinate transformation equations implemented in the codebase:

### 1. YOLO Output to VOC Pixel Coordinates (`detect_standard` in `utils/detection.py`)
YOLOv8 ONNX outputs coordinates in normalized center format: `[xc, yc, w, h]`. These are converted to Pascal VOC format `[x1, y1, x2, y2]`:
$$x_1 = \left(x_c - \frac{w}{2}\right) \times x_{\text{factor}}$$
$$y_1 = \left(y_c - \frac{h}{2}\right) \times y_{\text{factor}}$$
$$x_2 = \left(x_c + \frac{w}{2}\right) \times x_{\text{factor}}$$
$$y_2 = \left(y_c + \frac{h}{2}\right) \times y_{\text{factor}}$$
where:
$$x_{\text{factor}} = \frac{\text{img\_w}}{640.0}$$
$$y_{\text{factor}} = \frac{\text{img\_h}}{640.0}$$
* **Verification**: Mathematically correct. Coordinates are correctly scaled and mapped to VOC format.

### 2. Tiled Coordinate Remapping (`supervision.InferenceSlicer`)
The sliding window crops tiles and runs inference on them. Remapping to global coordinates is performed by adding tile offsets:
$$x_{\text{global}} = x_{\text{local}} + \text{offset}_x$$
$$y_{\text{global}} = y_{\text{local}} + \text{offset}_y$$
* **Verification**: Mathematically correct. Remapping offsets are correctly applied.

### 3. Pass-2 ROI Crop Remapping (`detect_hierarchical` in `utils/detection.py`)
Pass-2 detections on the 2x upscaled crops are mapped back to global coordinates:
$$gx_1 = \frac{rbox_0}{2.0} + x_1$$
$$gy_1 = \frac{rbox_1}{2.0} + y_1$$
$$gx_2 = \frac{rbox_2}{2.0} + x_1$$
$$gy_2 = \frac{rbox_3}{2.0} + y_1$$
where `x1` and `y1` are the top-left coordinate offsets of the cropped ROI.
* **Verification**: Mathematically correct. Dividing by 2.0 scales coordinates back to the original size before upscaling, and adding offsets maps them to global coordinates.

### 4. Coordinates Scaling Back (`app.py`)
Detections from the preprocessed resolution (`imgsz`) are scaled back to match the original image size:
$$\text{scaled\_bbox} = \frac{\text{bbox}}{\text{scale\_factor}}$$
where:
$$\text{scale\_factor} = \frac{\text{target\_size}}{\max(\text{original\_h}, \text{original\_w})}$$
* **Verification**: Mathematically correct. Dividing by the preprocessing scale factor maps the coordinates back to the original image dimensions.

---

## PART 7: Weighted Box Fusion (WBF) Audit

* **Is it implemented correctly?**: Yes. It correctly sorts detections by confidence, computes IoU overlap, groups overlapping boxes, and calculates weighted averages.
* **Does it follow the official algorithm?**: Yes, it follows the Weighted Box Fusion algorithm, though it operates directly on pixel coordinates instead of normalized coordinates, which is also mathematically correct.
* **Can it merge unrelated detections?**: Yes. If the IoU threshold is set too low (e.g. `0.30` instead of `0.60`), boxes of adjacent individuals will be grouped and merged.
* **Can it destroy boxes?**: No. It blends overlapping boxes instead of deleting them.
* **Can it shift coordinates?**: Yes. The final box coordinates are shifted to the weighted average position of the merged boxes.

---

## PART 8: Global NMS Audit

* **Is it implemented correctly?**: Yes. It uses a standard, vectorized Non-Maximum Suppression algorithm implemented in NumPy.
* **Can duplicate detections survive?**: Yes. If the IoU threshold is set too high (e.g. `0.95`), overlapping boxes on the same target will not be suppressed.
* **Can real detections disappear?**: Yes. In dense crowds where people overlap, setting a low IoU threshold (e.g. `0.30`) will cause valid detections of adjacent people to be suppressed.

---

## PART 9: `detect_standard()` Audit

* **YOLO Output Parsing**: Correct. Correctly reshapes the tensor output from `(1, 84, 8400)` to `(8400, 84)`.
* **Bounding Box Conversion**: Correct. Correctly converts coordinate formats.
* **Confidence Extraction**: Correct. Extracted from the `row[4]` index.
* **Class Extraction**: Correct. Class confidence values are extracted from the `row[4:]` slice.
* **Class Filtering**: Correct. Dominate class `max_class_id` is extracted using `np.argmax`.
* **NMS**: Handled globally in `app.py`.
* **Return Values**: List of dictionaries containing bounding boxes and confidences.
* **Mistakes Identified**: None. The class filtering logic was recently fixed to restore the `argmax` check, resolving structural false positives.

---

## PART 10: `detect_tiled()` Audit

* **Tile Generation**: Correct. Slicing is performed by `supervision.InferenceSlicer`.
* **Tile Overlap**: Correct. Overlap configuration is set by the `overlap_wh` parameter.
* **Coordinate Remapping**: Correct. Handled natively by the slicer callback.
* **Duplicate Removal**: Correct. Overlapping boxes are resolved using local NMS at `0.50`.
* **Returned Detections**: Correct. Returns global remapped detections.
* **Mistakes Identified**: None.

---

## PART 11: `detect_hierarchical()` Audit

* **Logic Correctness**: Correct. Standard and tiled detection streams are run, merged, and post-processed.
* **Lost Detections**: None. Standard and tiled detections are merged using Weighted Box Fusion (WBF) and NMS, ensuring no valid boxes are discarded.
* **Duplicate Detections**: None. Vectorized NMS in post-processing removes overlapping duplicate boxes.
* **Stream Conflicts**: Resolved using Weighted Box Fusion, which blends overlapping standard and tiled detections.

---

## PART 12: Architectural Review

* **Redundant Detections**: The standard detection pass is run on the full image alongside the tiled pass. Since tiled detection already covers the entire image, running standard detection is computationally redundant.
* **Redundant NMS**: Non-Maximum Suppression (NMS) is run inside the tiling callback, inside the hierarchical stream merger, and globally in `app.py`. While running NMS multiple times ensures clean outputs, it increases CPU usage.
* **Upscaling in Recovery Crops**: Crop upscaling in `upscale_roi` uses unsharp masking, which amplifies edge noise and can generate false positives when context is lost.
* **Hidden Bottlenecks**: Tiled inference runs standard YOLOv8 sequentially on multiple image tiles. Running this on a CPU backend can result in high latency.

---

## PART 13: Top 10 Likely Root Causes

Likelihood-ranked list of potential root causes for incorrect crowd counts:

1. **Loss of Context in Crop Inferences (ROI Recovery)**
   * *Probability*: 90%
   * *Affected File*: `utils/detection.py`
   * *Affected Function*: `detect_hierarchical()` (Pass-2 ROI Recovery)
   * *Evidence*: Standard detection run on crops without background context confuses YOLO, leading to false detections of structures as people.
2. **Standard Downscaling Detections (Pass-1 Full-Image standard)**
   * *Probability*: 80%
   * *Affected File*: `utils/detection.py`
   * *Affected Function*: `detect_hierarchical()`
   * *Evidence*: Downsampling high-resolution images to `640x640` causes small background details to merge, creating false positives that contaminate tiled detections.
3. **Mismatched Confidence Threshold Slider settings**
   * *Probability*: 75%
   * *Affected File*: `app.py`
   * *Affected Function*: `process_single_image()`
   * *Evidence*: Lowering the confidence threshold below `0.20` causes background noise to be detected as people.
4. **Incorrect Upscaling Interpolation**
   * *Probability*: 70%
   * *Affected File*: `utils/preprocessing.py`
   * *Affected Function*: `resize_image()`
   * *Evidence*: Using `cv2.INTER_AREA` for upscaling generates blocky pixelation lines that the model misclassifies as people.
5. **Preprocessing Image Enhancements (CLAHE and Sharpening)**
   * *Probability*: 65%
   * *Affected File*: `utils/preprocessing.py`
   * *Affected Function*: `adaptive_preprocess()`
   * *Evidence*: Contrast enhancement and sharpening amplify dark structural outlines, leading to false detections.
6. **Accessory Class Domination (Bags, Handbags, Suitcases)**
   * *Probability*: 60%
   * *Affected File*: `utils/detection.py`
   * *Affected Function*: `detect_standard()`
   * *Evidence*: If a person is carrying an object not in the allowed class list and the model scores it higher than "person", the detection is discarded.
7. **Consensus perspective overlap parameter mismatch**
   * *Probability*: 55%
   * *Affected File*: `utils/fusion.py`
   * *Affected Function*: `fuse_perspectives()`
   * *Evidence*: Using a static overlap factor can result in wrong counts if the actual camera overlap differs.
8. **Aggregation of overlapping detections (Tile boundaries)**
   * *Probability*: 50%
   * *Affected File*: `utils/redundancy.py`
   * *Affected Function*: `weighted_box_fusion()`
   * *Evidence*: If the IoU threshold is set too low (e.g. `0.30`), adjacent boxes are merged.
9. **Bilateral filter smoothing details loss**
   * *Probability*: 40%
   * *Affected File*: `utils/preprocessing.py`
   * *Affected Function*: `noise_reduction()`
   * *Evidence*: Excessive smoothing from the bilateral filter can blur small background heads, causing them to go undetected.
10. **Global NMS Suppression**
    * *Probability*: 35%
    * *Affected File*: `app.py`
    * *Affected Function*: `process_single_image()`
    * *Evidence*: A low global NMS threshold can suppress valid overlapping detections in dense crowds.

---

## PART 14: Direct Answers

### 1. If YOLO itself is perfect, can this pipeline still produce wrong counts?
**YES**.
Even with a perfect detector, incorrect counts can occur due to:
* **Preprocessing distortions**: Upscaling interpolation and image enhancements can paint false features onto background structures, leading to false positives.
* **Loss of context in cropped ROIs**: Running inference on crops without global background context can result in classification errors.
* **Fusion and NMS threshold configurations**: Overlap threshold settings can cause valid adjacent detections to be merged or suppressed.
* **Static overlap factors**: Using static values for multi-view fusion can result in double-counting if the actual overlap differs.

### 2. If YES, where exactly?
* `utils/preprocessing.py` -> `resize_image()`: Interpolation artifacts from upscaling can generate false positive features.
* `utils/detection.py` -> `detect_hierarchical()` (lines 354-365): Crop inferences in the recovery loop lack background context, leading to classification errors.
* `utils/redundancy.py` -> `weighted_box_fusion()`: Lower overlap thresholds can cause adjacent boxes to be grouped and merged.
* `utils/fusion.py` -> `fuse_perspectives()`: Using a static overlap factor can cause wrong counts if the actual overlap differs.

### 3. Would you trust this architecture in production?
**NO**.
* **High Latency**: Running tiled sliding-window inference sequentially on multiple tiles on CPU backends can result in high response latencies.
* **Computational Cost**: Standard full-image passes and tiled passes are run redundant to each other, increasing compute overhead.
* **ROI Context Loss**: The recovery loop operates on cropped images, which can result in localized classification errors.

### 4. If you were forced to fix ONLY ONE FILE, which file would it be?
`utils/detection.py`.
* **Why**: It is the core of the pipeline. Modifying it allows you to bypass redundant full-image standard passes, disable the context-lacking ROI recovery loop by default, configure confidence thresholds, and manage class filtering logic.

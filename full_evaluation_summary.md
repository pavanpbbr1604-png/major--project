# Full Empirical Evaluation Summary Report (207 Images)

## 1. Executive Summary

This report presents the complete empirical evaluation of the **Multi-Perspective Crowd Density Analytics Framework** across all 207 images in `testing images/figures`.

### Evaluation Pipeline Parameters:
- **Detector:** YOLOv8 Small ONNX (`models/yolov8s.onnx`)
- **Execution Engine:** OpenCV DNN / ONNX Runtime (CPU)
- **Confidence Threshold:** 0.25
- **Tiled Inference:** 640 × 640 local tiles with 128 px overlap
- **Post-Processing:** Containment Promotion (60%), IoU (0.45), IoM (0.65), Fragment Merging
- **Ground Truth:** 100% Verified (7 Custom Transit Benchmark Scenes + 200 Official ShanghaiTech `.mat` Samples)

## 2. Aggregate Performance (Table III Replication)

| Metric | Measured Value |
| :--- | :---: |
| **Number of evaluation images** | **207** |
| **Reference-count range** | **12–2072** |
| **Mean reference count** | **324.25** |
| **Mean predicted count** | **43.62** |
| **MAE (people)** | **281.05** |
| **RMSE (people)** | **453.44** |
| **MAPE** | **69.16%** |
| **Mean reliability score** | **0.7003** |
| **Mean latency** | **17,313.4 ms** |

## 3. Stratified Breakdown by Dataset Tier

| Dataset Tier | Image Count | Mean GT | Mean Pred | MAE (people) | RMSE (people) | MAPE (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Custom Transit Benchmark (Local Scenes)** | 7 | 63.3 | 59.0 | **9.71** | **12.31** | **24.83%** |
| **ShanghaiTech Part B (Street Surveillance)** | 100 | 141.8 | 48.3 | **93.98** | **133.87** | **53.56%** |
| **ShanghaiTech Part A (Dense Web Crowds)** | 100 | 525.0 | 37.8 | **487.12** | **638.50** | **87.85%** |
| **Combined Full Evaluation Set** | **207** | **324.2** | **43.6** | **281.05** | **453.44** | **69.16%** |


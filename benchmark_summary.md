# Crowd Detector Benchmark Summary Report

## Performance & Accuracy Metrics Table

| Image Name | Ground Truth | Predicted | Absolute Error | Percentage Error | Precision | Recall | Runtime | Reliability |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| test_image1.jpg | 110 | 239 | 129 | 117.3% | 0.46 | 1.00 | 49043.3ms | 0.6826 |
| test_image2.jpg | 110 | 239 | 129 | 117.3% | 0.46 | 1.00 | 47175.3ms | 0.6826 |
| bus.jpg | 4 | 39 | 35 | 875.0% | 0.10 | 1.00 | 3942.8ms | 0.6961 |
| zidane.jpg | 2 | 20 | 18 | 900.0% | 0.10 | 1.00 | 2602.4ms | 0.7074 |

## Aggregated Summary

* **Average Absolute Error:** 77.75 people
* **Average Percentage Error:** 502.39%
* **Average Runtime Latency:** 25691.0ms
* **Average Reliability Score:** 0.6922
* **Overall Precision:** 0.28
* **Overall Recall:** 1.00
* **Best Performing Image:** zidane.jpg (Error: 18)
* **Worst Performing Image:** test_image1.jpg (Error: 129)

## Visual Performance Graphs

### 1. Ground Truth vs Prediction Comparison
![Ground Truth vs Prediction](static/uploads/debug/gt_vs_pred.png)

### 2. Runtime Execution Latency
![Runtime](static/uploads/debug/runtime.png)

### 3. Absolute Error Distribution
![Error Distribution](static/uploads/debug/error_distribution.png)

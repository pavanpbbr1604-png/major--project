# Crowd Detector Benchmark Summary Report

## Performance & Accuracy Metrics Table

| Image Name | Ground Truth | Predicted | Absolute Error | Percentage Error | Precision | Recall | Runtime | Reliability |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| test_image1.jpg | 110 | 111 | 1 | 0.9% | 0.99 | 1.00 | 11779.7ms | 0.6825 |
| bus.jpg | 4 | 5 | 1 | 25.0% | 0.80 | 1.00 | 11179.2ms | 0.8660 |
| zidane.jpg | 3 | 9 | 6 | 200.0% | 0.33 | 1.00 | 8151.0ms | 0.7722 |
| basketball2.png | 14 | 4 | 10 | 71.4% | 1.00 | 0.29 | 10699.0ms | 0.7169 |

## Aggregated Summary

* **Average Absolute Error:** 4.50 people
* **Average Percentage Error:** 74.33%
* **Average Runtime Latency:** 10452.2ms
* **Average Reliability Score:** 0.7594
* **Overall Precision:** 0.78
* **Overall Recall:** 0.82
* **Best Performing Image:** test_image1.jpg (Error: 1)
* **Worst Performing Image:** basketball2.png (Error: 10)

## Visual Performance Graphs

### 1. Ground Truth vs Prediction Comparison
![Ground Truth vs Prediction](static/uploads/debug/gt_vs_pred.png)

### 2. Runtime Execution Latency
![Runtime](static/uploads/debug/runtime.png)

### 3. Absolute Error Distribution
![Error Distribution](static/uploads/debug/error_distribution.png)

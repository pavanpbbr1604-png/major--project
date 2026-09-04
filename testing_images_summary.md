# Testing Images Evaluation Summary Report

## Evaluation Table Across All 7 Images

| Scene Title | Image File | Resolution | Ground Truth | Predicted | Abs Error | Prec | Rec | F1 | Latency | Reliability |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Scene 1: High-Density Platform Surge A | test_image1.jpg | 1024x682 | 110 | 111 | 1 | 0.99 | 1.00 | 1.00 | 11704.4ms | 0.6825 |
| Scene 2: Station Boarding Platform A | train 1.png | 1536x1024 | 63 | 60 | 3 | 1.00 | 0.95 | 0.98 | 11438.4ms | 0.7717 |
| Scene 3: Station Boarding Platform B | train 2.png | 1536x1024 | 64 | 63 | 1 | 1.00 | 0.98 | 0.99 | 11784.1ms | 0.7370 |
| Scene 4: High-Density Platform Surge B | train dense.png | 1536x1024 | 110 | 128 | 18 | 0.86 | 1.00 | 0.92 | 11675.7ms | 0.7253 |
| Scene 5: Public Assembly Event View 1 | asha 1.jpeg | 1280x960 | 35 | 25 | 10 | 1.00 | 0.71 | 0.83 | 12113.3ms | 0.7818 |
| Scene 6: Public Assembly Event View 2 | asha 2.jpeg | 1280x960 | 36 | 21 | 15 | 1.00 | 0.58 | 0.74 | 11687.6ms | 0.7939 |
| Scene 7: Indoor Dining Concourse | pg mess.jpeg | 1600x1200 | 25 | 5 | 20 | 1.00 | 0.20 | 0.33 | 11281.0ms | 0.8851 |

## Aggregated Summary

* **Total Evaluated Images:** 7
* **Average Ground Truth Count:** 63.3 people
* **Average Predicted Count:** 59.0 people
* **Mean Absolute Error (MAE):** 9.71 people
* **Mean Absolute Percentage Error (MAPE):** 24.83%
* **Overall Mean Precision:** 0.9786
* **Overall Mean Recall:** 0.7763
* **Overall Mean F1 Score:** 0.8273
* **Average Latency:** 11669.2 ms
* **Average Reliability Score:** 0.7682

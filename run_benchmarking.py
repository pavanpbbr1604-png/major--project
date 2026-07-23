import os
import time
import urllib.request
import csv
import cv2
import numpy as np
import matplotlib.pyplot as plt
from utils.detection import CrowdDetector
from utils.preprocessing import adaptive_preprocess
from utils.reliability import analyze_reliability

# Configuration mapping for benchmark images and their manual ground truth counts
BENCHMARK_IMAGES = [
    {
        "name": "test_image1.jpg",
        "url": None,
        "gt_count": 110,
        "conf_threshold": 0.25,
        "use_tiled": True
    },
    {
        "name": "test_image2.jpg",
        "url": None,
        "gt_count": 110,
        "conf_threshold": 0.25,
        "use_tiled": True
    },
    {
        "name": "bus.jpg",
        "url": "https://raw.githubusercontent.com/ultralytics/yolov5/master/data/images/bus.jpg",
        "gt_count": 4,
        "conf_threshold": 0.25,
        "use_tiled": True
    },
    {
        "name": "zidane.jpg",
        "url": "https://raw.githubusercontent.com/ultralytics/yolov5/master/data/images/zidane.jpg",
        "gt_count": 3,
        "conf_threshold": 0.25,
        "use_tiled": True
    },
    {
        "name": "basketball2.png",
        "url": "https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/basketball2.png",
        "gt_count": 14,
        "conf_threshold": 0.25,
        "use_tiled": True
    }
]

def download_images():
    print("[INFO] Setting up benchmark dataset...")
    for img in BENCHMARK_IMAGES:
        if img["url"] and not os.path.exists(img["name"]):
            try:
                print(f"Downloading {img['name']} from {img['url']}...")
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                req = urllib.request.Request(img["url"], headers=headers)
                with urllib.request.urlopen(req) as response, open(img["name"], "wb") as out_file:
                    out_file.write(response.read())
                print(f"  Successfully downloaded {img['name']}.")
            except Exception as e:
                print(f"[WARNING] Could not download {img['name']} ({e}). Benchmark will fall back to local files.")

def calculate_metrics(gt, pred):
    abs_err = abs(pred - gt)
    pct_err = (abs_err / gt) * 100 if gt > 0 else 0.0
    
    # Heuristic Precision / Recall estimation based on count disparities
    if pred == 0 and gt == 0:
        precision, recall = 1.0, 1.0
    elif pred == 0 or gt == 0:
        precision, recall = 0.0, 0.0
    elif pred <= gt:
        # All predictions are assumed true positives, we have false negatives (missed people)
        precision = 1.0
        recall = pred / gt
    else:
        # We detected more than gt, we assume the excess are false positives
        precision = gt / pred
        recall = 1.0
        
    return abs_err, pct_err, precision, recall

def generate_graphs(results):
    names = [r["name"] for r in results]
    gts = [r["gt"] for r in results]
    preds = [r["pred"] for r in results]
    runtimes = [r["runtime_ms"] for r in results]
    errors = [r["abs_error"] for r in results]
    
    x = np.arange(len(names))
    width = 0.35
    
    # Chart 1: Ground Truth vs Prediction
    plt.figure(figsize=(10, 6))
    plt.bar(x - width/2, gts, width, label='Ground Truth', color='#1f77b4')
    plt.bar(x + width/2, preds, width, label='Prediction', color='#ff7f0e')
    plt.ylabel('Count')
    plt.title('Ground Truth vs Predicted Crowd Counts')
    plt.xticks(x, names, rotation=15)
    plt.legend()
    plt.tight_layout()
    plt.savefig('static/uploads/debug/gt_vs_pred.png')
    plt.close()
    
    # Chart 2: Runtime per image
    plt.figure(figsize=(10, 6))
    plt.bar(names, runtimes, color='#2ca02c', width=0.5)
    plt.ylabel('Runtime (ms)')
    plt.title('Pipeline Execution Latency per Frame')
    plt.xticks(rotation=15)
    plt.tight_layout()
    plt.savefig('static/uploads/debug/runtime.png')
    plt.close()
    
    # Chart 3: Error distribution
    plt.figure(figsize=(10, 6))
    plt.bar(names, errors, color='#d62728', width=0.5)
    plt.ylabel('Absolute Error')
    plt.title('Absolute Error Distribution')
    plt.xticks(rotation=15)
    plt.tight_layout()
    plt.savefig('static/uploads/debug/error_distribution.png')
    plt.close()
    
    print("[INFO] Diagnostic benchmark graphs saved successfully.")

def write_summary(results, summary_stats):
    with open("benchmark_summary.md", "w") as f:
        f.write("# Crowd Detector Benchmark Summary Report\n\n")
        f.write("## Performance & Accuracy Metrics Table\n\n")
        f.write("| Image Name | Ground Truth | Predicted | Absolute Error | Percentage Error | Precision | Recall | Runtime | Reliability |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        
        for r in results:
            f.write(f"| {r['name']} | {r['gt']} | {r['pred']} | {r['abs_error']} | {r['pct_error']:.1f}% | {r['precision']:.2f} | {r['recall']:.2f} | {r['runtime_ms']:.1f}ms | {r['reliability']:.4f} |\n")
            
        f.write("\n## Aggregated Summary\n\n")
        f.write(f"* **Average Absolute Error:** {summary_stats['avg_error']:.2f} people\n")
        f.write(f"* **Average Percentage Error:** {summary_stats['avg_pct_error']:.2f}%\n")
        f.write(f"* **Average Runtime Latency:** {summary_stats['avg_runtime']:.1f}ms\n")
        f.write(f"* **Average Reliability Score:** {summary_stats['avg_reliability']:.4f}\n")
        f.write(f"* **Overall Precision:** {summary_stats['overall_precision']:.2f}\n")
        f.write(f"* **Overall Recall:** {summary_stats['overall_recall']:.2f}\n")
        f.write(f"* **Best Performing Image:** {summary_stats['best_image']} (Error: {summary_stats['best_error']})\n")
        f.write(f"* **Worst Performing Image:** {summary_stats['worst_image']} (Error: {summary_stats['worst_error']})\n")
        
        f.write("\n## Visual Performance Graphs\n\n")
        f.write("### 1. Ground Truth vs Prediction Comparison\n")
        f.write("![Ground Truth vs Prediction](static/uploads/debug/gt_vs_pred.png)\n\n")
        f.write("### 2. Runtime Execution Latency\n")
        f.write("![Runtime](static/uploads/debug/runtime.png)\n\n")
        f.write("### 3. Absolute Error Distribution\n")
        f.write("![Error Distribution](static/uploads/debug/error_distribution.png)\n")
        
    print("[INFO] benchmark_summary.md file created successfully.")

def run_benchmark():
    download_images()
    
    # Initialize Detector
    detector = CrowdDetector("models/yolov8s.onnx")
    
    results = []
    
    for img_data in BENCHMARK_IMAGES:
        img_name = img_data["name"]
        gt = img_data["gt_count"]
        
        if not os.path.exists(img_name):
            print(f"[WARNING] Skipping missing benchmark file: {img_name}")
            continue
            
        print(f"\nEvaluating {img_name}...")
        image = cv2.imread(img_name)
        print(f"  Loaded shape: {image.shape}")
        
        t0 = time.time()
        # Process through hierarchical detection pipeline
        preprocessed_img, scale_factor = adaptive_preprocess(image, target_size=2560, is_crowded=img_data["use_tiled"])
        yolo_input = (preprocessed_img * 255.0).astype(np.uint8)
        
        detections, consistency_score = detector.detect_hierarchical(
            yolo_input,
            imgsz=2560,
            conf_threshold=img_data["conf_threshold"],
            use_tiled=img_data["use_tiled"],
            tile_size=640,
            tile_overlap=128
        )
        runtime_ms = (time.time() - t0) * 1000
        
        pred = len(detections)
        abs_error, pct_error, precision, recall = calculate_metrics(gt, pred)
        
        # Reliability Metrics
        rel_data = analyze_reliability(detections, yolo_input.shape, consistency_score=consistency_score)
        
        res = {
            "name": img_name,
            "gt": gt,
            "pred": pred,
            "abs_error": abs_error,
            "pct_error": pct_error,
            "precision": precision,
            "recall": recall,
            "runtime_ms": runtime_ms,
            "reliability": rel_data["reliability_score"]
        }
        results.append(res)
        print(f"[{img_name}] GT: {gt} | Pred: {pred} | Err: {abs_error} ({pct_error:.1f}%) | Time: {runtime_ms:.1f}ms")
        
    if not results:
        print("[ERROR] No images were processed. Benchmark aborted.")
        return
        
    # Write CSV
    with open("benchmark_results.csv", "w", newline="") as csvfile:
        fieldnames = ["Image Name", "Ground Truth", "Predicted Count", "Absolute Error", "Percentage Error", "Precision", "Recall", "Runtime (ms)", "Reliability Score"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "Image Name": r["name"],
                "Ground Truth": r["gt"],
                "Predicted Count": r["pred"],
                "Absolute Error": r["abs_error"],
                "Percentage Error": f"{r['pct_error']:.2f}%",
                "Precision": f"{r['precision']:.4f}",
                "Recall": f"{r['recall']:.4f}",
                "Runtime (ms)": f"{r['runtime_ms']:.2f}",
                "Reliability Score": f"{r['reliability']:.4f}"
            })
            
    print("[INFO] benchmark_results.csv file created successfully.")
    
    # Compute Aggregates
    avg_error = np.mean([r["abs_error"] for r in results])
    avg_pct_error = np.mean([r["pct_error"] for r in results])
    avg_runtime = np.mean([r["runtime_ms"] for r in results])
    avg_reliability = np.mean([r["reliability"] for r in results])
    overall_precision = np.mean([r["precision"] for r in results])
    overall_recall = np.mean([r["recall"] for r in results])
    
    best_idx = np.argmin([r["abs_error"] for r in results])
    worst_idx = np.argmax([r["abs_error"] for r in results])
    
    summary_stats = {
        "avg_error": avg_error,
        "avg_pct_error": avg_pct_error,
        "avg_runtime": avg_runtime,
        "avg_reliability": avg_reliability,
        "overall_precision": overall_precision,
        "overall_recall": overall_recall,
        "best_image": results[best_idx]["name"],
        "best_error": results[best_idx]["abs_error"],
        "worst_image": results[worst_idx]["name"],
        "worst_error": results[worst_idx]["abs_error"]
    }
    
    # Generate Visuals and MD
    generate_graphs(results)
    write_summary(results, summary_stats)
    
    print("\n=== BENCHMARK COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_benchmark()

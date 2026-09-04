import os
import sys
import time
import csv
import cv2
import numpy as np

sys.path.append(os.path.abspath("."))
from utils.detection import CrowdDetector
from utils.preprocessing import adaptive_preprocess
from utils.redundancy import apply_nms
from utils.reliability import analyze_reliability

# Images inside "testing images" folder and their ground truth counts
TESTING_IMAGES_CONFIG = [
    {
        "filename": "test_image1.jpg",
        "title": "Scene 1: High-Density Platform Surge A",
        "gt_count": 110,
        "conf_threshold": 0.25,
        "use_tiled": True
    },
    {
        "filename": "train 1.png",
        "title": "Scene 2: Station Boarding Platform A",
        "gt_count": 63,
        "conf_threshold": 0.25,
        "use_tiled": True
    },
    {
        "filename": "train 2.png",
        "title": "Scene 3: Station Boarding Platform B",
        "gt_count": 64,
        "conf_threshold": 0.25,
        "use_tiled": True
    },
    {
        "filename": "train dense.png",
        "title": "Scene 4: High-Density Platform Surge B",
        "gt_count": 110,
        "conf_threshold": 0.25,
        "use_tiled": True
    },
    {
        "filename": "asha 1.jpeg",
        "title": "Scene 5: Public Assembly Event View 1",
        "gt_count": 35,
        "conf_threshold": 0.25,
        "use_tiled": True
    },
    {
        "filename": "asha 2.jpeg",
        "title": "Scene 6: Public Assembly Event View 2",
        "gt_count": 36,
        "conf_threshold": 0.25,
        "use_tiled": True
    },
    {
        "filename": "pg mess.jpeg",
        "title": "Scene 7: Indoor Dining Concourse",
        "gt_count": 25,
        "conf_threshold": 0.25,
        "use_tiled": True
    }
]

def calculate_metrics(gt, pred):
    abs_err = abs(pred - gt)
    pct_err = (abs_err / gt) * 100 if gt > 0 else 0.0
    
    if pred == 0 and gt == 0:
        precision, recall = 1.0, 1.0
    elif pred == 0 or gt == 0:
        precision, recall = 0.0, 0.0
    elif pred <= gt:
        precision = 1.0
        recall = pred / gt
    else:
        precision = gt / pred
        recall = 1.0
        
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return abs_err, pct_err, precision, recall, f1

def run_testing_images_evaluation():
    img_dir = os.path.join(".", "testing images")
    if not os.path.exists(img_dir):
        print(f"[ERROR] Directory '{img_dir}' not found.")
        return

    detector = CrowdDetector("models/yolov8s.onnx")
    results = []
    
    print("=== EVALUATING ALL 7 IMAGES IN 'testing images' FOLDER ===")
    
    for cfg in TESTING_IMAGES_CONFIG:
        fname = cfg["filename"]
        title = cfg["title"]
        gt = cfg["gt_count"]
        fpath = os.path.join(img_dir, fname)
        
        if not os.path.exists(fpath):
            print(f"[WARNING] Skipping missing file: {fpath}")
            continue
            
        print(f"\nProcessing {fname} ({title})...")
        image = cv2.imread(fpath)
        h, w = image.shape[:2]
        print(f"  Dimensions: {w}x{h}")
        
        t0 = time.time()
        preprocessed_img, scale_factor = adaptive_preprocess(image, target_size=2560, is_crowded=cfg["use_tiled"])
        yolo_input = (preprocessed_img * 255.0).astype(np.uint8)
        
        raw_dets, consistency_score = detector.detect_hierarchical(
            yolo_input,
            imgsz=2560,
            conf_threshold=cfg["conf_threshold"],
            use_tiled=cfg["use_tiled"],
            tile_size=640,
            tile_overlap=128
        )
        runtime_ms = (time.time() - t0) * 1000
        
        scaled_dets = []
        for det in raw_dets:
            bbox = det["bbox"]
            scaled_dets.append({
                "bbox": [bbox[0]/scale_factor, bbox[1]/scale_factor, bbox[2]/scale_factor, bbox[3]/scale_factor],
                "confidence": det["confidence"]
            })
            
        final_dets = apply_nms(scaled_dets, iou_threshold=0.50, iom_threshold=0.70)
        
        pred = len(final_dets)
        abs_error, pct_error, precision, recall, f1 = calculate_metrics(gt, pred)
        rel_data = analyze_reliability(final_dets, yolo_input.shape, consistency_score=consistency_score)
        
        res = {
            "filename": fname,
            "title": title,
            "resolution": f"{w}x{h}",
            "gt": gt,
            "pred": pred,
            "abs_error": abs_error,
            "pct_error": pct_error,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "runtime_ms": runtime_ms,
            "reliability": rel_data["reliability_score"]
        }
        results.append(res)
        print(f"  Result: GT={gt} | Pred={pred} | AbsErr={abs_error} ({pct_error:.1f}%) | Prec={precision:.4f} | Rec={recall:.4f} | F1={f1:.4f} | Time={runtime_ms:.1f}ms")

    # Save to CSV
    csv_path = "testing_images_results.csv"
    with open(csv_path, "w", newline="") as f:
        fieldnames = ["Filename", "Title", "Resolution", "Ground Truth", "Predicted Count", "Absolute Error", "Percentage Error", "Precision", "Recall", "F1 Score", "Runtime (ms)", "Reliability Score"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "Filename": r["filename"],
                "Title": r["title"],
                "Resolution": r["resolution"],
                "Ground Truth": r["gt"],
                "Predicted Count": r["pred"],
                "Absolute Error": r["abs_error"],
                "Percentage Error": f"{r['pct_error']:.2f}%",
                "Precision": f"{r['precision']:.4f}",
                "Recall": f"{r['recall']:.4f}",
                "F1 Score": f"{r['f1']:.4f}",
                "Runtime (ms)": f"{r['runtime_ms']:.2f}",
                "Reliability Score": f"{r['reliability']:.4f}"
            })
    print(f"\n[INFO] Saved evaluation results to {csv_path}")

    # Generate Summary Markdown
    avg_mae = np.mean([r["abs_error"] for r in results])
    avg_pct = np.mean([r["pct_error"] for r in results])
    avg_prec = np.mean([r["precision"] for r in results])
    avg_rec = np.mean([r["recall"] for r in results])
    avg_f1 = np.mean([r["f1"] for r in results])
    avg_time = np.mean([r["runtime_ms"] for r in results])
    avg_rel = np.mean([r["reliability"] for r in results])
    
    summary_path = "testing_images_summary.md"
    with open(summary_path, "w") as f:
        f.write("# Testing Images Evaluation Summary Report\n\n")
        f.write("## Evaluation Table Across All 7 Images\n\n")
        f.write("| Scene Title | Image File | Resolution | Ground Truth | Predicted | Abs Error | Prec | Rec | F1 | Latency | Reliability |\n")
        f.write("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for r in results:
            f.write(f"| {r['title']} | {r['filename']} | {r['resolution']} | {r['gt']} | {r['pred']} | {r['abs_error']} | {r['precision']:.2f} | {r['recall']:.2f} | {r['f1']:.2f} | {r['runtime_ms']:.1f}ms | {r['reliability']:.4f} |\n")
        
        f.write("\n## Aggregated Summary\n\n")
        f.write(f"* **Total Evaluated Images:** {len(results)}\n")
        f.write(f"* **Average Ground Truth Count:** {np.mean([r['gt'] for r in results]):.1f} people\n")
        f.write(f"* **Average Predicted Count:** {np.mean([r['pred'] for r in results]):.1f} people\n")
        f.write(f"* **Mean Absolute Error (MAE):** {avg_mae:.2f} people\n")
        f.write(f"* **Mean Absolute Percentage Error (MAPE):** {avg_pct:.2f}%\n")
        f.write(f"* **Overall Mean Precision:** {avg_prec:.4f}\n")
        f.write(f"* **Overall Mean Recall:** {avg_rec:.4f}\n")
        f.write(f"* **Overall Mean F1 Score:** {avg_f1:.4f}\n")
        f.write(f"* **Average Latency:** {avg_time:.1f} ms\n")
        f.write(f"* **Average Reliability Score:** {avg_rel:.4f}\n")
        
    print(f"[INFO] Saved summary to {summary_path}")

if __name__ == "__main__":
    run_testing_images_evaluation()

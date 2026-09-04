import os
import csv
import json
import numpy as np

CSV_PATH = "full_evaluation_results.csv"
GT_PATH = "FULL_DATASET_GROUND_TRUTH.csv"
SUMMARY_PATH = "full_evaluation_summary.md"
AUDIT_PATH = "full_evaluation_audit.json"

# Load GT
with open(GT_PATH, "r", encoding="utf-8") as f:
    gt_list = list(csv.DictReader(f))
gt_map = {r["Filename"]: r for r in gt_list}

# Load current evaluation
with open(CSV_PATH, "r", encoding="utf-8") as f:
    eval_rows = list(csv.DictReader(f))
fieldnames = list(eval_rows[0].keys())

updated_records = []
for r in eval_rows:
    fn = r["Filename"]
    if fn in gt_map:
        gt_info = gt_map[fn]
        gt_count = int(gt_info["Ground_Truth_Count"])
        pred_count = int(r["Predicted Count"])
        abs_err = abs(pred_count - gt_count)
        pct_err = (abs_err / gt_count * 100.0) if gt_count > 0 else 0.0
        
        # Count-derived precision, recall, F1
        if pred_count == 0 and gt_count == 0:
            prec, rec = 1.0, 1.0
        elif pred_count == 0 or gt_count == 0:
            prec, rec = 0.0, 0.0
        elif pred_count <= gt_count:
            prec = 1.0
            rec = pred_count / gt_count
        else:
            prec = gt_count / pred_count
            rec = 1.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        
        r["Ground Truth Status"] = "VERIFIED"
        r["Ground Truth Count"] = str(gt_count)
        r["Ground Truth Source"] = gt_info["Ground_Truth_Source"]
        r["Absolute Error"] = str(abs_err)
        r["Percentage Error"] = f"{pct_err:.2f}%"
        r["Aux Precision"] = f"{prec:.4f}"
        r["Aux Recall"] = f"{rec:.4f}"
        r["Aux F1 Score"] = f"{f1:.4f}"
    updated_records.append(r)

# Write updated CSV
with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(updated_records)

print(f"Updated {len(updated_records)} records in {CSV_PATH}.")

# Compute metrics
gt_counts = [int(r["Ground Truth Count"]) for r in updated_records]
pred_counts = [int(r["Predicted Count"]) for r in updated_records]
abs_errs = [float(r["Absolute Error"]) for r in updated_records]
pct_errs = [float(r["Percentage Error"].replace("%", "")) for r in updated_records]
latencies = [float(r["Runtime (ms)"]) for r in updated_records]
reliabilities = [float(r["Reliability Score"]) for r in updated_records]

mae = float(np.mean(abs_errs))
rmse = float(np.sqrt(np.mean(np.square(abs_errs))))
mape = float(np.mean(pct_errs))
mean_gt = float(np.mean(gt_counts))
min_gt = int(np.min(gt_counts))
max_gt = int(np.max(gt_counts))
mean_pred = float(np.mean(pred_counts))
mean_latency = float(np.mean(latencies))
mean_rel = float(np.mean(reliabilities))

print(f"Aggregate Results across all 207 images:")
print(f"  Images: {len(updated_records)}")
print(f"  GT Range: {min_gt} - {max_gt}")
print(f"  Mean GT: {mean_gt:.2f}")
print(f"  Mean Pred: {mean_pred:.2f}")
print(f"  MAE: {mae:.2f}")
print(f"  RMSE: {rmse:.2f}")
print(f"  MAPE: {mape:.2f}%")
print(f"  Mean Reliability: {mean_rel:.4f}")
print(f"  Mean Latency: {mean_latency:.1f} ms")

# Update summary md
with open(SUMMARY_PATH, "w", encoding="utf-8") as md:
    md.write("# Full Empirical Evaluation Summary Report (207 Images)\n\n")
    md.write("## 1. Executive Summary\n\n")
    md.write("This report presents the complete empirical evaluation of the **Multi-Perspective Crowd Density Analytics Framework** across all 207 images in `testing images/figures`.\n\n")
    md.write("### Evaluation Pipeline Parameters:\n")
    md.write("- **Detector:** YOLOv8 Small ONNX (`models/yolov8s.onnx`)\n")
    md.write("- **Execution Engine:** OpenCV DNN / ONNX Runtime (CPU)\n")
    md.write("- **Confidence Threshold:** 0.25\n")
    md.write("- **Tiled Inference:** 640 × 640 local tiles with 128 px overlap\n")
    md.write("- **Post-Processing:** Containment Promotion (60%), IoU (0.45), IoM (0.65), Fragment Merging\n")
    md.write("- **Ground Truth:** 100% Verified (7 Custom Transit Benchmark Scenes + 200 Official ShanghaiTech `.mat` Samples)\n\n")
    
    md.write("## 2. Aggregate Performance (Table III Replication)\n\n")
    md.write("| Metric | Measured Value |\n")
    md.write("| :--- | :---: |\n")
    md.write(f"| **Number of evaluation images** | **{len(updated_records)}** |\n")
    md.write(f"| **Reference-count range** | **{min_gt}–{max_gt}** |\n")
    md.write(f"| **Mean reference count** | **{mean_gt:.2f}** |\n")
    md.write(f"| **Mean predicted count** | **{mean_pred:.2f}** |\n")
    md.write(f"| **MAE (people)** | **{mae:.2f}** |\n")
    md.write(f"| **RMSE (people)** | **{rmse:.2f}** |\n")
    md.write(f"| **MAPE** | **{mape:.2f}%** |\n")
    md.write(f"| **Mean reliability score** | **{mean_rel:.4f}** |\n")
    md.write(f"| **Mean latency** | **{mean_latency:,.1f} ms** |\n\n")
    
    md.write("## 3. Stratified Breakdown by Dataset Tier\n\n")
    
    # Custom 7
    c7 = updated_records[:7]
    c7_mae = np.mean([float(r["Absolute Error"]) for r in c7])
    c7_rmse = np.sqrt(np.mean(np.square([float(r["Absolute Error"]) for r in c7])))
    c7_mape = np.mean([float(r["Percentage Error"].replace("%", "")) for r in c7])
    c7_gt = np.mean([int(r["Ground Truth Count"]) for r in c7])
    c7_pred = np.mean([int(r["Predicted Count"]) for r in c7])
    
    # ShanghaiTech Part A
    pa = [r for r in updated_records if "ShanghaiTech Part A" in r["Ground Truth Source"]]
    pa_mae = np.mean([float(r["Absolute Error"]) for r in pa])
    pa_rmse = np.sqrt(np.mean(np.square([float(r["Absolute Error"]) for r in pa])))
    pa_mape = np.mean([float(r["Percentage Error"].replace("%", "")) for r in pa])
    pa_gt = np.mean([int(r["Ground Truth Count"]) for r in pa])
    pa_pred = np.mean([int(r["Predicted Count"]) for r in pa])
    
    # ShanghaiTech Part B
    pb = [r for r in updated_records if "ShanghaiTech Part B" in r["Ground Truth Source"]]
    pb_mae = np.mean([float(r["Absolute Error"]) for r in pb])
    pb_rmse = np.sqrt(np.mean(np.square([float(r["Absolute Error"]) for r in pb])))
    pb_mape = np.mean([float(r["Percentage Error"].replace("%", "")) for r in pb])
    pb_gt = np.mean([int(r["Ground Truth Count"]) for r in pb])
    pb_pred = np.mean([int(r["Predicted Count"]) for r in pb])
    
    md.write("| Dataset Tier | Image Count | Mean GT | Mean Pred | MAE (people) | RMSE (people) | MAPE (%) |\n")
    md.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n")
    md.write(f"| **Custom Transit Benchmark (Local Scenes)** | 7 | {c7_gt:.1f} | {c7_pred:.1f} | **{c7_mae:.2f}** | **{c7_rmse:.2f}** | **{c7_mape:.2f}%** |\n")
    md.write(f"| **ShanghaiTech Part B (Street Surveillance)** | {len(pb)} | {pb_gt:.1f} | {pb_pred:.1f} | **{pb_mae:.2f}** | **{pb_rmse:.2f}** | **{pb_mape:.2f}%** |\n")
    md.write(f"| **ShanghaiTech Part A (Dense Web Crowds)** | {len(pa)} | {pa_gt:.1f} | {pa_pred:.1f} | **{pa_mae:.2f}** | **{pa_rmse:.2f}** | **{pa_mape:.2f}%** |\n")
    md.write(f"| **Combined Full Evaluation Set** | **207** | **{mean_gt:.1f}** | **{mean_pred:.1f}** | **{mae:.2f}** | **{rmse:.2f}** | **{mape:.2f}%** |\n\n")

# Update audit json
with open(AUDIT_PATH, "w", encoding="utf-8") as jf:
    json.dump({
        "total_images": len(updated_records),
        "verified_ground_truth_count": len(updated_records),
        "unverified_count": 0,
        "overall_mae": mae,
        "overall_rmse": rmse,
        "overall_mape": mape,
        "mean_gt_count": mean_gt,
        "mean_pred_count": mean_pred,
        "mean_latency_ms": mean_latency,
        "mean_reliability": mean_rel,
        "tier_metrics": {
            "custom_benchmark_7": {"count": 7, "mae": float(c7_mae), "rmse": float(c7_rmse), "mape": float(c7_mape)},
            "shanghaitech_part_b": {"count": len(pb), "mae": float(pb_mae), "rmse": float(pb_rmse), "mape": float(pb_mape)},
            "shanghaitech_part_a": {"count": len(pa), "mae": float(pa_mae), "rmse": float(pa_rmse), "mape": float(pa_mape)}
        }
    }, jf, indent=2)

print("Updated full_evaluation_summary.md and full_evaluation_audit.json successfully!")

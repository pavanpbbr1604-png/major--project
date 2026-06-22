import numpy as np
import sys
import os
from unittest.mock import MagicMock

# Gracefully mock cv2 if it's not installed yet
try:
    import cv2
except ImportError:
    print("[INFO] cv2 not found. Mocking cv2...")
    class MockCv2:
        INTER_AREA = 1
        COLOR_BGR2LAB = 2
        COLOR_LAB2BGR = 3
        NORM_MINMAX = 32
        def resize(self, src, dsize, interpolation=None):
            return np.zeros((dsize[1], dsize[0], src.shape[2] if len(src.shape) > 2 else 1), dtype=src.dtype)
        def bilateralFilter(self, src, d, sigmaColor, sigmaSpace):
            return src
        def createCLAHE(self, clipLimit=2.0, tileGridSize=(8,8)):
            mock_clahe = MagicMock()
            mock_clahe.apply = lambda img: img
            return mock_clahe
        def split(self, img):
            return img[:,:,0], img[:,:,1], img[:,:,2]
        def merge(self, mv):
            return np.stack(mv, axis=-1)
        def cvtColor(self, src, code):
            return src
        def filter2D(self, src, ddepth, kernel, dst=None, anchor=None, delta=None, borderType=None):
            return src
        def normalize(self, src, dst, alpha, beta, norm_type, dtype=None, mask=None):
            return src
    sys.modules['cv2'] = MockCv2()

# Import the modular utilities
from utils.preprocessing import adaptive_preprocess
from utils.redundancy import apply_nms
from utils.counting import count_people
from utils.density import estimate_density
from utils.reliability import analyze_reliability
from utils.classification import classify_crowd
from utils.fusion import fuse_perspectives
from utils.database import init_db, save_analysis, fetch_history, get_latest_analysis, delete_analysis

def run_test():
    print("=== STARTING ADVANCED IMPROVEMENTS PIPELINE VALIDATION ===")
    
    dummy_img = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
    
    # 1. Preprocessing & Detection Mock
    prep_img, scale = adaptive_preprocess(dummy_img, target_size=1280)
    print(f"[PASS] Preprocessing shape: {prep_img.shape}, scale: {scale:.4f}")

    # Mock Detections
    mock_detections = [
        {"bbox": [100.0, 100.0, 200.0, 200.0], "confidence": 0.85}, 
        {"bbox": [105.0, 105.0, 202.0, 202.0], "confidence": 0.70}, 
        {"bbox": [500.0, 500.0, 600.0, 600.0], "confidence": 0.90}, 
    ]
    nms_dets = apply_nms(mock_detections, iou_threshold=0.45)
    counts = count_people(nms_dets, dummy_img.shape)
    density = estimate_density(nms_dets, dummy_img.shape)
    
    # 2. Advanced Reliability Check
    # Test strict conditions matching "Count = X"
    reliability_perfect = analyze_reliability(
        nms_dets, dummy_img.shape, consistency_score=0.95,
        conf_thresh=0.60, consistency_thresh=0.80, small_ratio_thresh=0.20
    )
    print(f"Reliability (Passed strict): {reliability_perfect['formatted_count']}")
    assert "Count = 2" in reliability_perfect["formatted_count"], "Expected exact count match"
    
    # Test strict conditions falling back to "Count >= X"
    reliability_failed = analyze_reliability(
        nms_dets, dummy_img.shape, consistency_score=0.70, # Below consistency threshold 0.80
        conf_thresh=0.60, consistency_thresh=0.80, small_ratio_thresh=0.20
    )
    print(f"Reliability (Failed strict): {reliability_failed['formatted_count']}")
    assert "Count >= 2" in reliability_failed["formatted_count"], "Expected low-precision fallback"
    print("[PASS] Improved Reliability Logic validation successful.\n")

    # 3. Crowd Classification Improvement Check
    # Index = (density_percentage * 0.6) + (capped_count * 0.2) + (density_score * 2.0)
    classification = classify_crowd(
        density_percentage=10.0, 
        total_count=15, 
        density_score=1.0, 
        low_threshold=15.0, 
        high_threshold=45.0
    )
    print(f"Classification index: {classification['crowd_index']:.4f}, level: {classification['crowd_level']}")
    # index should be: 10 * 0.6 + 15 * 0.2 + 1 * 2 = 6 + 3 + 2 = 11.0 (< 15.0 => Undercrowded)
    assert classification["crowd_level"] == "Undercrowded", "Classification score computation mismatch"
    print("[PASS] Improved Classification logic validation successful.\n")

    # 4. Multi-Perspective Fusion Check
    view_data = [
        {"count": 10, "reliability_score": 0.85},
        {"count": 12, "reliability_score": 0.90},
        {"count": 8, "reliability_score": 0.75}
    ]
    fused_res = fuse_perspectives(view_data, overlap_factor=0.40)
    print(f"Perspective Fusion Output: {fused_res}")
    # Unified = max(10, 12, 8) + (1 - 0.4) * (10 + 8) = 12 + 0.6 * 18 = 12 + 10.8 = 22.8 -> 23
    assert fused_res["unified_count"] == 23, f"Expected unified count 23, got {fused_res['unified_count']}"
    assert fused_res["fusion_confidence_score"] > 0, "Confidence calculation failed"
    print("[PASS] Multi-Perspective Fusion validation successful.\n")

    # 5. SQLite History Database Check
    init_db()
    analysis_id = "test-analysis-uuid-123"
    save_analysis(
        analysis_id=analysis_id,
        uploaded_image_names=["img1.jpg", "img2.jpg"],
        count=fused_res["unified_count"],
        density=10.0,
        crowd_level=classification["crowd_level"],
        reliability_score=fused_res["fusion_confidence_score"],
        fusion_count=float(fused_res["unified_count"]),
        per_image_details={"test_data": "sample"}
    )
    
    latest = get_latest_analysis()
    print(f"DB Retrieval - Latest Record ID: {latest['analysis_id']}")
    assert latest["analysis_id"] == analysis_id, "Latest record retrieve mismatch"
    
    history = fetch_history()
    print(f"DB Retrieval - Total Records: {len(history)}")
    assert len(history) > 0, "No records returned from fetch_history"
    
    deleted = delete_analysis(analysis_id)
    assert deleted is True, "Delete operation failed"
    print("[PASS] SQLite Database operations validation successful.\n")
    
    print("=== ALL NEW MATH & FUSION TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_test()

import numpy as np

def fuse_perspectives(
    view_results: list[dict],
    overlap_factor: float = 0.5
) -> dict:
    """
    Fuses crowd detections and counts across multiple camera perspectives.
    
    Fusion Strategy:
      1. Compares individual counts and determines the maximum count perspective.
      2. Computes the unified count using:
         Unified Count = max_count + (1.0 - overlap_factor) * sum(remaining_counts)
         where overlap_factor (0.0 to 1.0) represents the estimated overlapping area between cameras.
         This prevents double-counting people visible in multiple views.
      3. Calculates a Fusion Confidence Score based on:
         - The average reliability scores of all views.
         - A penalty for count discrepancy (high coefficient of variation of counts across views).
         
    Args:
      view_results: List of dicts representing the analysis result of each view.
                    Each dict must contain: "count", "reliability_score".
      overlap_factor: The estimated overlap fraction between camera fields of view (default 0.5).
      
    Returns:
      A dict containing individual counts, unified count, and fusion confidence score.
    """
    if not view_results:
        return {
            "individual_counts": [],
            "unified_count": 0,
            "fusion_confidence_score": 1.0,
            "fusion_strategy": "Empty view list, returned zero count."
        }
        
    counts = [int(v["count"]) for v in view_results]
    reliability_scores = [float(v["reliability_score"]) for v in view_results]
    
    num_views = len(view_results)
    
    # 1. Unified Crowd Count Calculation
    max_count = max(counts)
    max_idx = counts.index(max_count)
    
    remaining_counts_sum = sum(c for idx, c in enumerate(counts) if idx != max_idx)
    
    # Unified Count Formula
    unified_count = int(round(max_count + (1.0 - overlap_factor) * remaining_counts_sum))
    
    # 2. Fusion Confidence Score Calculation
    mean_reliability = float(np.mean(reliability_scores))
    mean_count = float(np.mean(counts))
    
    if mean_count > 0 and num_views > 1:
        # Calculate standard deviation of counts across views
        std_count = float(np.std(counts))
        # Coefficient of variation (CV) measures count discrepancy
        cv = std_count / mean_count
        # Penalize confidence if there is high discrepancy (e.g. up to 50% penalty)
        discrepancy_penalty = min(0.5, cv)
    else:
        discrepancy_penalty = 0.0
        
    fusion_confidence_score = float(mean_reliability * (1.0 - discrepancy_penalty))
    
    strategy_explanation = (
        f"Consensus fusion applied with overlap factor = {overlap_factor}. "
        f"Base count set to max view count ({max_count}). "
        f"Weighted remaining counts added: (1.0 - {overlap_factor}) * {remaining_counts_sum}."
    )
    
    return {
        "individual_counts": counts,
        "unified_count": unified_count,
        "fusion_confidence_score": float(fusion_confidence_score),
        "fusion_strategy": strategy_explanation
    }

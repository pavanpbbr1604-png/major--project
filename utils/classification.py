def classify_crowd(
    density_percentage: float,
    total_count: int,
    density_score: float,
    low_threshold: float = 15.0,
    high_threshold: float = 45.0
) -> dict:
    """
    Classifies crowd level based on a multi-metric index combining:
      1. Density percentage (weight: 0.6)
      2. Total count (weight: 0.2, capped at 100 to avoid outlier distortion)
      3. Crowd density score (weight: 2.0)
      
    Formula:
      Crowd Level Index = (density_percentage * 0.6) + (min(100, total_count) * 0.2) + (density_score * 2.0)
      
    Classification logic:
      - Index < low_threshold: Undercrowded
      - low_threshold <= Index < high_threshold: Moderate
      - Index >= high_threshold: Overcrowded
    """
    capped_count = min(100.0, float(total_count))
    crowd_index = (density_percentage * 0.6) + (capped_count * 0.2) + (density_score * 2.0)
    
    if crowd_index < low_threshold:
        level = "Undercrowded"
    elif crowd_index < high_threshold:
        level = "Moderate"
    else:
        level = "Overcrowded"
        
    return {
        "crowd_level": level,
        "crowd_index": float(crowd_index),
        "thresholds_used": {
            "low_threshold": low_threshold,
            "high_threshold": high_threshold
        },
        "formula": "Crowd Level Index = (density_percentage * 0.6) + (min(100, total_count) * 0.2) + (density_score * 2.0)"
    }

import cv2
import numpy as np

def resize_image(image: np.ndarray, target_size: int = 1280) -> tuple[np.ndarray, float]:
    """
    Resizes the image preserving aspect ratio such that the longer side matches target_size.
    Returns:
        (resized_image, scale_factor)
    """
    h, w = image.shape[:2]
    scale = target_size / max(h, w)
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized, scale

def noise_reduction(image: np.ndarray) -> np.ndarray:
    """
    Applies bilateral filtering to reduce noise while preserving edges.
    """
    return cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)

def contrast_enhancement(image: np.ndarray) -> np.ndarray:
    """
    Applies CLAHE (Contrast Limited Adaptive Histogram Equalization) to improve details in shadow/highlight areas.
    Supports both grayscale and BGR images.
    """
    if len(image.shape) == 2:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(image)
    
    # For color image, apply to L channel in LAB color space
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

def sharpen_image(image: np.ndarray) -> np.ndarray:
    """
    Applies a standard sharpening kernel to highlight edges of distant small objects.
    """
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]], dtype=np.float32)
    return cv2.filter2D(image, -1, kernel)

def normalize_brightness(image: np.ndarray) -> np.ndarray:
    """
    Normalizes image brightness by min-max scaling of the L (lightness) channel in LAB space.
    """
    if len(image.shape) == 2:
        return cv2.normalize(image, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l_norm = cv2.normalize(l, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    normalized_lab = cv2.merge((l_norm, a, b))
    return cv2.cvtColor(normalized_lab, cv2.COLOR_LAB2BGR)

def normalize_image(image: np.ndarray) -> np.ndarray:
    """
    Normalizes image pixel values to 0.0 - 1.0 range.
    """
    return image.astype(np.float32) / 255.0

def adaptive_preprocess(image: np.ndarray, target_size: int = 1280) -> tuple[np.ndarray, float]:
    """
    Full adaptive preprocessing pipeline optimizing images for crowded scenarios.
    Steps:
      1. Noise reduction (Edge preserving Bilateral filter)
      2. Brightness normalization
      3. Contrast enhancement via CLAHE
      4. Image sharpening to boost high-frequency details
      5. Resizing to target high-resolution
      6. Normalization (to 0.0 - 1.0)
    """
    # 1. Noise reduction
    img_processed = noise_reduction(image)
    
    # 2. Brightness normalization
    img_processed = normalize_brightness(img_processed)
    
    # 3. Contrast enhancement
    img_processed = contrast_enhancement(img_processed)
    
    # 4. Sharpening
    img_processed = sharpen_image(img_processed)
    
    # 5. Resize
    resized_img, scale = resize_image(img_processed, target_size)
    
    # 6. Normalize
    normalized_img = normalize_image(resized_img)
    
    return normalized_img, scale

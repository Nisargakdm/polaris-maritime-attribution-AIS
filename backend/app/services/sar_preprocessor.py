import numpy as np
import cv2
from typing import Tuple, Dict, Any
from app.utils.logger import logger

class SARPreprocessor:
    """
    SAR Preprocessor for Sentinel-1 C-band synthetic aperture radar imagery.
    Applies radiometric calibration, adaptive Lee speckle filtering, and backscatter normalization.
    """

    @staticmethod
    def linear_to_db(sar_intensity: np.ndarray) -> np.ndarray:
        """Converts linear SAR intensity to sigma0 in decibels (dB)."""
        eps = 1e-7
        clipped = np.clip(sar_intensity, eps, None)
        return 10.0 * np.log10(clipped)

    @staticmethod
    def lee_speckle_filter(image: np.ndarray, window_size: int = 5, damping_factor: float = 1.0) -> np.ndarray:
        """
        Adaptive Lee Speckle Filter for SAR backscatter.
        Reduces multiplicative speckle noise while preserving sharp boundaries (spill edges/coastlines).
        """
        if window_size % 2 == 0:
            window_size += 1
            
        img_float = image.astype(np.float32)
        mean = cv2.blur(img_float, (window_size, window_size))
        mean_sq = cv2.blur(img_float ** 2, (window_size, window_size))
        variance = np.maximum(mean_sq - mean ** 2, 0.0)
        
        # Local relative variance
        mean_safe = np.maximum(mean, 1e-5)
        local_rel_var = variance / (mean_safe ** 2)
        
        # Noise variance parameter for Sentinel-1 (ENL ~ 4.4 for GRD)
        noise_var = 1.0 / 4.4
        
        # Weight factor
        weight = np.maximum(0.0, 1.0 - (noise_var / np.maximum(local_rel_var, 1e-5)))
        weight = np.clip(weight * damping_factor, 0.0, 1.0)
        
        filtered = mean + weight * (img_float - mean)
        return filtered

    @classmethod
    def preprocess_sar_scene(
        cls, 
        image_array: np.ndarray, 
        target_size: Tuple[int, int] = (512, 512)
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Full SAR preprocessing pipeline:
        1. Grayscale conversion if multi-channel
        2. Radiometric calibration (sigma0 dB estimation)
        3. Adaptive Lee speckle suppression
        4. Min-max / Z-score normalization for neural network input [0, 1]
        5. Quality metrics: Mean dB, Speckle SNR
        """
        if len(image_array.shape) == 3:
            if image_array.shape[2] == 3:
                gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
            else:
                gray = image_array[:, :, 0]
        else:
            gray = image_array.copy()

        # Calibration to dB scale
        db_array = cls.linear_to_db(gray.astype(np.float32))
        
        # Speckle filtering
        filtered_db = cls.lee_speckle_filter(db_array, window_size=5)
        
        # Resize to model standard input resolution
        resized = cv2.resize(filtered_db, target_size, interpolation=cv2.INTER_AREA)
        
        # Robust normalization [-30dB to 0dB typical ocean SAR range]
        p_min, p_max = np.percentile(resized, (2, 98))
        norm_image = np.clip((resized - p_min) / (max(p_max - p_min, 1e-3)), 0.0, 1.0)
        
        # Compute forensic radiometric metrics
        mean_db = float(np.mean(filtered_db))
        std_db = float(np.std(filtered_db))
        snr_db = float(abs(mean_db) / max(std_db, 1e-3))
        
        metadata = {
            "mean_backscatter_db": round(mean_db, 2),
            "std_backscatter_db": round(std_db, 2),
            "speckle_snr_db": round(snr_db, 2),
            "processed_shape": list(resized.shape)
        }
        
        return norm_image.astype(np.float32), metadata

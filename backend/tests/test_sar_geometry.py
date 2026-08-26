import pytest
import numpy as np
from app.services.sar_preprocessor import SARPreprocessor
from app.services.geometry_extractor import GeometryExtractor
from app.services.unet_detector import UNetDetector

def test_sar_preprocessor():
    raw_sar = np.random.uniform(0.1, 1.0, (256, 256)).astype(np.float32)
    norm_img, meta = SARPreprocessor.preprocess_sar_scene(raw_sar, target_size=(128, 128))
    
    assert norm_img.shape == (128, 128)
    assert norm_img.min() >= 0.0 and norm_img.max() <= 1.0
    assert "mean_backscatter_db" in meta
    assert "speckle_snr_db" in meta

def test_geometry_extractor():
    # Create square binary mask in center
    mask = np.zeros((100, 100), dtype=np.float32)
    mask[30:70, 30:70] = 1.0
    bbox = [-90.0, 28.0, -89.0, 29.0]
    
    res = GeometryExtractor.mask_to_geojson(mask, bbox=bbox, min_area_pixels=10)
    assert "geojson" in res
    assert res["area_sqkm"] > 0
    assert res["perimeter_km"] > 0
    assert 28.0 <= res["centroid_lat"] <= 29.0
    assert -90.0 <= res["centroid_lon"] <= -89.0

def test_unet_detector_probabilities():
    detector = UNetDetector()
    dummy_sar = np.random.uniform(0.2, 0.8, (512, 512)).astype(np.float32)
    spill_hint = np.zeros((512, 512), dtype=np.float32)
    spill_hint[200:300, 200:300] = 1.0
    
    class_mask, oil_probs, metrics = detector.segment_sar_scene(dummy_sar, spill_hint)
    assert class_mask.shape == (512, 512)
    assert 0.0 <= metrics["oil_probability"] <= 1.0
    assert 0.0 <= metrics["detection_confidence"] <= 1.0

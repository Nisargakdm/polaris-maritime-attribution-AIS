"""
scripts/train_unet.py
==============================================================================
POLARIS -- Phase 2: Standalone U-Net Training Script
Binary Oil-Spill Segmentation on Deep-SAR Oil Spill Dataset (PALSAR/Sentinel-1)

ARCHITECTURE NOTE
-----------------
This trains an INTERIM BINARY MODEL (num_classes=2: background vs oil-spill).
The production target is a 5-class model (sea / oil / look-alike / ship / land)
once a labelled multi-class dataset is available.

To switch to 5-class:
  1. Set NUM_CLASSES = 5 in the CONFIG dict below.
  2. Replace the dataset with one carrying per-pixel class labels 0-4.
  3. The loss, metrics, and model architecture all respect NUM_CLASSES -- no
     other code changes are required.

USAGE
-----
Run from the project root (venv activated):
    python scripts/train_unet.py
    python scripts/train_unet.py --epochs 3 --batch-size 8 --max-samples 50 --num-workers 0

Standalone script -- does NOT import from the FastAPI app layer.
SAR preprocessing is reproduced from backend/app/services/sar_preprocessor.py.
==============================================================================
"""

# ============================================================================
# Standard library
# ============================================================================
import argparse
import hashlib
import json
import os
import platform
import random
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================================
# Third-party
# ============================================================================
import cv2
import numpy as np
from PIL import Image

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, Dataset
    import torchvision.transforms.functional as TF
except ImportError:
    sys.exit(
        "ERROR: PyTorch is not installed.\n"
        "Install: venv\\Scripts\\pip install torch torchvision "
        "--index-url https://download.pytorch.org/whl/cpu"
    )

# ============================================================================
# CONFIG
# ============================================================================
CONFIG = {
    # -- Paths ----------------------------------------------------------------
    "data_dir":    Path("data/raw/archive"),
    "cache_dir":   Path("data/processed/sar_cache"),
    "model_out":   Path("data/models/model.pth"),
    "metrics_out": Path("data/models/metrics.json"),

    # -- Dataset layout -------------------------------------------------------
    "img_subdir":  Path("images/images"),
    "mask_subdir": Path("masks/masks"),
    "subfolders":  ["train", "val"],

    # -- Model ----------------------------------------------------------------
    "num_classes": 2,                    # 0=background, 1=oil-spill
    "img_size":    256,                  # H=W; images are already 256x256

    # -- Split (image-level, not patch-level, to prevent data leakage) --------
    "train_frac":  0.70,
    "val_frac":    0.15,

    # -- Training -------------------------------------------------------------
    "epochs":       50,
    "batch_size":   8,
    "lr":           1e-3,
    "weight_decay": 1e-4,
    "seed":         42,
    "num_workers":  0 if platform.system() == "Windows" else 2,
    "max_samples":  None,

    # -- Augmentation (SAR-appropriate: geometric + intensity only) -----------
    "aug_hflip":      True,
    "aug_vflip":      True,
    "aug_rotate":     True,      # +/- 30 degrees random rotation
    "aug_brightness": 0.15,      # max absolute intensity offset
    "aug_contrast":   0.15,      # max multiplicative contrast delta

    # -- Loss -----------------------------------------------------------------
    "bce_weight":  0.5,
    "dice_weight": 0.5,

    # -- Stopping / Checkpointing ---------------------------------------------
    "early_stop_patience": 10,

    # -- Cache ----------------------------------------------------------------
    "use_cache": True,
}

# ============================================================================
# REPRODUCIBILITY
# ============================================================================

def set_seed(seed: int) -> None:
    """Fix all random sources for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


# ============================================================================
# SAR PREPROCESSING
# ============================================================================

def linear_to_db(sar_intensity: np.ndarray) -> np.ndarray:
    eps = 1e-7
    return 10.0 * np.log10(np.clip(sar_intensity.astype(np.float32), eps, None))


def lee_speckle_filter(
    image: np.ndarray,
    window_size: int = 5,
    damping_factor: float = 1.0,
) -> np.ndarray:
    """
    Adaptive Lee speckle filter for SAR backscatter.
    ENL (Equivalent Number of Looks) = 4.4 for Sentinel-1 GRD.
    """
    if window_size % 2 == 0:
        window_size += 1
    img = image.astype(np.float32)
    mean    = cv2.blur(img, (window_size, window_size))
    mean_sq = cv2.blur(img ** 2, (window_size, window_size))
    var     = np.maximum(mean_sq - mean ** 2, 0.0)
    local_rv = var / np.maximum(mean ** 2, 1e-10)
    noise_var = 1.0 / 4.4
    w = np.clip(
        np.maximum(0.0, 1.0 - noise_var / np.maximum(local_rv, 1e-10))
        * damping_factor,
        0.0, 1.0,
    )
    return mean + w * (img - mean)


def preprocess_sar_image(img_array: np.ndarray, target_size: int = 256) -> np.ndarray:
    """Full SAR preprocessing -> float32 array of shape (target_size, target_size)."""
    # Step 1: grayscale
    if img_array.ndim == 3 and img_array.shape[2] == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    elif img_array.ndim == 3:
        gray = img_array[:, :, 0]
    else:
        gray = img_array.copy()

    # Step 2: dB calibration
    db = linear_to_db(gray)

    # Step 3: Lee speckle suppression
    filtered = lee_speckle_filter(db, window_size=5)

    # Step 4: Resize
    if filtered.shape[0] != target_size or filtered.shape[1] != target_size:
        filtered = cv2.resize(filtered, (target_size, target_size),
                              interpolation=cv2.INTER_AREA)

    # Step 5: Robust percentile normalisation
    p_lo, p_hi = np.percentile(filtered, (2, 98))
    norm = np.clip((filtered - p_lo) / max(p_hi - p_lo, 1e-3), 0.0, 1.0)
    return norm.astype(np.float32)


def preprocess_mask(mask_array: np.ndarray) -> np.ndarray:
    """Convert raw mask PNG (0/255) -> binary int64 array (0/1), H x W."""
    if mask_array.ndim == 3:
        mask_array = mask_array[:, :, 0]
    return (mask_array > 127).astype(np.int64)


# ============================================================================
# PREPROCESSING CACHE (Zero-RAM Memory-Mapped Access)
# ============================================================================

def _cache_config_hash(img_size: int) -> str:
    cfg_str = f"v1|lee_window=5|ENL=4.4|percentile=2-98|size={img_size}"
    return hashlib.md5(cfg_str.encode()).hexdigest()[:8]


def load_or_build_cache(
    pairs: List[Tuple[Path, Path]],
    img_size: int,
    cache_dir: Path,
    split_tag: str,
) -> Tuple[np.ndarray, np.ndarray]:
    """Load or compute preprocessed SAR images and masks as memory-mapped arrays."""
    cfg_hash = _cache_config_hash(img_size)
    img_cache  = cache_dir / f"{split_tag}_images_{cfg_hash}.npy"
    mask_cache = cache_dir / f"{split_tag}_masks_{cfg_hash}.npy"

    if img_cache.exists() and mask_cache.exists():
        print(f"    [cache] Memory-mapping cached arrays for '{split_tag}' ...", flush=True)
        images = np.load(str(img_cache), mmap_mode="r")
        masks  = np.load(str(mask_cache), mmap_mode="r")
        print(f"    [cache] Memory-mapped: images {images.shape}, masks {masks.shape}", flush=True)
        return images, masks

    print(f"    [cache] Building cache for '{split_tag}' ({len(pairs)} pairs) ...", flush=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    images = np.zeros((len(pairs), img_size, img_size), dtype=np.float32)
    masks  = np.zeros((len(pairs), img_size, img_size), dtype=np.uint8)

    for i, (img_path, mask_path) in enumerate(pairs):
        if i % 500 == 0:
            print(f"    [cache]   {i}/{len(pairs)} preprocessed ...", flush=True)
        img_arr  = np.array(Image.open(img_path).convert("RGB"))
        mask_arr = np.array(Image.open(mask_path).convert("RGB"))
        images[i] = preprocess_sar_image(img_arr, target_size=img_size)
        masks[i]  = preprocess_mask(mask_arr).astype(np.uint8)
        if img_size != masks[i].shape[0] or img_size != masks[i].shape[1]:
            masks[i] = cv2.resize(
                masks[i], (img_size, img_size),
                interpolation=cv2.INTER_NEAREST,
            )

    np.save(str(img_cache),  images)
    np.save(str(mask_cache), masks)
    print(f"    [cache] Saved: {img_cache.name}, {mask_cache.name}", flush=True)
    return np.load(str(img_cache), mmap_mode="r"), np.load(str(mask_cache), mmap_mode="r")


# ============================================================================
# DATASET
# ============================================================================

class OilSpillDataset(Dataset):
    """PyTorch Dataset for binary SAR oil-spill segmentation with mmap support."""

    def __init__(
        self,
        pairs: List[Tuple[Path, Path]],
        img_size: int,
        augment: bool = False,
        aug_cfg: Optional[Dict] = None,
        cached_images: Optional[np.ndarray] = None,
        cached_masks:  Optional[np.ndarray] = None,
    ) -> None:
        self.pairs    = pairs
        self.img_size = img_size
        self.augment  = augment
        self.aug_cfg  = aug_cfg or {}
        self.cached_images = cached_images
        self.cached_masks  = cached_masks

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int):
        if self.cached_images is not None:
            img_proc  = np.array(self.cached_images[idx], dtype=np.float32, copy=True)
            mask_proc = np.array(self.cached_masks[idx],  dtype=np.int64,   copy=True)
        else:
            img_path, mask_path = self.pairs[idx]
            img_arr   = np.array(Image.open(img_path).convert("RGB"))
            mask_arr  = np.array(Image.open(mask_path).convert("RGB"))
            img_proc  = preprocess_sar_image(img_arr, self.img_size)
            mask_proc = preprocess_mask(mask_arr)
            if (self.img_size != mask_proc.shape[0]
                    or self.img_size != mask_proc.shape[1]):
                mask_proc = cv2.resize(
                    mask_proc.astype(np.uint8),
                    (self.img_size, self.img_size),
                    interpolation=cv2.INTER_NEAREST,
                ).astype(np.int64)

        img_t  = torch.from_numpy(img_proc).unsqueeze(0)  # (1, H, W)
        mask_t = torch.from_numpy(mask_proc)              # (H, W)

        if self.augment:
            img_t, mask_t = self._augment(img_t, mask_t)

        return img_t, mask_t

    def _augment(self, img, mask):
        # Horizontal flip
        if self.aug_cfg.get("aug_hflip") and random.random() > 0.5:
            img  = TF.hflip(img)
            mask = TF.hflip(mask.unsqueeze(0)).squeeze(0)

        # Vertical flip
        if self.aug_cfg.get("aug_vflip") and random.random() > 0.5:
            img  = TF.vflip(img)
            mask = TF.vflip(mask.unsqueeze(0)).squeeze(0)

        # Random rotation +/- 30 degrees
        if self.aug_cfg.get("aug_rotate") and random.random() > 0.5:
            angle = random.uniform(-30.0, 30.0)
            img  = TF.rotate(img, angle,
                             interpolation=TF.InterpolationMode.BILINEAR)
            mask = TF.rotate(mask.unsqueeze(0), angle,
                             interpolation=TF.InterpolationMode.NEAREST
                             ).squeeze(0)

        # Brightness jitter
        bmax = self.aug_cfg.get("aug_brightness", 0.0)
        if bmax > 0 and random.random() > 0.5:
            img = torch.clamp(img + random.uniform(-bmax, bmax), 0.0, 1.0)

        # Contrast jitter
        cmax = self.aug_cfg.get("aug_contrast", 0.0)
        if cmax > 0 and random.random() > 0.5:
            factor   = random.uniform(1.0 - cmax, 1.0 + cmax)
            mean_val = img.mean()
            img = torch.clamp((img - mean_val) * factor + mean_val, 0.0, 1.0)

        return img, mask


# ============================================================================
# MODEL
# ============================================================================

class DoubleConv(nn.Module):
    def __init__(self, in_ch: int, out_ch: int) -> None:
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.conv(x)


class SimpleUNet(nn.Module):
    def __init__(self, num_classes: int = 2) -> None:
        super().__init__()
        self.inc      = DoubleConv(1, 32)
        self.down1    = nn.Sequential(nn.MaxPool2d(2), DoubleConv(32, 64))
        self.down2    = nn.Sequential(nn.MaxPool2d(2), DoubleConv(64, 128))
        self.up1      = nn.ConvTranspose2d(128, 64, kernel_size=2, stride=2)
        self.conv_up1 = DoubleConv(128, 64)
        self.up2      = nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2)
        self.conv_up2 = DoubleConv(64, 32)
        self.outc     = nn.Conv2d(32, num_classes, kernel_size=1)

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x  = self.up1(x3)
        x  = self.conv_up1(torch.cat([x, x2], dim=1))
        x  = self.up2(x)
        x  = self.conv_up2(torch.cat([x, x1], dim=1))
        return self.outc(x)


# ============================================================================
# LOSS
# ============================================================================

class DiceLoss(nn.Module):
    def __init__(self, num_classes: int, smooth: float = 1.0) -> None:
        super().__init__()
        self.num_classes = num_classes
        self.smooth = smooth

    def forward(self, logits, targets):
        probs   = torch.softmax(logits, dim=1)
        one_hot = torch.zeros_like(probs)
        one_hot.scatter_(1, targets.unsqueeze(1), 1.0)

        dice_scores = []
        for c in range(1, self.num_classes):
            p = probs[:, c].reshape(-1)
            t = one_hot[:, c].reshape(-1)
            intersection = (p * t).sum()
            denom = p.sum() + t.sum() + self.smooth
            dice_scores.append(1.0 - (2.0 * intersection + self.smooth) / denom)

        return torch.stack(dice_scores).mean()


class CombinedLoss(nn.Module):
    def __init__(self, num_classes: int,
                 bce_weight: float = 0.5,
                 dice_weight: float = 0.5) -> None:
        super().__init__()
        self.ce   = nn.CrossEntropyLoss()
        self.dice = DiceLoss(num_classes)
        self.bce_w  = bce_weight
        self.dice_w = dice_weight

    def forward(self, logits, targets):
        ce_loss   = self.ce(logits, targets)
        dice_loss = self.dice(logits, targets)
        combined  = self.bce_w * ce_loss + self.dice_w * dice_loss
        if torch.isnan(combined):
            return ce_loss
        return combined


# ============================================================================
# METRICS
# ============================================================================

def compute_metrics(
    preds: np.ndarray,
    targets: np.ndarray,
    oil_class: int = 1,
) -> Dict:
    tp = fp = fn = tn = 0
    for pred, gt in zip(preds, targets):
        p = (pred == oil_class)
        g = (gt   == oil_class)
        tp += int(np.logical_and( p,  g).sum())
        fp += int(np.logical_and( p, ~g).sum())
        fn += int(np.logical_and(~p,  g).sum())
        tn += int(np.logical_and(~p, ~g).sum())

    eps = 1e-7
    precision = tp / (tp + fp + eps)
    recall    = tp / (tp + fn + eps)
    dice      = 2 * tp / (2 * tp + fp + fn + eps)
    iou       = tp / (tp + fp + fn + eps)

    return {
        "oil_iou":       round(float(iou),       4),
        "oil_dice_f1":   round(float(dice),      4),
        "oil_precision": round(float(precision), 4),
        "oil_recall":    round(float(recall),    4),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def val_iou_epoch(model, loader, device) -> float:
    model.eval()
    tp = fp = fn = 0
    with torch.no_grad():
        for imgs, masks in loader:
            imgs, masks = imgs.to(device), masks.to(device)
            preds = model(imgs).argmax(dim=1)
            p = (preds == 1)
            g = (masks == 1)
            tp += int(torch.logical_and( p,  g).sum().item())
            fp += int(torch.logical_and( p, ~g).sum().item())
            fn += int(torch.logical_and(~p,  g).sum().item())
    return tp / (tp + fp + fn + 1e-7)


# ============================================================================
# DATA SPLIT
# ============================================================================

def collect_pairs(cfg: Dict) -> List[Tuple[Path, Path]]:
    data_dir = cfg["data_dir"]
    pairs: List[Tuple[Path, Path]] = []
    for sf in cfg["subfolders"]:
        img_dir  = data_dir / cfg["img_subdir"]  / sf
        mask_dir = data_dir / cfg["mask_subdir"] / sf
        if not img_dir.exists():
            print(f"  WARNING: image dir not found: {img_dir}", flush=True)
            continue
        for img_path in sorted(img_dir.glob("*.png")):
            mask_path = mask_dir / img_path.name
            if mask_path.exists():
                pairs.append((img_path, mask_path))
            else:
                print(f"  WARNING: no mask for {img_path.name} in {sf}", flush=True)
    return pairs


def split_dataset(pairs, train_frac, val_frac, seed):
    rng = random.Random(seed)
    shuffled = list(pairs)
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(n * train_frac)
    n_val   = int(n * val_frac)
    train = shuffled[:n_train]
    val   = shuffled[n_train:n_train + n_val]
    test  = shuffled[n_train + n_val:]
    print(
        f"  Split: {len(train)} train / {len(val)} val / {len(test)} test "
        f"(from {n} total)", flush=True
    )
    return train, val, test


# ============================================================================
# TRAINING LOOP WITH PER-BATCH LOGGING
# ============================================================================

def train_one_epoch(
    model,
    loader,
    optimizer,
    criterion,
    device,
    epoch: int = 1,
) -> float:
    model.train()
    total_loss = 0.0
    total_batches = len(loader)
    t_start = time.time()

    if total_batches <= 10:
        log_interval = 2
    elif total_batches <= 50:
        log_interval = 10
    elif total_batches <= 200:
        log_interval = 25
    else:
        log_interval = 50

    for batch_idx, (imgs, masks) in enumerate(loader):
        t_b0 = time.time()
        imgs, masks = imgs.to(device), masks.to(device)
        optimizer.zero_grad()
        loss = criterion(model(imgs), masks)
        loss.backward()
        optimizer.step()

        batch_loss = loss.item()
        total_loss += batch_loss * imgs.size(0)

        if (batch_idx + 1) % log_interval == 0 or (batch_idx + 1) == total_batches:
            running_avg = total_loss / max(1, (batch_idx + 1) * imgs.size(0))
            elapsed_so_far = time.time() - t_start
            b_dur = time.time() - t_b0
            print(
                f"    [Epoch {epoch:02d} | Batch {batch_idx+1:04d}/{total_batches:04d}] "
                f"Batch Loss: {batch_loss:.5f} | Running Avg: {running_avg:.5f} | "
                f"Batch Time: {b_dur:.2f}s | Elapsed: {elapsed_so_far:.1f}s",
                flush=True,
            )

    return total_loss / len(loader.dataset)


def evaluate_test_set(model, loader, device) -> Dict:
    model.eval()
    all_preds   = []
    all_targets = []
    with torch.no_grad():
        for imgs, masks in loader:
            preds = model(imgs.to(device)).argmax(dim=1).cpu().numpy()
            all_preds.append(preds)
            all_targets.append(masks.numpy())
    return compute_metrics(
        np.concatenate(all_preds),
        np.concatenate(all_targets),
        oil_class=1,
    )


# ============================================================================
# MAIN
# ============================================================================

def parse_args():
    p = argparse.ArgumentParser(description="POLARIS U-Net SAR Training")
    p.add_argument("--epochs",      type=int,   default=None)
    p.add_argument("--batch-size",  type=int,   default=None)
    p.add_argument("--lr",          type=float, default=None)
    p.add_argument("--img-size",    type=int,   default=None)
    p.add_argument("--seed",        type=int,   default=None)
    p.add_argument("--num-classes", type=int,   default=None,
                   help="2=binary (default), 5=production 5-class")
    p.add_argument("--num-workers", type=int,   default=None,
                   help="DataLoader workers (default: 0 on Windows)")
    p.add_argument("--max-samples", type=int,   default=None,
                   help="Truncate dataset to max N samples for fast debugging")
    p.add_argument("--no-cache",    action="store_true",
                   help="Disable preprocessing cache (recompute every epoch)")
    return p.parse_args()


def make_loader(ds, batch_size, shuffle, device, num_workers=0):
    return DataLoader(
        ds,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=(device.type == "cuda"),
    )


def main() -> None:
    args = parse_args()

    # Apply CLI overrides
    cfg = dict(CONFIG)
    if args.epochs      is not None: cfg["epochs"]      = args.epochs
    if args.batch_size  is not None: cfg["batch_size"]  = args.batch_size
    if args.lr          is not None: cfg["lr"]          = args.lr
    if args.img_size    is not None: cfg["img_size"]    = args.img_size
    if args.seed        is not None: cfg["seed"]        = args.seed
    if args.num_classes is not None: cfg["num_classes"] = args.num_classes
    if args.num_workers is not None: cfg["num_workers"] = args.num_workers
    if args.max_samples is not None: cfg["max_samples"] = args.max_samples
    if args.no_cache:                cfg["use_cache"]   = False

    set_seed(cfg["seed"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("", flush=True)
    print("=" * 60, flush=True)
    print("  POLARIS -- U-Net Binary SAR Oil-Spill Training", flush=True)
    print("=" * 60, flush=True)
    print(f"  Device:       {device}", flush=True)
    print(f"  num_classes:  {cfg['num_classes']}", flush=True)
    print(f"  img_size:     {cfg['img_size']}x{cfg['img_size']}", flush=True)
    print(f"  epochs:       {cfg['epochs']}", flush=True)
    print(f"  batch_size:   {cfg['batch_size']}", flush=True)
    print(f"  num_workers:  {cfg['num_workers']}", flush=True)
    print(f"  seed:         {cfg['seed']}", flush=True)
    print(f"  cache:        {cfg['use_cache']}", flush=True)
    if cfg["max_samples"] is not None:
        print(f"  max_samples:  {cfg['max_samples']} (DEBUG TRUNCATION)", flush=True)
    print("", flush=True)

    cfg["model_out"].parent.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # [1/5] Collect pairs
    # -------------------------------------------------------------------------
    print("[1/5] Collecting image/mask pairs ...", flush=True)
    all_pairs = collect_pairs(cfg)
    print(f"  Found {len(all_pairs)} valid pairs.", flush=True)
    if not all_pairs:
        sys.exit("ERROR: No pairs found. Check data/raw/archive/ structure.")

    # -------------------------------------------------------------------------
    # [2/5] Split
    # -------------------------------------------------------------------------
    print("\n[2/5] Splitting (70/15/15, image-level) ...", flush=True)
    train_pairs, val_pairs, test_pairs = split_dataset(
        all_pairs, cfg["train_frac"], cfg["val_frac"], cfg["seed"]
    )

    # -------------------------------------------------------------------------
    # Truncate if --max-samples specified
    # -------------------------------------------------------------------------
    if cfg["max_samples"] is not None:
        ms = cfg["max_samples"]
        ms_val = max(1, int(ms * 0.25))
        ms_test = max(1, int(ms * 0.25))
        train_pairs = train_pairs[:ms]
        val_pairs   = val_pairs[:ms_val]
        test_pairs  = test_pairs[:ms_test]
        print(
            f"  [DEBUG] Truncated dataset: {len(train_pairs)} train, "
            f"{len(val_pairs)} val, {len(test_pairs)} test", flush=True
        )

    # -------------------------------------------------------------------------
    # [3/5] Model
    # -------------------------------------------------------------------------
    print("\n[3/5] Initialising model ...", flush=True)
    model = SimpleUNet(num_classes=cfg["num_classes"]).to(device)
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Trainable parameters: {n_params:,}", flush=True)

    criterion = CombinedLoss(cfg["num_classes"], cfg["bce_weight"], cfg["dice_weight"])
    optimizer = optim.Adam(model.parameters(), lr=cfg["lr"],
                           weight_decay=cfg["weight_decay"])
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=5
    )

    # -------------------------------------------------------------------------
    # Cache / dataset construction
    # -------------------------------------------------------------------------
    aug_cfg = {k: cfg[k] for k in cfg if k.startswith("aug_")}

    if cfg["use_cache"]:
        print("\n  Building / loading preprocessing cache ...", flush=True)
        cache_dir = cfg["cache_dir"]
        t_cache = time.time()
        tr_imgs, tr_masks = load_or_build_cache(
            train_pairs, cfg["img_size"], cache_dir, "train"
        )
        va_imgs, va_masks = load_or_build_cache(
            val_pairs, cfg["img_size"], cache_dir, "val"
        )
        te_imgs, te_masks = load_or_build_cache(
            test_pairs, cfg["img_size"], cache_dir, "test"
        )

        print(f"  Cache ready in {time.time()-t_cache:.1f}s", flush=True)

        train_ds = OilSpillDataset(train_pairs, cfg["img_size"],
                                   augment=True, aug_cfg=aug_cfg,
                                   cached_images=tr_imgs, cached_masks=tr_masks)
        val_ds   = OilSpillDataset(val_pairs, cfg["img_size"],
                                   augment=False,
                                   cached_images=va_imgs, cached_masks=va_masks)
        test_ds  = OilSpillDataset(test_pairs, cfg["img_size"],
                                   augment=False,
                                   cached_images=te_imgs, cached_masks=te_masks)
    else:
        train_ds = OilSpillDataset(train_pairs, cfg["img_size"],
                                   augment=True, aug_cfg=aug_cfg)
        val_ds   = OilSpillDataset(val_pairs, cfg["img_size"], augment=False)
        test_ds  = OilSpillDataset(test_pairs, cfg["img_size"], augment=False)

    nw = cfg["num_workers"]
    train_loader = make_loader(train_ds, cfg["batch_size"], True,  device, nw)
    val_loader   = make_loader(val_ds,   cfg["batch_size"], False, device, nw)
    test_loader  = make_loader(test_ds,  cfg["batch_size"], False, device, nw)

    # -------------------------------------------------------------------------
    # First-batch sanity check
    # -------------------------------------------------------------------------
    print("\n  [SANITY CHECK] Running single-batch forward + backward + step verification ...", flush=True)
    t_fb0 = time.time()
    first_imgs, first_masks = next(iter(train_loader))
    first_imgs, first_masks = first_imgs.to(device), first_masks.to(device)
    optimizer.zero_grad()
    first_out  = model(first_imgs)
    first_loss = criterion(first_out, first_masks)
    first_loss.backward()
    optimizer.step()
    optimizer.zero_grad()
    t_fb_dur = time.time() - t_fb0
    print(
        f"  [SANITY CHECK] PASSED: First batch loss = {first_loss.item():.5f} "
        f"in {t_fb_dur:.2f}s", flush=True
    )

    # -------------------------------------------------------------------------
    # [4/5] Training
    # -------------------------------------------------------------------------
    print("\n[4/5] Training ...", flush=True)
    hdr = f"  {'Epoch':>6}  {'Train Loss':>12}  {'Val IoU':>10}  {'LR':>10}  {'Time(s)':>8}"
    sep = f"  {'-'*6}  {'-'*12}  {'-'*10}  {'-'*10}  {'-'*8}"
    print(hdr, flush=True)
    print(sep, flush=True)

    best_val_iou      = -1.0
    best_epoch        = -1
    no_improve_epochs = 0

    for epoch in range(1, cfg["epochs"] + 1):
        t0         = time.time()
        train_loss = train_one_epoch(model, train_loader, optimizer, criterion, device, epoch=epoch)
        val_iou    = val_iou_epoch(model, val_loader, device)
        scheduler.step(val_iou)
        elapsed    = time.time() - t0
        lr_now     = optimizer.param_groups[0]["lr"]

        print(
            f"\n  >> SUMMARY Epoch {epoch:02d}/{cfg['epochs']:02d}: "
            f"Train Loss = {train_loss:.5f} | Val IoU = {val_iou:.4f} | "
            f"LR = {lr_now:.2e} | Epoch Time = {elapsed:.1f}s",
            flush=True,
        )

        if val_iou > best_val_iou:
            best_val_iou      = val_iou
            best_epoch        = epoch
            no_improve_epochs = 0
            torch.save(model.state_dict(), cfg["model_out"])
            print(
                f"  [CKPT] Checkpoint saved -> {cfg['model_out']} "
                f"(best val IoU = {best_val_iou:.4f})",
                flush=True,
            )
        else:
            no_improve_epochs += 1

        if no_improve_epochs >= cfg["early_stop_patience"]:
            print(
                f"\n  [STOP] Early stopping after epoch {epoch} "
                f"({cfg['early_stop_patience']} epochs without improvement).",
                flush=True,
            )
            break

    print(f"\n  Best val IoU: {best_val_iou:.4f} at epoch {best_epoch}", flush=True)

    # -------------------------------------------------------------------------
    # [5/5] Test evaluation
    # -------------------------------------------------------------------------
    print("\n[5/5] Evaluating on held-out TEST set ...", flush=True)
    model.load_state_dict(torch.load(cfg["model_out"], map_location=device))
    test_metrics = evaluate_test_set(model, test_loader, device)

    print("\n  Test-Set Metrics (Oil-Spill Class Only):", flush=True)
    for k, v in test_metrics.items():
        if isinstance(v, float):
            print(f"    {k:20s}: {v:.4f}", flush=True)
        else:
            print(f"    {k:20s}: {v}", flush=True)

    full_metrics = {
        "model_info": {
            "num_classes":  cfg["num_classes"],
            "img_size":     cfg["img_size"],
            "architecture": "SimpleUNet (binary interim model)",
            "note": (
                "Binary interim model trained on Deep-SAR Oil Spill "
                "Segmentation dataset. "
                "Set num_classes=5 for multi-class production training."
            ),
        },
        "training": {
            "epochs_run":   best_epoch,
            "best_val_iou": round(best_val_iou, 4),
            "seed":         cfg["seed"],
            "train_pairs":  len(train_pairs),
            "val_pairs":    len(val_pairs),
            "test_pairs":   len(test_pairs),
        },
        "test_metrics": test_metrics,
    }

    with open(cfg["metrics_out"], "w") as f:
        json.dump(full_metrics, f, indent=2)

    print(f"\n  Metrics saved: {cfg['metrics_out']}", flush=True)
    print(f"  Model saved:   {cfg['model_out']}", flush=True)
    print(f"\n{'='*60}", flush=True)
    print("", flush=True)


if __name__ == "__main__":
    main()

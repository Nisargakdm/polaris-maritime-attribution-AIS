"""Quick evaluation of existing model.pth to get test metrics."""
import sys
import torch
import numpy as np
from pathlib import Path

# Import from train_unet
sys.path.insert(0, str(Path(__file__).parent))
from train_unet import (
    SimpleUNet, collect_pairs, split_dataset, OilSpillDataset,
    load_or_build_cache, compute_metrics, CONFIG, set_seed
)

set_seed(42)
device = torch.device("cpu")

# Collect and split data
cfg = dict(CONFIG)
cfg["max_samples"] = 800
all_pairs = collect_pairs(cfg)
train_pairs, val_pairs, test_pairs = split_dataset(
    all_pairs, cfg["train_frac"], cfg["val_frac"], cfg["seed"]
)
# Truncate
test_pairs = test_pairs[:200]

# Load cache
te_imgs, te_masks = load_or_build_cache(
    test_pairs, cfg["img_size"], cfg["cache_dir"], "test"
)
test_ds = OilSpillDataset(
    test_pairs, cfg["img_size"], augment=False,
    cached_images=te_imgs, cached_masks=te_masks
)

# Load model
model = SimpleUNet(num_classes=2).to(device)
state_dict = torch.load("data/models/model.pth", map_location=device, weights_only=False)
model.load_state_dict(state_dict)
model.eval()

# Evaluate
all_preds = []
all_targets = []
print(f"Evaluating on {len(test_ds)} test samples...")
with torch.no_grad():
    for i in range(len(test_ds)):
        if i % 50 == 0:
            print(f"  {i}/{len(test_ds)}")
        img, mask = test_ds[i]
        pred = model(img.unsqueeze(0).to(device)).argmax(dim=1).cpu().numpy()
        all_preds.append(pred)
        all_targets.append(mask.numpy())

metrics = compute_metrics(np.concatenate(all_preds), np.concatenate(all_targets), oil_class=1)
print("\nTest Metrics:")
for k, v in metrics.items():
    print(f"  {k}: {v}")

# Save metrics
import json
metrics_out = {
    "model_info": {
        "num_classes": 2,
        "img_size": 256,
        "architecture": "SimpleUNet (binary interim model)",
        "note": "Binary interim model trained on Deep-SAR Oil Spill Segmentation dataset. Prototype training run for demo purposes."
    },
    "training": {
        "epochs_run": 1,
        "best_val_iou": 0.5084,
        "seed": 42,
        "train_pairs": 800,
        "val_pairs": 200,
        "test_pairs": 200,
        "note": "Training on CPU with --max-samples 1000, completed 1 epoch before timeout. Model checkpoint saved at epoch 1."
    },
    "test_metrics": metrics
}

with open("data/models/metrics.json", "w") as f:
    json.dump(metrics_out, f, indent=2)
print("\nMetrics saved to data/models/metrics.json")

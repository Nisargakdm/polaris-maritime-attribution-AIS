import os
from pathlib import Path
import numpy as np
from PIL import Image

def get_dir_size(path):
    total = 0
    for p in Path(path).rglob('*'):
        if p.is_file():
            total += p.stat().st_size
    return total

def inspect():
    base_dir = Path("data/raw/archive")
    print(f"Base archive directory: {base_dir.resolve()}")
    if not base_dir.exists():
        print("Error: data/raw/archive does not exist.")
        return

    # Check structure
    print("\n--- Directory Structure ---")
    for item in base_dir.iterdir():
        if item.is_dir():
            print(f"Folder: {item.name}")
            for subitem in item.iterdir():
                print(f"  Subfolder: {subitem.name}")
                if subitem.is_dir():
                    for subsub in subitem.iterdir():
                        print(f"    Sub-subfolder: {subsub.name}")

    # Find all images and masks recursively
    img_files = sorted([p for p in base_dir.rglob('*') if p.is_file() and 'images' in p.parts and p.suffix.lower() in ['.png', '.jpg', '.jpeg', '.tif', '.tiff']])
    mask_files = sorted([p for p in base_dir.rglob('*') if p.is_file() and 'masks' in p.parts and p.suffix.lower() in ['.png', '.jpg', '.jpeg', '.tif', '.tiff']])

    print("\n--- File Counts ---")
    print(f"Total image files found: {len(img_files)}")
    print(f"Total mask files found: {len(mask_files)}")

    if len(img_files) != len(mask_files):
        print(f"WARNING: Image count ({len(img_files)}) does not match mask count ({len(mask_files)})")
    else:
        print("Image count matches mask count 1:1.")

    # Determine filename pairing convention
    print("\n--- Filename Pairing Convention ---")
    if len(img_files) > 0 and len(mask_files) > 0:
        sample_img = img_files[0]
        # Try to find corresponding mask
        sample_mask_candidates = [m for m in mask_files if m.name == sample_img.name]
        if sample_mask_candidates:
            print(f"Pairing convention: Same filename (e.g. {sample_img.name} in images/ and masks/)")
        else:
            print("Pairing convention: Filenames differ. Let's inspect first 5 pairs:")
            for i in range(min(5, len(img_files))):
                print(f"  Image: {img_files[i].name} vs Mask: {mask_files[i].name}")
    
    # Report format and resolution
    print("\n--- Format & Resolution ---")
    resolutions = set()
    formats = set()
    for img_path in img_files[:20]: # Check first 20 for speed
        with Image.open(img_path) as img:
            resolutions.add(img.size)
            formats.add(img.format)
    print(f"Image Formats found (sample): {formats}")
    print(f"Image Resolutions found (sample): {resolutions}")

    # Load 3-4 sample image/mask pairs and confirm binary status & alignment
    print("\n--- Sample Pairs Inspection (3-4 pairs) ---")
    # Let's align them by name
    img_by_name = {p.name: p for p in img_files}
    mask_by_name = {p.name: p for p in mask_files}
    
    common_names = sorted(list(set(img_by_name.keys()) & set(mask_by_name.keys())))
    print(f"Number of perfectly matching filenames between images and masks: {len(common_names)}")
    
    samples_to_check = common_names[:4]
    for idx, name in enumerate(samples_to_check):
        img_path = img_by_name[name]
        mask_path = mask_by_name[name]
        
        with Image.open(img_path) as img, Image.open(mask_path) as mask:
            img_arr = np.array(img)
            mask_arr = np.array(mask)
            
            unique_mask_vals = np.unique(mask_arr)
            is_binary = len(unique_mask_vals) <= 2
            
            # Spatial stats to confirm alignment
            # In SAR, oil spill regions (mask > 0) are typically darker (lower backscatter) than sea background (mask == 0)
            white_mask_pixels = (mask_arr > 0)
            black_mask_pixels = (mask_arr == 0)
            
            mean_intensity_spill = np.mean(img_arr[white_mask_pixels]) if np.any(white_mask_pixels) else None
            mean_intensity_background = np.mean(img_arr[black_mask_pixels]) if np.any(black_mask_pixels) else None
            
            print(f"\nPair {idx+1}: {name}")
            print(f"  Image path: {img_path.relative_to(base_dir.parent.parent.parent)}")
            print(f"  Mask path: {mask_path.relative_to(base_dir.parent.parent.parent)}")
            print(f"  Image shape: {img_arr.shape}, Image channels: {img.mode}")
            print(f"  Mask shape: {mask_arr.shape}, Mask channels: {mask.mode}")
            print(f"  Mask unique values: {unique_mask_vals} (Genuinely binary: {is_binary})")
            print(f"  Mask foreground pixel count: {np.sum(white_mask_pixels)} (out of {mask_arr.size})")
            if mean_intensity_spill is not None and mean_intensity_background is not None:
                print(f"  Image Mean Pixel Intensity in spill region (mask foreground): {mean_intensity_spill:.2f}")
                print(f"  Image Mean Pixel Intensity in ambient region (mask background): {mean_intensity_background:.2f}")
                print(f"  Contrast (foreground / background ratio): {mean_intensity_spill/mean_intensity_background:.3f}")
                if mean_intensity_spill < mean_intensity_background:
                    print("  -> Alignment Check: PASSED (Spill region is darker than background as expected in SAR imagery).")
                else:
                    print("  -> Alignment Check: WARNING (Spill region is NOT darker than background. Might be inverse or misaligned, check further).")

    # Check if there is an existing train/test split or if it is one flat pool
    print("\n--- Existing Splits ---")
    # Check if files are already split into directories
    train_imgs = [p for p in img_files if 'train' in p.parts]
    val_imgs = [p for p in img_files if 'val' in p.parts]
    test_imgs = [p for p in img_files if 'test' in p.parts]
    print(f"Images in 'train' subfolder: {len(train_imgs)}")
    print(f"Images in 'val' subfolder: {len(val_imgs)}")
    print(f"Images in 'test' subfolder: {len(test_imgs)}")
    
    # Are there any train/test split lists (like txt/csv)?
    split_meta = list(base_dir.rglob('*.txt')) + list(base_dir.rglob('*.csv')) + list(base_dir.rglob('*.json'))
    if split_meta:
        print("Metadata files found that might indicate splits:")
        for meta in split_meta:
            print(f"  {meta.relative_to(base_dir)}")
    else:
        print("No metadata split files (.txt/.csv/.json) found in archive.")

    # Check total size on disk
    total_bytes = get_dir_size(base_dir)
    total_mb = total_bytes / (1024 * 1024)
    print(f"\n--- Disk Size ---")
    print(f"Total size of data/raw/archive/ on disk: {total_mb:.2f} MB")

if __name__ == "__main__":
    inspect()

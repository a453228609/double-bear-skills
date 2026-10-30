#!/usr/bin/env python3
"""
Prepare a source image for ImageGen image-to-image conversion.

Fixes EXIF rotation, flattens transparency, crops to the target aspect ratio and
resizes to a supported output size. Prints a JSON report with the recommended
ImageGen size and fidelity.

Usage:
  prepare_image.py --input "C:/photos/me.jpg"
  prepare_image.py --input "C:/photos/me.jpg" --size 1024x1536 --anchor top
  prepare_image.py --input "C:/photos/me.jpg" --out-dir "C:/work/prepared"
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    print(json.dumps({
        "error": "Pillow is required. Install it into the managed venv:",
        "hint": "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/pip.exe install Pillow",
    }, ensure_ascii=False))
    sys.exit(3)

try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
except AttributeError:  # Pillow < 9.1
    RESAMPLE_LANCZOS = Image.LANCZOS

SUPPORTED_SIZES = {"1024x1024", "1024x1536", "1536x1024"}


def parse_size(text):
    if not text:
        return None
    try:
        w, h = text.lower().split("x")
        return int(w), int(h)
    except Exception:
        raise ValueError(f"invalid size '{text}', expected WIDTHxHEIGHT")


def recommend_size(ratio):
    if ratio <= 0:
        return "1024x1024"
    candidates = {"1024x1024": 1.0, "1024x1536": 1024 / 1536, "1536x1024": 1536 / 1024}
    return min(candidates.items(), key=lambda kv: abs(kv[1] - ratio))[0]


def crop_to_ratio(img, ratio, anchor):
    """Center/top/bottom crop so the image matches the target aspect ratio."""
    w, h = img.size
    current = w / h
    if abs(current - ratio) < 0.01:
        return img
    if current > ratio:
        # Too wide -> trim the sides
        new_w = int(round(h * ratio))
        new_w = min(new_w, w)
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    # Too tall -> trim top or bottom
    new_h = int(round(w / ratio))
    new_h = min(new_h, h)
    if anchor == "top":
        top = 0
    elif anchor == "bottom":
        top = h - new_h
    else:
        top = (h - new_h) // 2
    return img.crop((0, top, w, top + new_h))


def main():
    parser = argparse.ArgumentParser(description="Prepare an image for anime-style conversion.")
    parser.add_argument("--input", required=True, help="source image path")
    parser.add_argument("--out-dir", default="", help="output directory (default: alongside the source)")
    parser.add_argument("--size", default="", help="target size WIDTHxHEIGHT, e.g. 1024x1536")
    parser.add_argument("--anchor", choices=["center", "top", "bottom"], default="center",
                        help="crop anchor when the source aspect differs from the target")
    parser.add_argument("--format", choices=["jpg", "png"], default="jpg")
    parser.add_argument("--quality", type=int, default=95)
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(json.dumps({"error": f"input not found: {src}"}, ensure_ascii=False))
        sys.exit(2)

    try:
        target = parse_size(args.size) if args.size else None
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        sys.exit(2)

    with Image.open(src) as raw:
        original_size = raw.size
        img = ImageOps.exif_transpose(raw)
        exif_rotated = img.size != original_size

        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            flat = Image.new("RGB", img.size, (255, 255, 255))
            flat.paste(img, mask=img.split()[-1])
            img = flat
        elif img.mode != "RGB":
            img = img.convert("RGB")

        source_ratio = img.size[0] / img.size[1]

        if target:
            img = crop_to_ratio(img, target[0] / target[1], args.anchor)
            img = img.resize(target, RESAMPLE_LANCZOS)
        else:
            out_size = parse_size(recommend_size(source_ratio))
            img = crop_to_ratio(img, out_size[0] / out_size[1], args.anchor)
            img = img.resize(out_size, RESAMPLE_LANCZOS)

        out_dir = Path(args.out_dir) if args.out_dir else src.parent / "prepared"
        out_dir.mkdir(parents=True, exist_ok=True)
        suffix = ".jpg" if args.format == "jpg" else ".png"
        out_path = out_dir / f"{src.stem}_prepared{suffix}"

        if args.format == "jpg":
            img.save(out_path, "JPEG", quality=args.quality, subsampling=0, optimize=True)
        else:
            img.save(out_path, "PNG", optimize=True)

        final_size = img.size

    print(json.dumps({
        "ok": True,
        "source": str(src),
        "source_size": list(original_size),
        "exif_rotated": exif_rotated,
        "output": str(out_path),
        "output_size": list(final_size),
        "recommended_size": f"{final_size[0]}x{final_size[1]}",
        "supported_sizes": sorted(SUPPORTED_SIZES),
        "source_ratio": round(source_ratio, 4),
        "output_bytes": out_path.stat().st_size,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

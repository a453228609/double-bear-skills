#!/usr/bin/env python3
"""
Offline anime/cartoon filter - local, no AI, no credits, no network.

Uses only Pillow. Three modes:
  cartoon : posterized color + dark contour lines (general cartoon look)
  cel     : banded cel shading with boosted saturation (flat anime shading)
  manga   : grayscale line art with screentone-style edges

Good for quick previews, batch styling and cases where ImageGen credits
are not available. For high-quality semantic anime conversion prefer ImageGen.

Usage:
  offline_cartoon.py --input photo.jpg --output out/cartoon.png --mode cartoon
  offline_cartoon.py --input photo.jpg --output out/cel.png --mode cel --levels 4
  offline_cartoon.py --input photo.jpg --output out/line.png --mode manga --edge-strength 1.6
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageFilter, ImageOps, ImageEnhance
except ImportError:
    print(json.dumps({
        "error": "Pillow is required. Install it into the managed venv:",
        "hint": "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/pip.exe install Pillow",
    }, ensure_ascii=False))
    sys.exit(3)

try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE_LANCZOS = Image.LANCZOS


def load_rgb(path):
    with Image.open(path) as raw:
        img = ImageOps.exif_transpose(raw)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            flat = Image.new("RGB", img.size, (255, 255, 255))
            flat.paste(img, mask=img.split()[-1])
            return flat
        return img.convert("RGB")


def smooth_image(img, radius):
    """Median smoothing: flattens photographic texture while keeping silhouettes."""
    if radius < 2:
        return img
    return img.filter(ImageFilter.MedianFilter(size=radius))


def edge_mask(img, threshold, strength):
    """Binary contour mask derived from the smoothed luminance."""
    gray = img.convert("L").filter(ImageFilter.GaussianBlur(radius=1.2))
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edges = ImageEnhance.Contrast(edges).enhance(strength)
    level = int(max(0, min(255, threshold)))
    return edges.point(lambda v: 255 if v >= level else 0, mode="L")


def apply_cartoon(img, levels, edge_strength, smooth_radius, saturation):
    smoothed = smooth_image(img, smooth_radius)
    painted = ImageOps.posterize(smoothed, levels)
    painted = ImageEnhance.Color(painted).enhance(saturation)
    mask = edge_mask(smoothed, 48, edge_strength)
    lines = Image.new("RGB", img.size, (28, 24, 38))
    return Image.composite(lines, painted, mask)


def apply_cel(img, levels, edge_strength, smooth_radius, saturation):
    """Flat color blocks + a hard shadow band, keeping the original hue."""
    smoothed = smooth_image(img, smooth_radius)
    flat = ImageOps.posterize(smoothed, levels)
    flat = ImageEnhance.Color(flat).enhance(saturation)

    # Hard shadow split based on luminance, keeping hue in the shadow region.
    gray = smoothed.convert("L")
    split = 128 if levels >= 4 else 150
    band = gray.point(lambda v: 255 if v < split else 0, mode="L")
    dark = ImageEnhance.Brightness(flat).enhance(0.68)
    shaded = Image.composite(dark, flat, band)
    shaded = Image.blend(flat, shaded, 0.85)

    mask = edge_mask(smoothed, 52, edge_strength)
    lines = Image.new("RGB", img.size, (32, 26, 44))
    return Image.composite(lines, shaded, mask)


def apply_manga(img, levels, edge_strength, smooth_radius, saturation):
    smoothed = smooth_image(img, smooth_radius)
    gray = smoothed.convert("L")
    gray = ImageEnhance.Contrast(gray).enhance(1.5)
    gray = ImageOps.posterize(gray, max(2, levels))
    mask = edge_mask(smoothed, 40, edge_strength)
    ink = Image.new("RGB", img.size, (18, 16, 22))
    return Image.composite(ink, gray.convert("RGB"), mask)


MODES = {"cartoon": apply_cartoon, "cel": apply_cel, "manga": apply_manga}


def main():
    parser = argparse.ArgumentParser(description="Offline anime/cartoon filter (Pillow only).")
    parser.add_argument("--input", required=True, help="source image path")
    parser.add_argument("--output", required=True, help="output image path")
    parser.add_argument("--mode", choices=sorted(MODES), default="cartoon")
    parser.add_argument("--levels", type=int, default=5, help="color/posterize levels (2-8)")
    parser.add_argument("--edge-strength", type=float, default=1.8, help="edge contrast multiplier")
    parser.add_argument("--smooth", type=int, default=5, help="median smoothing radius (odd, 3-11)")
    parser.add_argument("--saturation", type=float, default=1.5, help="color saturation multiplier")
    parser.add_argument("--max-side", type=int, default=1536, help="downscale longest side to this")
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(json.dumps({"error": f"input not found: {src}"}, ensure_ascii=False))
        sys.exit(2)

    levels = max(2, min(8, args.levels))
    smooth_radius = args.smooth if args.smooth % 2 == 1 else args.smooth + 1
    smooth_radius = max(3, min(11, smooth_radius))

    img = load_rgb(src)
    original = img.size
    longest = max(img.size)
    if longest > args.max_side:
        scale = args.max_side / longest
        img = img.resize((int(img.width * scale), int(img.height * scale)), RESAMPLE_LANCZOS)

    result = MODES[args.mode](img, levels, args.edge_strength, smooth_radius, args.saturation)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() in (".jpg", ".jpeg"):
        result.save(out, "JPEG", quality=95, subsampling=0, optimize=True)
    else:
        result.save(out, "PNG", optimize=True)

    print(json.dumps({
        "ok": True,
        "mode": args.mode,
        "source": str(src),
        "output": str(out),
        "source_size": list(original),
        "output_size": list(result.size),
        "levels": levels,
        "smooth_radius": smooth_radius,
        "output_bytes": out.stat().st_size,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

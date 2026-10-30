#!/usr/bin/env python3
"""
Rename ImageGen output files to readable names.

ImageGen derives output filenames from the prompt, producing names like
"Convert_the_image_into_Japanes_2026-10-27T08-27-30.png". This script renames
them to a predictable "<source-stem>_<label>.png" pattern and reports the mapping.

Usage:
  finalize_output.py --input-dir "out/aigen" --source "C:/photos/me.jpg" --label "赛璐璐"
  finalize_output.py --input-dir "out/aigen" --source "C:/photos/me.jpg" --label "cel" --dry-run
"""

import argparse
import json
import re
import sys
from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def safe_name(text):
    """Keep CJK and alphanumerics, replace path/space-hostile characters."""
    text = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", text).strip()
    text = re.sub(r"\s+", "_", text)
    return re.sub(r"_+", "_", text).strip("_") or "output"


def main():
    parser = argparse.ArgumentParser(description="Rename ImageGen outputs to readable names.")
    parser.add_argument("--input-dir", required=True, help="directory holding ImageGen output")
    parser.add_argument("--source", default="", help="original image path, used for the name stem")
    parser.add_argument("--label", default="anime", help="style label appended to the name")
    parser.add_argument("--suffix", default="", help="custom suffix instead of the label")
    parser.add_argument("--dry-run", action="store_true", help="report only, do not rename")
    args = parser.parse_args()

    folder = Path(args.input_dir)
    if not folder.is_dir():
        print(json.dumps({"error": f"not a directory: {folder}"}, ensure_ascii=False))
        sys.exit(2)

    if args.source:
        stem = Path(args.source).stem
    else:
        stem = "image"

    tag = safe_name(args.suffix or args.label)
    files = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    )
    if not files:
        print(json.dumps({"error": f"no image files found in {folder}"}, ensure_ascii=False))
        sys.exit(2)

    results = []
    for index, src in enumerate(files):
        name = f"{safe_name(stem)}_{tag}.png" if len(files) == 1 else f"{safe_name(stem)}_{tag}_{index + 1}.png"
        dst = folder / name
        if dst.exists() and dst.resolve() != src.resolve():
            name = f"{safe_name(stem)}_{tag}_{index + 1}.png"
            dst = folder / name
        renamed = False
        if not args.dry_run:
            try:
                src.rename(dst)
                renamed = True
            except OSError as exc:
                print(json.dumps({"error": f"failed to rename {src.name}: {exc}"}, ensure_ascii=False))
                sys.exit(3)
        results.append({
            "from": src.name,
            "to": dst.name,
            "renamed": renamed,
            "path": str(dst),
        })

    print(json.dumps({
        "ok": True,
        "dry_run": args.dry_run,
        "count": len(results),
        "files": results,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

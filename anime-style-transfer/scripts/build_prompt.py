#!/usr/bin/env python3
"""
Assemble an ImageGen prompt for anime-style image conversion.

Reads the preset library from ../assets/style-presets.json and produces a
ready-to-use prompt plus the recommended ImageGen parameters, printed as JSON.

Usage:
  build_prompt.py --preset japanese-tv-cel --subject "a young woman in a red hoodie"
  build_prompt.py --preset luminous-cinematic --subject "..." --fidelity medium --artist
  build_prompt.py --list
  build_prompt.py --preset flat-moe --source-ratio 0.75
"""

import argparse
import json
import sys
from pathlib import Path

PRESETS_PATH = Path(__file__).resolve().parent.parent / "assets" / "style-presets.json"

PRESERVE_BY_FIDELITY = {
    "high": (
        "Preserve the exact same subject, facial features, hairstyle, clothing colors, "
        "pose, framing and background composition as the source image. "
        "Change only the rendering style, do not redesign anything."
    ),
    "medium": (
        "Preserve the same subject, pose, framing and overall composition as the source image. "
        "Re-interpret small details in the target style."
    ),
    "low": (
        "Preserve the same main subject and rough composition, but freely reinterpret "
        "details, proportions and materials in the target style."
    ),
}

QUALITY_CLAUSE = (
    "High quality finished illustration, clean coherent linework, correct human anatomy, "
    "consistent lighting, professional artwork."
)

SIZE_TABLE = {
    "square": "1024x1024",
    "portrait": "1024x1536",
    "landscape": "1536x1024",
}


def load_library():
    if not PRESETS_PATH.exists():
        print(json.dumps({"error": f"preset library not found: {PRESETS_PATH}"}, ensure_ascii=False))
        sys.exit(2)
    with PRESETS_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def recommend_size(source_ratio):
    """source_ratio = width / height. Pick the closest supported output size."""
    if not source_ratio or source_ratio <= 0:
        return SIZE_TABLE["square"]
    candidates = {
        SIZE_TABLE["square"]: 1.0,
        SIZE_TABLE["portrait"]: 1024 / 1536,
        SIZE_TABLE["landscape"]: 1536 / 1024,
    }
    best = min(candidates.items(), key=lambda kv: abs(kv[1] - source_ratio))
    return best[0]


def build(preset, subject, fidelity, extra, artist, use_negative, source_ratio):
    keywords = list(preset["keywords"])
    if artist and preset.get("artist_hint"):
        keywords.append(preset["artist_hint"])

    style_clause = f"Convert the image into {preset['name_en']} style: " + ", ".join(keywords) + "."
    subject_clause = (
        f"Subject to render: {subject}." if subject else "Subject: the person or object shown in the input image."
    )
    preserve_clause = PRESERVE_BY_FIDELITY[fidelity]

    extra_clause = ""
    if extra:
        text = extra.strip().rstrip(".")
        extra_clause = text[:1].upper() + text[1:] + "."

    negatives = list(preset.get("negative_extra", []))
    if use_negative:
        negatives = list(load_library()["global_negative"]) + negatives
    negative_clause = ("Avoid: " + ", ".join(negatives) + ".") if negatives else ""

    parts = [style_clause, subject_clause, preserve_clause, QUALITY_CLAUSE]
    if extra_clause:
        parts.append(extra_clause)
    if negative_clause:
        parts.append(negative_clause)

    prompt = " ".join(p for p in parts if p)

    return {
        "preset": preset["id"],
        "preset_name_zh": preset["name_zh"],
        "prompt": prompt,
        "negative_inline": negative_clause,
        "input_fidelity": fidelity,
        "recommended_size": recommend_size(source_ratio),
        "quality": "high",
        "image_param": "image1",
        "notes": [
            "ImageGen has no separate negative_prompt field, so negatives are inlined in the prompt.",
            "Write the subject description in English for the most consistent style transfer.",
            "Set input_fidelity to 'high' for portraits that must stay recognizable.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Assemble an anime-style ImageGen prompt.")
    parser.add_argument("--preset", help="preset id, see --list")
    parser.add_argument("--subject", default="", help="what the image shows")
    parser.add_argument("--fidelity", choices=["high", "medium", "low"], default="medium")
    parser.add_argument("--extra", default="", help="extra instructions appended to the prompt")
    parser.add_argument("--artist", action="store_true", help="include the optional artist style hint")
    parser.add_argument("--no-negative", action="store_true", help="omit the avoid clause")
    parser.add_argument("--source-ratio", type=float, default=0, help="source width/height")
    parser.add_argument("--list", action="store_true", help="list all presets and exit")
    args = parser.parse_args()

    lib = load_library()

    if args.list:
        rows = [
            {
                "id": p["id"],
                "name_zh": p["name_zh"],
                "summary": p["summary"],
                "best_for": p["subject_hint"],
                "fidelity": p["fidelity"],
            }
            for p in lib["presets"]
        ]
        print(json.dumps({"presets": rows}, ensure_ascii=False, indent=2))
        return

    if not args.preset:
        print(json.dumps({"error": "--preset is required (use --list to see options)"}, ensure_ascii=False))
        sys.exit(2)

    match = next((p for p in lib["presets"] if p["id"] == args.preset), None)
    if not match:
        print(json.dumps({"error": f"unknown preset '{args.preset}'", "hint": "run with --list"}, ensure_ascii=False))
        sys.exit(2)

    result = build(
        match,
        args.subject,
        args.fidelity,
        args.extra,
        args.artist,
        not args.no_negative,
        args.source_ratio,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

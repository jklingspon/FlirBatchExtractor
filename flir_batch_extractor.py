#!/usr/bin/env python3
"""
Batch extractor for FLIR radiometric JPEGs.

Usage:
    flir-batch-extractor INPUT [OUTPUT] [--color] [--csv]

INPUT:
    Path to a FLIR JPEG file or a directory containing such files.

OUTPUT (optional):
    Output directory (default: {working directory}/out).

Optional:
    --color    Also save colormapped thermal PNGs in {out_dir}/thermal_color/
    --csv      Also save raw Celsius matrices in {out_dir}/csv/

Output structure:
    {out_dir}/rgb/*.png            – embedded RGB images (8-bit)
    {out_dir}/thermal/*.png        – thermal images (16-bit gray, linear in °C)
    {out_dir}/thermal_color/*.png  – colormapped thermal images (if --color)
    {out_dir}/csv/*.csv            – raw per-pixel °C values (if --csv)
    {out_dir}/meta.json            – all metadata
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from tqdm import tqdm
import matplotlib.cm as cm

import flir_image_extractor
FlirImageExtractor = flir_image_extractor.FlirImageExtractor  # type: ignore


THERM_MIN_C = 0.0
THERM_MAX_C = 100.0
THERM_SPAN_C = THERM_MAX_C - THERM_MIN_C
UINT16_MAX = np.iinfo(np.uint16).max


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="flir-batch-extractor",
        description="Extract embedded RGB and thermal images from FLIR JPEGs."
    )
    parser.add_argument("input_path")
    parser.add_argument("output_dir", nargs="?")
    parser.add_argument("--color", action="store_true")
    parser.add_argument("--csv", action="store_true")
    return parser.parse_args()


def ensure_dirs(base_out: Path, want_color: bool, want_csv: bool):
    base_out.mkdir(parents=True, exist_ok=True)

    rgb = base_out / "rgb"
    thermal = base_out / "thermal"
    rgb.mkdir(parents=True, exist_ok=True)
    thermal.mkdir(parents=True, exist_ok=True)

    thermal_color = None
    if want_color:
        thermal_color = base_out / "thermal_color"
        thermal_color.mkdir(parents=True, exist_ok=True)

    csv_dir = None
    if want_csv:
        csv_dir = base_out / "csv"
        csv_dir.mkdir(parents=True, exist_ok=True)

    return rgb, thermal, thermal_color, csv_dir


def list_images(root: Path):
    if root.is_file():
        return [root]
    if not root.is_dir():
        print(f"ERROR: Not a file or directory we can use: {root}", file=sys.stderr)
        sys.exit(1)

    exts = {".jpg", ".jpeg", ".JPG", ".JPEG"}
    out = []
    for r, _d, files in os.walk(root):
        for f in files:
            p = Path(r, f)
            if p.suffix in exts:
                out.append(p)
    return sorted(out)


def extract_exif(path: Path):
    try:
        p = subprocess.run(
            ["exiftool", "-j", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        data = json.loads(p.stdout)
        return data[0] if isinstance(data, list) and data else data
    except Exception:
        return None


def save_rgb(arr: np.ndarray, out_path: Path):
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    Image.fromarray(arr).save(out_path, format="PNG")


def save_thermal_encoded(arr_celsius: np.ndarray, out: Path):
    arr = arr_celsius.astype(np.float32)
    arr = np.nan_to_num(arr, nan=THERM_MIN_C, posinf=THERM_MAX_C, neginf=THERM_MIN_C)

    arr = np.clip(arr, THERM_MIN_C, THERM_MAX_C)
    norm = (arr - THERM_MIN_C) / THERM_SPAN_C
    values = np.round(norm * UINT16_MAX).astype(np.uint16)

    Image.fromarray(values, mode="I;16").save(out, format="PNG")


def save_thermal_color(arr_celsius: np.ndarray, out: Path):
    arr = arr_celsius.astype(np.float32)

    if np.isnan(arr).all():
        norm = np.zeros_like(arr)
    else:
        tmin = np.nanmin(arr)
        tmax = np.nanmax(arr)
        if tmax == tmin:
            norm = np.zeros_like(arr)
        else:
            norm = (arr - tmin) / (tmax - tmin)

    norm = np.clip(norm, 0, 1)
    rgba = cm.inferno(norm)
    rgb = (rgba[..., :3] * 255).astype(np.uint8)
    Image.fromarray(rgb).save(out, format="PNG")


def save_csv(arr_celsius: np.ndarray, out: Path):
    np.savetxt(out, arr_celsius, delimiter=",", fmt="%.4f")


def main():
    args = parse_args()

    in = Path(args.input_path).expanduser().resolve()
    out_base = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir else Path.cwd() / "out"
    )

    rgb_dir, th_dir, th_color_dir, csv_dir = ensure_dirs(
        out_base, want_color=args.color, want_csv=args.csv
    )

    imgs = list_images(in)
    if not imgs:
        print(f"ERROR: No images found in {in}", file=sys.stderr)
        sys.exit(1)

    flir = FlirImageExtractor()
    meta = {}

    for p in tqdm(imgs, desc="Extracting"):
        try:
            flir.process_image(str(p))
        except Exception as e:
            print(f"\nBad image {p}: {e}", file=sys.stderr)
            continue

        try:
            rgb = flir.get_rgb_np()
        except Exception:
            rgb = None

        try:
            thermal = flir.get_thermal_np()  # float °C
        except Exception:
            thermal = None

        base = p.stem

        rgb_out = rgb_dir / f"{base}_rgb.png"
        thermal_out = th_dir / f"{base}_thermal.png"
        color_out = th_color_dir / f"{base}_thermal_color.png" if args.color else None
        csv_out = csv_dir / f"{base}.csv" if args.csv else None

        if rgb is not None:
            try:
                save_rgb(rgb, rgb_out)
            except Exception:
                rgb_out = None

        if thermal is not None:
            try:
                save_thermal_encoded(thermal, thermal_out)
            except Exception:
                thermal_out = None

            if args.color and color_out is not None:
                try:
                    save_thermal_color(thermal, color_out)
                except Exception:
                    color_out = None

            if args.csv and csv_out is not None:
                try:
                    save_csv(thermal, csv_out)
                except Exception:
                    csv_out = None
        else:
            thermal_out = None
            if args.color:
                color_out = None
            if args.csv:
                csv_out = None

        meta[str(p)] = {
            "input": str(p),
            "rgb_image": str(rgb_out) if rgb_out else None,
            "thermal_image": str(thermal_out) if thermal_out else None,
            "thermal_color_image": str(color_out) if color_out else None,
            "thermal_csv": str(csv_out) if csv_out else None,
            "thermal_encoding": {
                "unit": "celsius",
                "range_celsius": [THERM_MIN_C, THERM_MAX_C],
                "decode": (
                    "norm = value / 65535.0; "
                    "temperature_celsius = norm * (range[1] - range[0]) + range[0]"
                ),
                "note": "With range [0,100], naive normalization value/65535*100 gives °C.",
            },
            "exif": extract_exif(p),
        }

    with (out_base / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()


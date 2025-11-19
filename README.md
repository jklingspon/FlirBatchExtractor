# Flir Batch Extractor

A wrapper tool for extracting RGB, 16-bit Thermal, and raw CSV from a directory full of FLIR ONE® images.

## Requirements

- Python ≥ 3.8  
- numpy  
- pillow  
- matplotlib  
- tqdm  
- exiftool

To install exiftool, see: https://exiftool.org/install.html
This script expects it to be in your PATH.

## Usage

```bash
    flir-batch-extractor INPUT [OUTPUT] [--color] [--csv]
 
INPUT:
    Path to a FLIR JPEG file or a directory containing such files.
 
OUTPUT (optional):
    Output directory (default: {working directory}/out).
 
Optional:
    --color    Also save colormapped thermal PNGs in {out_dir}/thermal_color/
    --csv      Also save raw Celsius matrices in {out_dir}/csv/

```

## Output Sturecture
```bash
    {out_dir}/rgb/*.png            – embedded RGB images (8-bit)
    {out_dir}/thermal/*.png        – thermal images (16-bit gray, linear in °C)
    {out_dir}/thermal_color/*.png  – colormapped thermal images (if --color)
    {out_dir}/csv/*.csv            – raw per-pixel °C values (if --csv)
    {out_dir}/meta.json            – all metadata
```

## Examples


```bash
flir-batch-extractor /path/to/some/jpgs/ ./myoutputs/ --color --csv
```

Outputs:

```
myoutputs/
  rgb/
  thermal/
  thermal_color/
  csv/
  meta.json
```


## 16 bit thermal PNG enoding details:
The thermal/\*.png files are encoded as 16-bit PNGs. Essentially the behavior I've seen from FlirStudio when you export thermal as 16-bit PNGs. Image values are linear in centi-degrees, such that if you normalize to a 0-100 scale, pixel values should read as their actual measured temperatures.

<img width="1520" height="1198" alt="image" src="https://github.com/user-attachments/assets/f21f4c42-de91-486d-954f-fcdc680f28c8" />

## Credits

FlirImageExtractor is forked from https://github.com/ITVRoC/FlirImageExtractor

Raw value to temperature conversion is ported from this R package: https://github.com/gtatters/Thermimage/blob/master/R/raw2temp.R
Original Python code from: https://github.com/Nervengift/read_thermal.py

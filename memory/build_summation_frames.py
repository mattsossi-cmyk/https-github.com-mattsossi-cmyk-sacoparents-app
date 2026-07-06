"""Generate 5 pan/zoom crops from the Summation poster so the 45-second
trailer can Ken-Burns across each report while keeping a coherent visual.

The source is 1024x1536. We output 5 PNGs sized to preserve the 1080x1350
(4:5) target aspect so the video builder can drop them straight in with
no letterboxing.
"""
from pathlib import Path
from PIL import Image

SRC = Path("/app/memory/summation_frames/summation-source.png")
OUT_DIR = Path("/app/memory/summation_frames")

# Target aspect matches the trailer output (1080x1350 → 4:5)
TARGET_W, TARGET_H = 1080, 1350
ASPECT = TARGET_W / TARGET_H  # 0.8


def crop_to_aspect(img: Image.Image, cx: float, cy: float, zoom: float) -> Image.Image:
    """Crop centred on normalised (cx, cy) at the given zoom factor.
    zoom=1.0 → largest crop that fits the source. zoom=1.5 → 1.5x closer.
    """
    src_w, src_h = img.size
    # Largest 4:5 rectangle that fits inside the source at zoom=1.
    if src_w / src_h > ASPECT:
        # source is wider than target ratio → height-bound
        base_h = src_h
        base_w = base_h * ASPECT
    else:
        base_w = src_w
        base_h = base_w / ASPECT

    crop_w = base_w / zoom
    crop_h = base_h / zoom

    cx_px = cx * src_w
    cy_px = cy * src_h

    left = max(0, min(src_w - crop_w, cx_px - crop_w / 2))
    top = max(0, min(src_h - crop_h, cy_px - crop_h / 2))
    right = left + crop_w
    bottom = top + crop_h
    return img.crop((left, top, right, bottom)).resize(
        (TARGET_W, TARGET_H), Image.LANCZOS
    )


def main():
    img = Image.open(SRC).convert("RGB")

    # 1. Full poster — establishing shot (slight breathing room)
    crop_to_aspect(img, 0.50, 0.50, 1.00).save(OUT_DIR / "01-full.png")

    # 2. Conflict Assessment (left panel, upper middle of image)
    crop_to_aspect(img, 0.20, 0.48, 1.55).save(OUT_DIR / "02-conflict.png")

    # 3. Foundation Statement (middle panel)
    crop_to_aspect(img, 0.50, 0.48, 1.55).save(OUT_DIR / "03-foundation.png")

    # 4. Mediation Declaration (right panel)
    crop_to_aspect(img, 0.80, 0.48, 1.55).save(OUT_DIR / "04-mediation.png")

    # 5. Outro — pan down to tagline area
    crop_to_aspect(img, 0.50, 0.86, 1.00).save(OUT_DIR / "05-tagline.png")

    for f in sorted(OUT_DIR.glob("0*.png")):
        print(f.name, "→", Image.open(f).size)


if __name__ == "__main__":
    main()

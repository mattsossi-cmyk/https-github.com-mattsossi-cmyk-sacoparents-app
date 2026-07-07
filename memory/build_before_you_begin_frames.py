"""Generate pan/zoom crops for the before-you-begin coaching video.
Now uses two posters:
  - '01-journey.png'   (A Better Co-Parenting Journey Starts Here)
  - '09-summaries.png' (Your Summaries. Your Roadmap.)
"""
from pathlib import Path
from PIL import Image

SLIDES_DIR = Path("/app/memory/intro_slides")
OUT_DIR = Path("/app/memory/before_you_begin_frames")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_W, TARGET_H = 1080, 1350
ASPECT = TARGET_W / TARGET_H


def crop_to_aspect(img: Image.Image, cx: float, cy: float, zoom: float) -> Image.Image:
    src_w, src_h = img.size
    if src_w / src_h > ASPECT:
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
    return img.crop((left, top, left + crop_w, top + crop_h)).resize(
        (TARGET_W, TARGET_H), Image.LANCZOS
    )


def main():
    journey = Image.open(SLIDES_DIR / "01-journey.png").convert("RGB")
    summaries = Image.open(SLIDES_DIR / "09-summaries.png").convert("RGB")

    # 1. Journey — full establishing shot
    crop_to_aspect(journey, 0.50, 0.50, 1.00).save(OUT_DIR / "01-full.png")
    # 2. Journey — laptop / app preview zoom
    crop_to_aspect(journey, 0.60, 0.45, 1.55).save(OUT_DIR / "02-laptop.png")
    # 3. Journey — journal (Our Goals / Our Concerns / Our Commitments)
    crop_to_aspect(journey, 0.92, 0.55, 1.85).save(OUT_DIR / "03-journal.png")
    # 4. Journey — slow zoom-out to full again
    crop_to_aspect(journey, 0.50, 0.50, 1.05).save(OUT_DIR / "04-full-out.png")
    # 5. Summaries — full closing poster
    crop_to_aspect(summaries, 0.50, 0.50, 1.00).save(OUT_DIR / "05-summaries.png")

    for f in sorted(OUT_DIR.glob("0*.png")):
        print(f.name, "→", Image.open(f).size)


if __name__ == "__main__":
    main()

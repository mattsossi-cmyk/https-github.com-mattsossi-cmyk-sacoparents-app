"""Generate 6 pan/zoom crops from the SA CoParents landscape collage so
the intro video can Ken-Burns across each region with a portrait 4:5
output that matches our other trailers.
"""
from pathlib import Path
from PIL import Image

SRC = Path("/app/frontend/public/images/sa-coparents-collage.png")
OUT_DIR = Path("/app/memory/intro_collage_frames")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_W, TARGET_H = 1080, 1350
ASPECT = TARGET_W / TARGET_H  # 0.8


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
    img = Image.open(SRC).convert("RGB")

    # 1. Hero — SA CoParents logo + "Reflect. Prepare. Connect."
    crop_to_aspect(img, 0.50, 0.20, 1.60).save(OUT_DIR / "01-hero.png")

    # 2. Child at window — "your child deserves to feel safe, loved, supported"
    crop_to_aspect(img, 0.85, 0.20, 1.75).save(OUT_DIR / "02-child.png")

    # 3. Phone / app mockup — "assess, identify, create, prepare"
    crop_to_aspect(img, 0.30, 0.55, 1.55).save(OUT_DIR / "03-app.png")

    # 4. Parents writing — "personalized Foundation Statement, mediation prep"
    crop_to_aspect(img, 0.70, 0.55, 1.60).save(OUT_DIR / "04-writing.png")

    # 5. Family walking — "practical tools, reports, thoughtful guidance"
    crop_to_aspect(img, 0.15, 0.85, 1.75).save(OUT_DIR / "05-family.png")

    # 6. "3 SIMPLE STEPS" — closing "Let's get started together"
    crop_to_aspect(img, 0.50, 0.80, 1.55).save(OUT_DIR / "06-steps.png")

    for f in sorted(OUT_DIR.glob("0*.png")):
        print(f.name, "→", Image.open(f).size)


if __name__ == "__main__":
    main()

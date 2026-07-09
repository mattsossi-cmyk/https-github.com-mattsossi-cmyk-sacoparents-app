"""Generate Ken-Burns pan/zoom crops from the IPV Assessment infographic
so the intro video can pan across each section:
  1. Full establishing shot
  2. Title + hero silhouette
  3. "You are not alone" reassurance panel
  4. Four-icon feature grid at the bottom
  5. Footer CTA — "Start Assessment" tagline

Source is 1536x1024 (landscape 3:2). Output is 1920x1080 (16:9) so it
matches the landscape trailer aspect used elsewhere on the site.
"""
from pathlib import Path
from PIL import Image

SRC = Path("/app/memory/ipv_frames/ipv-source.png")
OUT_DIR = Path("/app/memory/ipv_frames")

TARGET_W, TARGET_H = 1920, 1080
ASPECT = TARGET_W / TARGET_H  # 1.777


def crop_to_aspect(img: Image.Image, cx: float, cy: float, zoom: float) -> Image.Image:
    src_w, src_h = img.size
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
    return img.crop((left, top, left + crop_w, top + crop_h)).resize(
        (TARGET_W, TARGET_H), Image.LANCZOS
    )


def main() -> None:
    img = Image.open(SRC).convert("RGB")

    # 1. Full establishing shot — the whole poster
    crop_to_aspect(img, 0.50, 0.50, 1.00).save(OUT_DIR / "01-title.png")

    # 2. Title area (left half) — "Intimate Partner Violence Assessment"
    crop_to_aspect(img, 0.28, 0.28, 1.55).save(OUT_DIR / "02-why.png")

    # 3. "You are not alone" reassurance shield (left, mid)
    crop_to_aspect(img, 0.30, 0.53, 1.65).save(OUT_DIR / "03-assess.png")

    # 4. Four-icon feature grid (bottom purple band)
    crop_to_aspect(img, 0.50, 0.74, 1.35).save(OUT_DIR / "04-confidential.png")

    # 5. Footer tagline + Start Assessment CTA
    crop_to_aspect(img, 0.60, 0.92, 1.30).save(OUT_DIR / "05-footer.png")

    print(f"wrote 5 frames to {OUT_DIR}")


if __name__ == "__main__":
    main()

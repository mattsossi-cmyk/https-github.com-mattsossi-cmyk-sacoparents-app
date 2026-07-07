"""Generate pan/zoom crops from the IPV Assessment infographic so the
intro video can Ken-Burns across each section:
  1. Title + silhouette hero
  2. "Why This Matters" 5-column grid
  3. "What You'll Assess" checklist
  4. "You are not alone" / confidential panels
  5. Footer CTA ("Take the First Step")

Source is 1024x1536 (portrait 2:3). We output 1080x1350 (4:5) so it
matches the trailer aspect ratio and drops into the builder unchanged.
"""
from pathlib import Path
from PIL import Image

SRC = Path("/app/memory/ipv_frames/ipv-source.png")
OUT_DIR = Path("/app/memory/ipv_frames")

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

    # 1. Title + hero silhouette (upper portion)
    crop_to_aspect(img, 0.50, 0.22, 1.40).save(OUT_DIR / "01-title.png")

    # 2. "Why This Matters" 5-column grid (mid-upper band)
    crop_to_aspect(img, 0.50, 0.48, 1.35).save(OUT_DIR / "02-why.png")

    # 3. "What You'll Assess" checklist (mid-lower left)
    crop_to_aspect(img, 0.30, 0.72, 1.30).save(OUT_DIR / "03-assess.png")

    # 4. "You are not alone" / confidential panel (mid-lower right)
    crop_to_aspect(img, 0.72, 0.72, 1.30).save(OUT_DIR / "04-confidential.png")

    # 5. Footer CTA — "Take the First Step Toward Safety and Solutions"
    crop_to_aspect(img, 0.50, 0.94, 1.10).save(OUT_DIR / "05-footer.png")

    for f in sorted(OUT_DIR.glob("0*.png")):
        print(f.name, "→", Image.open(f).size)


if __name__ == "__main__":
    main()

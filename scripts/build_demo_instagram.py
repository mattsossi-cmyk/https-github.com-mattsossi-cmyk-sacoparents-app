"""Instagram cuts of the demo: Reels 1080x1920 and feed 1080x1080, ~80 s highlight, big captions."""
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

D = Path("/tmp/demo")
OUT = Path("/app/frontend/public/demo")
FONT_B, FONT_R = "/app/backend/fonts/DejaVuSans-Bold.ttf", "/app/backend/fonts/DejaVuSans.ttf"
PURPLE, TEAL, GOLD = (91, 42, 134), (26, 142, 142), (214, 156, 32)

HIGHLIGHT = [
    ("01_landing", 9, "Two parents. Two perspectives.\nOne child-focused picture."),
    ("03_judge_dashboard", 9, "Judges refer a case from the\nJudicial Portal — no raw parent\nanswers are ever shown."),
    ("07_invite_parents", 9, "Each parent gets a private\nassessment link. Nothing is\nexchanged between them."),
    ("08_joint_report_top", 9, "When both finish, the Joint Report\ncompares perspectives — neutral\nand system-generated."),
    ("10b_pdf_cover_guide", 10, "The Professional Alignment Report:\ncover, reader guide and\n11 numbered sections."),
    ("10c_pdf_sections", 10, "Child-focused issues, options,\nresources and pathways — then\nthe professional certifies."),
    ("13_assistant", 9, "The Align Assistant drafts\nneutral text for review.\nAdvisory only — never a ruling."),
    ("12_court_packets", 9, "The judge receives a sealed\ncourt packet with a reader guide."),
]


def wrap_text(dr, text, font, width):
    out = []
    for para in text.split("\n"):
        cur = ""
        for w in para.split():
            t = (cur + " " + w).strip()
            if dr.textlength(t, font=font) > width:
                out.append(cur); cur = w
            else:
                cur = t
        out.append(cur)
    return out


def frame(src: Path, cap: str, W: int, H: int, dst: Path):
    im = Image.open(src).convert("RGB")
    canvas = Image.new("RGB", (W, H), (29, 15, 51))
    dr = ImageDraw.Draw(canvas)
    dr.ellipse((W - 520, -300, W + 200, 420), fill=TEAL)
    dr.ellipse((-220, H - 420, 300, H + 100), fill=GOLD)
    f_cap = ImageFont.truetype(FONT_B, 54 if H > W else 44)
    lines = wrap_text(dr, cap, f_cap, W - 140)
    cap_h = len(lines) * (f_cap.size + 12) + 40
    pad = 70
    img_w = W - 2 * pad
    shot = im.resize((img_w, round(im.height * img_w / im.width)))
    max_h = H - cap_h - 260
    if shot.height > max_h:
        shot = shot.crop((0, 0, shot.width, max_h))
    y_img = 150 if H > W else 110
    # card shadow + rounded screenshot
    mask = Image.new("L", shot.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, shot.width - 1, shot.height - 1), radius=28, fill=255)
    dr.rounded_rectangle((pad + 10, y_img + 14, pad + shot.width + 10, y_img + shot.height + 14), radius=28, fill=(0, 0, 0))
    canvas.paste(shot, (pad, y_img), mask)
    f_brand = ImageFont.truetype(FONT_B, 34)
    dr.text((pad, 60 if H > W else 40), "SA CoParents Align", font=f_brand, fill="white")
    y = y_img + shot.height + 60
    for l in lines:
        dr.text((pad, y), l, font=f_cap, fill="white")
        y += f_cap.size + 12
    dr.text((pad, H - 90), "sacoparentsalign.com", font=ImageFont.truetype(FONT_R, 30), fill=(154, 217, 217))
    canvas.save(dst)


def card(title, lines, bg, W, H, dst):
    im = Image.new("RGB", (W, H), bg)
    dr = ImageDraw.Draw(im)
    dr.ellipse((W - 520, -300, W + 200, 420), fill=TEAL if bg == PURPLE else PURPLE)
    dr.ellipse((-220, H - 420, 300, H + 100), fill=GOLD)
    f1, f2 = ImageFont.truetype(FONT_B, 84 if H > W else 70), ImageFont.truetype(FONT_R, 40 if H > W else 34)
    y = H // 2 - 220
    for l in wrap_text(dr, title, f1, W - 160):
        dr.text((80, y), l, font=f1, fill="white"); y += f1.size + 10
    y += 30
    for l in lines:
        dr.text((82, y), l, font=f2, fill=(240, 236, 250)); y += f2.size + 14
    im.save(dst)


def build(fmt: str):
    W, H = (1080, 1920) if fmt == "reels" else (1080, 1080)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    scenes = [("t", 5, None), *HIGHLIGHT, ("e", 7, None)]
    card("Two Parents. Two Perspectives. One Child-Focused Picture.", ["A 90-second look at SA CoParents Align", "for courts & family professionals"], PURPLE, W, H, D / f"ig_{fmt}_t.png")
    card("Starting With Alignment, Ending With Agreement.", ["sacoparentsalign.com", "Professionals: free account · Courts: Judicial Portal"], TEAL, W, H, D / f"ig_{fmt}_e.png")
    inputs, filters, durs = [], [], []
    for i, (name, secs, cap) in enumerate(scenes):
        p = D / f"ig_{fmt}_{name}.png"
        if cap is not None:
            frame(D / f"{name}.png", cap, W, H, p)
        inputs += ["-loop", "1", "-t", str(secs), "-i", str(p)]
        filters.append(f"[{i}:v]scale={W}:{H},setsar=1,format=yuv420p[v{i}]")
        durs.append(secs)
    prev, off = "[v0]", durs[0]
    for i in range(1, len(scenes)):
        out = f"[x{i}]" if i < len(scenes) - 1 else "[vout]"
        filters.append(f"{prev}[v{i}]xfade=transition=fade:duration=0.5:offset={off - 0.5}{out}")
        prev, off = out, off + durs[i] - 0.5
    dst = OUT / f"sacoparentsalign-demo-{'reels-9x16' if fmt == 'reels' else 'square-1x1'}.mp4"
    cmd = [ff, "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[vout]", "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(fmt, r.returncode, r.stderr[-400:] if r.returncode else f"ok {dst.name} {dst.stat().st_size // 1024} KB ~{off:.0f}s")


if __name__ == "__main__":
    for f in (sys.argv[1:] or ["reels", "square"]):
        build(f)

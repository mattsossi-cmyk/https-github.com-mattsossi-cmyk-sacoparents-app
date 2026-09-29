"""Assemble the 3-minute captioned demo MP4 from scene screenshots (no narration)."""
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

D = Path("/tmp/demo")
FONT_B = "/app/backend/fonts/DejaVuSans-Bold.ttf"
FONT_R = "/app/backend/fonts/DejaVuSans.ttf"
W, H = 1280, 720
PURPLE, TEAL = (91, 42, 134), (26, 142, 142)

SCENES = [  # (file, seconds, caption)
    ("00_title", 6, ""),
    ("01_landing", 10, "SA CoParents Align — professional & court tools for child-focused family resolution."),
    ("02_judge_welcome", 10, "1 · A judge signs in to the Judicial Portal. First-timers get a guided welcome and a 1-minute tour."),
    ("03_judge_dashboard", 11, "2 · The Judicial Portal: refer cases, track status, read frozen packets. Raw parent answers are never shown."),
    ("04_refer_case", 11, "3 · Refer a case: cause number, parties, hearing date and a nearby verified professional."),
    ("05_pro_dashboard", 11, "4 · The professional's dashboard: Invite Parents → Review Joint Report → Create Professional Report."),
    ("07_invite_parents", 11, "5 · Each parent receives a private invitation. Parents never see each other's answers."),
    ("06_pipeline", 11, "6 · The workflow pipeline tracks every case from individual assessments to the final report."),
    ("08_joint_report_top", 11, "7 · When both parents finish, the Joint Report compares perspectives — neutral and system-generated."),
    ("09_joint_report_alignment", 11, "8 · Areas of alignment, differences in perspective, and child-focused needs — side by side."),
    ("10_pro_report_cover", 11, "9 · The Professional Alignment Report editor: cover page, then 11 numbered sections."),
    ("10b_pdf_cover_guide", 12, "10 · The finished PDF — Page 1 professional contact cover and the 'How to Read This Report' guide."),
    ("10c_pdf_sections", 12, "11 · Child-Focused Legal Issues, Options & Resources, pathways — and the signed Professional Certification."),
    ("13_assistant", 11, "12 · The Align Assistant drafts neutral text for review — advisory only, never a custody recommendation."),
    ("11_pro_report_court_summary", 11, "13 · The professional certifies and finalizes. PDF, ZIP bundle or court packet — one click."),
    ("12_court_packets", 11, "14 · The judge receives the hash-sealed court packet with a reader guide beside each report."),
    ("99_end", 9, ""),
]


def card(name: str, title: str, lines: list[str], bg):
    im = Image.new("RGB", (W, H), bg)
    dr = ImageDraw.Draw(im)
    dr.ellipse((W - 420, -180, W + 120, 360), fill=TEAL if bg == PURPLE else PURPLE)
    dr.ellipse((-160, H - 260, 260, H + 160), fill=(214, 156, 32))
    f1, f2 = ImageFont.truetype(FONT_B, 64), ImageFont.truetype(FONT_R, 30)
    dr.text((90, 200), title, font=f1, fill="white")
    for i, l in enumerate(lines):
        dr.text((92, 310 + i * 46), l, font=f2, fill=(240, 236, 250))
    im.save(D / f"{name}.png")


def fit(src: Path, dst: Path, cap: str = ""):
    im = Image.open(src).convert("RGB")
    im = im.resize((W, round(im.height * W / im.width)))
    im = im.crop((0, 0, W, min(H, im.height)))
    canvas = Image.new("RGB", (W, H), (246, 244, 250))
    canvas.paste(im, (0, 0))
    if cap:
        dr = ImageDraw.Draw(canvas, "RGBA")
        dr.rectangle((0, H - 96, W, H), fill=(43, 20, 68, 228))
        f = ImageFont.truetype(FONT_B, 25)
        words, lines, cur = cap.split(), [], ""
        for w_ in words:
            t = (cur + " " + w_).strip()
            if dr.textlength(t, font=f) > W - 80:
                lines.append(cur); cur = w_
            else:
                cur = t
        lines.append(cur)
        for i, l in enumerate(lines[:2]):
            dr.text((40, H - 82 + i * 34), l, font=f, fill="white")
        dr.rounded_rectangle((W - 250, 14, W - 20, 46), radius=16, fill=(43, 20, 68, 200))
        dr.text((W - 236, 20), "sacoparentsalign.com", font=ImageFont.truetype(FONT_B, 17), fill=(154, 217, 217))
    canvas.save(dst)


def main():
    card("00_title", "SA CoParents Align", ["Two Parents. Two Perspectives.", "One Child-Focused Picture.", "", "A 3-minute walkthrough for courts and family professionals"], PURPLE)
    card("99_end", "Starting With Alignment,", ["Ending With Agreement.", "", "sacoparentsalign.com", "Professionals: create a free account · Courts: Judicial Portal"], TEAL)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    inputs, filters, streams = [], [], []
    for i, (name, secs, cap) in enumerate(SCENES):
        src = D / f"{name}.png"
        if not src.exists():
            print("missing", name)
            continue
        fit(src, D / f"f_{name}.png", cap)
        inputs += ["-loop", "1", "-t", str(secs), "-i", str(D / f"f_{name}.png")]
        n = len(streams)
        vf = f"[{n}:v]scale={W}:{H},setsar=1,format=yuv420p"
        filters.append(vf + f"[v{n}]")
        streams.append((n, secs))
    # chain xfades
    prev, offset = f"[v0]", streams[0][1]
    for idx in range(1, len(streams)):
        n, secs = streams[idx]
        out = f"[x{idx}]" if idx < len(streams) - 1 else "[vout]"
        filters.append(f"{prev}[v{n}]xfade=transition=fade:duration=0.6:offset={offset - 0.6}{out}")
        prev, offset = out, offset + secs - 0.6
    out = Path("/app/frontend/public/demo/sacoparentsalign-demo.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ff, "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[vout]", "-r", "24", "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.returncode, r.stderr[-600:] if r.returncode else f"ok {out} {out.stat().st_size // 1024} KB, ~{offset:.0f}s")


if __name__ == "__main__":
    main()

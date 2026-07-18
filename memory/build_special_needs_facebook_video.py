"""Special Needs Assessment — Facebook square video (1080x1080).

Walks a viewer through the 6-pillar Special Needs Assessment in ~55 seconds.
Optimised for Facebook feed autoplay (muted-first): every slide has a large
readable caption so the value is understood without sound.

Voiceover: OpenAI TTS "shimmer" (compassionate, soft) at 1.00x via Emergent LLM key.
Music bed: warm Cmaj7 chord at low volume — matches the other intro videos.

Output:
  /app/frontend/public/audio/special-needs-facebook.mp3
  /app/frontend/public/videos/special-needs-facebook.mp4
"""
import asyncio
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")

VIDEO_OUT = Path("/app/frontend/public/videos/special-needs-facebook.mp4")
AUDIO_OUT = Path("/app/frontend/public/audio/special-needs-facebook.mp3")
MUSIC_OUT = Path("/app/memory/_special_needs_facebook_music.wav")
FRAMES_DIR = Path("/app/memory/special_needs_facebook_frames")
FRAMES_DIR.mkdir(parents=True, exist_ok=True)

LOGO_PATH = Path("/app/backend/assets/sa_coparents_logo.png")
HERO_SOCCER = Path("/app/frontend/public/flyers/hero-soccer-parents.png")

W = H = 1080
MATTE = "0x3D1A78"

# Brand palette
DEEP_PURPLE = (61, 26, 120)
MID_PURPLE = (94, 45, 181)
TEAL = (45, 181, 181)
INK = (26, 19, 48)
WHITE = (255, 255, 255)
CREAM = (250, 247, 255)

SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
SERIF_R = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
SANS_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


SCRIPT = (
    "Every child is different. And for parents raising a child with autism, "
    "ADHD, a chronic medical condition, mental health needs, or a trauma "
    "history — co-parenting can feel like walking two very different paths. "
    "The SA CoParents Special Needs Assessment is a gentle, evidence-informed "
    "space to describe your child in your own words — across six practical "
    "pillars. "
    "Understanding your child. Daily care and routines. Emotional and "
    "behavioural supports. Parent alignment. Advocacy and community. And "
    "long-term wellbeing. "
    "One question at a time. Save and return anytime. And when you're done, "
    "you'll receive three warm, professionally-structured reports you can "
    "share with a co-parent, teacher, or therapist. "
    "Because your child deserves both homes on the same page. "
    "Start free at sacoparentsapp.online."
)


# ---- Slide frame renderer ---------------------------------------------------

def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(draw, text, ft, max_w):
    words = text.split(" ")
    lines, line = [], ""
    for w in words:
        trial = (line + " " + w).strip()
        if draw.textlength(trial, font=ft) > max_w and line:
            lines.append(line)
            line = w
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def brand_bg():
    """Vertical gradient background used on every slide."""
    img = Image.new("RGB", (W, H), DEEP_PURPLE)
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        if t < 0.5:
            tt = t / 0.5
            r = int(DEEP_PURPLE[0] + (MID_PURPLE[0] - DEEP_PURPLE[0]) * tt)
            g = int(DEEP_PURPLE[1] + (MID_PURPLE[1] - DEEP_PURPLE[1]) * tt)
            b = int(DEEP_PURPLE[2] + (MID_PURPLE[2] - DEEP_PURPLE[2]) * tt)
        else:
            tt = (t - 0.5) / 0.5
            r = int(MID_PURPLE[0] + (TEAL[0] - MID_PURPLE[0]) * tt)
            g = int(MID_PURPLE[1] + (TEAL[1] - MID_PURPLE[1]) * tt)
            b = int(MID_PURPLE[2] + (TEAL[2] - MID_PURPLE[2]) * tt)
        for x in range(W):
            px[x, y] = (r, g, b)
    # subtle top glow
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for radius in range(700, 100, -60):
        alpha = int(50 * (1 - radius / 700))
        gd.ellipse((W // 2 - radius, -radius + 120, W // 2 + radius, radius + 120),
                   fill=(255, 255, 255, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(50))
    img.paste(glow, (0, 0), glow)
    return img


def render_logo_chip(img, cx, cy, chip_r=110):
    d = ImageDraw.Draw(img)
    d.ellipse((cx - chip_r, cy - chip_r, cx + chip_r, cy + chip_r), fill=WHITE)
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo_thumb = logo.copy()
    logo_thumb.thumbnail((chip_r * 2 - 20, chip_r * 2 - 20))
    img.paste(logo_thumb, (cx - logo_thumb.width // 2, cy - logo_thumb.height // 2), logo_thumb)


def slide_title(fp: Path, eyebrow: str, title_lines: list, subtitle: str = ""):
    img = brand_bg()
    render_logo_chip(img, W // 2, 200, chip_r=100)
    d = ImageDraw.Draw(img)

    if eyebrow:
        f_eye = font(SANS_B, 28)
        ew = d.textlength(eyebrow, font=f_eye)
        d.text(((W - ew) // 2, 340), eyebrow, fill=(255, 255, 255, 235), font=f_eye)

    f_t = font(SERIF, 88)
    y = 400
    for line in title_lines:
        lw = d.textlength(line, font=f_t)
        d.text(((W - lw) // 2, y), line, fill=WHITE, font=f_t)
        y += 110

    if subtitle:
        f_sub = font(SERIF_R, 40)
        lines = wrap(d, subtitle, f_sub, W - 200)
        y += 20
        for line in lines:
            lw = d.textlength(line, font=f_sub)
            d.text(((W - lw) // 2, y), line, fill=(255, 255, 255, 235), font=f_sub)
            y += 56
    img.save(fp, "PNG", optimize=True)


def slide_pillar(fp: Path, number: int, title: str, subtitle: str):
    img = brand_bg()
    d = ImageDraw.Draw(img)

    # big numeral badge
    badge_r = 90
    badge_cx, badge_cy = W // 2, 220
    d.ellipse((badge_cx - badge_r, badge_cy - badge_r,
               badge_cx + badge_r, badge_cy + badge_r), fill=WHITE)
    f_n = font(SERIF, 100)
    num_str = str(number)
    nw = d.textlength(num_str, font=f_n)
    d.text((badge_cx - nw / 2, badge_cy - 68), num_str, fill=DEEP_PURPLE, font=f_n)

    # eyebrow
    f_eye = font(SANS_B, 28)
    eye = "PILLAR"
    ew = d.textlength(eye, font=f_eye)
    d.text(((W - ew) // 2, 360), eye, fill=(255, 255, 255, 220), font=f_eye)

    # title
    f_t = font(SERIF, 76)
    lines = wrap(d, title, f_t, W - 180)
    y = 420
    for line in lines:
        lw = d.textlength(line, font=f_t)
        d.text(((W - lw) // 2, y), line, fill=WHITE, font=f_t)
        y += 92

    # subtitle
    f_sub = font(SERIF_R, 40)
    slines = wrap(d, subtitle, f_sub, W - 220)
    y += 30
    for line in slines:
        lw = d.textlength(line, font=f_sub)
        d.text(((W - lw) // 2, y), line, fill=(255, 255, 255, 235), font=f_sub)
        y += 56
    img.save(fp, "PNG", optimize=True)


def slide_cta(fp: Path):
    img = brand_bg()
    render_logo_chip(img, W // 2, 220, chip_r=100)
    d = ImageDraw.Draw(img)

    f_eye = font(SANS_B, 28)
    eye = "TRY IT FREE"
    ew = d.textlength(eye, font=f_eye)
    d.text(((W - ew) // 2, 360), eye, fill=(255, 255, 255, 235), font=f_eye)

    f_t = font(SERIF, 84)
    for i, line in enumerate(["Both homes.", "Same page."]):
        lw = d.textlength(line, font=f_t)
        d.text(((W - lw) // 2, 420 + i * 105), line, fill=WHITE, font=f_t)

    # URL pill
    f_url = font(SANS_B, 44)
    url = "sacoparentsapp.online"
    uw = d.textlength(url, font=f_url)
    pill_pad_x, pill_pad_y = 40, 22
    pill_x = (W - (uw + 2 * pill_pad_x)) // 2
    pill_y = 700
    d.rounded_rectangle(
        (pill_x, pill_y, pill_x + uw + 2 * pill_pad_x, pill_y + 40 + 2 * pill_pad_y),
        radius=48, fill=WHITE,
    )
    d.text((pill_x + pill_pad_x, pill_y + pill_pad_y - 4), url, fill=DEEP_PURPLE, font=f_url)
    img.save(fp, "PNG", optimize=True)


def build_frames():
    frames = []
    p = FRAMES_DIR / "01-title.png"
    slide_title(p, "SA CoParents · Special Needs Assessment",
                ["Every child", "is different."],
                "Six practical pillars. One warm space. Made for co-parents.")
    frames.append(p)

    p = FRAMES_DIR / "02-intro.png"
    slide_title(p, "For parents raising a child with…",
                ["Autism. ADHD.", "Chronic illness."],
                "Mental health needs. Trauma history. Developmental delays.")
    frames.append(p)

    pillars = [
        (1, "Understanding my child", "Strengths · Communication · Learning profile"),
        (2, "Daily care & routines", "Medication · Sleep · Meals · Therapies · School"),
        (3, "Emotional & behavioural supports", "Regulation · Triggers · Safety · Trauma-informed"),
        (4, "Parent alignment", "Shared goals · Decisions · Two-home consistency"),
        (5, "Advocacy & community", "IEP / 504 · Providers · Insurance · Community"),
        (6, "Long-term wellbeing & vision", "Quality-of-life · Hopes · Independence"),
    ]
    for i, (n, t, s) in enumerate(pillars, start=3):
        p = FRAMES_DIR / f"{i:02d}-pillar-{n}.png"
        slide_pillar(p, n, t, s)
        frames.append(p)

    p = FRAMES_DIR / "09-reports.png"
    slide_title(p, "Your outputs",
                ["Three warm", "reports."],
                "Child Needs Summary · Two-Home Plan · Mediation Statement.")
    frames.append(p)

    p = FRAMES_DIR / "10-cta.png"
    slide_cta(p)
    frames.append(p)
    return frames


# ---- Duration plan --------------------------------------------------------

DURATIONS = [
    ("01-title.png",       5.0),   # "Every child is different"
    ("02-intro.png",       7.5),   # "For parents raising a child with…"
    ("03-pillar-1.png",    4.5),
    ("04-pillar-2.png",    4.5),
    ("05-pillar-3.png",    4.5),
    ("06-pillar-4.png",    4.5),
    ("07-pillar-5.png",    4.5),
    ("08-pillar-6.png",    4.5),
    ("09-reports.png",     7.5),   # "three warm reports…"
    ("10-cta.png",         6.5),   # closing CTA
]
FADE = 0.4
TOTAL_SECONDS = round(sum(d for _, d in DURATIONS) + FADE * (len(DURATIONS) - 1))


# ---- TTS voiceover --------------------------------------------------------

async def generate_voiceover() -> None:
    if AUDIO_OUT.exists() and AUDIO_OUT.stat().st_size > 20_000:
        print(f"voice-over already present at {AUDIO_OUT} — skipping regen")
        return
    tts = OpenAITextToSpeech(api_key=os.environ["EMERGENT_LLM_KEY"])
    audio_bytes = await tts.generate_speech(
        text=SCRIPT, model="tts-1-hd", voice="shimmer", speed=1.00,
    )
    AUDIO_OUT.parent.mkdir(parents=True, exist_ok=True)
    AUDIO_OUT.write_bytes(audio_bytes)
    print(f"wrote {AUDIO_OUT} ({len(audio_bytes)//1024} KB)")


def synth_music() -> None:
    notes = [130.81, 164.81, 196.00, 246.94, 329.63]
    aeval = "+".join(
        f"0.18*sin(2*PI*{f}*t)*(0.7+0.3*sin(2*PI*0.12*t+{i}))"
        for i, f in enumerate(notes)
    )
    chain = (
        f"aevalsrc='{aeval}':d={TOTAL_SECONDS}:s=44100,"
        "volume=1.5,lowpass=f=2600,"
        "chorus=0.5:0.9:50|60:0.35|0.45:0.25|0.30:2|2.5,"
        "aecho=0.8:0.7:60|120|240:0.25|0.18|0.10,"
        f"afade=t=in:st=0:d=1.5,afade=t=out:st={TOTAL_SECONDS-2.5}:d=2.5,"
        "aformat=channel_layouts=stereo"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-filter_complex", chain,
         "-t", str(TOTAL_SECONDS), "-c:a", "pcm_s16le", str(MUSIC_OUT)],
        check=True, capture_output=True,
    )


def build_video() -> None:
    inputs = []
    for name, dur in DURATIONS:
        inputs += ["-loop", "1", "-t", f"{dur + FADE:.3f}", "-i", str(FRAMES_DIR / name)]
    inputs += ["-i", str(AUDIO_OUT), "-i", str(MUSIC_OUT)]

    parts = []
    for i in range(len(DURATIONS)):
        parts.append(
            f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={MATTE},"
            "setsar=1,fps=30,format=yuv420p"
            f"[v{i}]"
        )

    prev = "v0"
    off = 0.0
    for i in range(1, len(DURATIONS)):
        off += DURATIONS[i - 1][1]
        parts.append(f"[{prev}][v{i}]xfade=transition=fade:duration={FADE}:offset={off:.3f}[vx{i}]")
        prev = f"vx{i}"
    parts.append(f"[{prev}]trim=duration={TOTAL_SECONDS},setpts=PTS-STARTPTS[vout]")

    v_idx = len(DURATIONS)
    m_idx = len(DURATIONS) + 1
    parts.append(
        f"[{v_idx}:a]apad=whole_dur={TOTAL_SECONDS},"
        f"atrim=duration={TOTAL_SECONDS},volume=1.0[avoice]"
    )
    parts.append(f"[{m_idx}:a]atrim=duration={TOTAL_SECONDS},volume=0.14[amus]")
    parts.append(
        f"[avoice][amus]amix=inputs=2:duration=first:dropout_transition=3:normalize=0,"
        f"afade=t=out:st={TOTAL_SECONDS-1.2}:d=1.2[aout]"
    )

    VIDEO_OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", *inputs,
            "-filter_complex", ";".join(parts),
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", "-shortest",
            str(VIDEO_OUT),
        ],
        check=True,
    )
    print(f"wrote {VIDEO_OUT} ({VIDEO_OUT.stat().st_size//1024} KB) ≈{TOTAL_SECONDS}s")


async def main():
    build_frames()
    await generate_voiceover()
    synth_music()
    build_video()


if __name__ == "__main__":
    asyncio.run(main())

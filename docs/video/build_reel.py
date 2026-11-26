"""Build a 30-second vertical AgriTwin Instagram Reel with motion graphics and VFX.

Inputs:  docs/video/assets/voice_*.mp3 + app screenshots
Outputs: docs/video/AgriTwin_Instagram_Reel.mp4
"""

from __future__ import annotations

import math
import random
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
VIDEO_DIR = ROOT / "docs" / "video"
ASSETS = VIDEO_DIR / "assets"
OUTPUT = VIDEO_DIR / "AgriTwin_Instagram_Reel.mp4"
NARRATION = ASSETS / "reel_narration.wav"

W, H = 1080, 1920
FPS = 24
DURATION = 30.0
TOTAL_FRAMES = int(FPS * DURATION)

SCENE_SECONDS = [3.4, 4.6, 3.1, 5.2, 3.0, 4.3, 6.4]
SCENE_STARTS: list[float] = []
_acc = 0.0
for _s in SCENE_SECONDS:
    SCENE_STARTS.append(_acc)
    _acc += _s

CAPTIONS = [
    "A farmer’s morning starts with questions.",
    "Crop sick? Harvest? Where should I sell?",
    "AgriTwin puts the answers in one place.",
    "Health · Yield · One clear decision",
    "A leaf photo says what needs attention.",
    "An honest yield range — not a fake number.",
    "Real mandi rates near his farm. Better selling.",
]

FONT_REG = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")
FONT_ITALIC = Path(r"C:\Windows\Fonts\segoeuii.ttf")

INK = (17, 51, 37)
GREEN = (34, 122, 76)
GREEN_DARK = (10, 43, 31)
AMBER = (244, 174, 78)
CREAM = (255, 249, 235)
WHITE = (255, 255, 255)
MUTED = (91, 111, 100)


def font(size: int, bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else (FONT_ITALIC if italic else FONT_REG)
    if not path.exists():
        path = Path(r"C:\Windows\Fonts\arial.ttf")
    return ImageFont.truetype(str(path), size)


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def ease_out(t: float) -> float:
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_out_back(t: float) -> float:
    t = clamp(t)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def alpha(v: float) -> int:
    return int(255 * clamp(v))


def rgb(c: tuple[int, int, int], a: int = 255) -> tuple[int, int, int, int]:
    return c + (a,)


def make_gradient(top: tuple[int, int, int], mid: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    px = img.load()
    for y in range(H):
        if y < H * 0.55:
            t = y / (H * 0.55)
            row = tuple(lerp(top[i], mid[i], t) for i in range(3))
        else:
            t = (y - H * 0.55) / (H * 0.45)
            row = tuple(lerp(mid[i], bottom[i], t) for i in range(3))
        for x in range(W):
            px[x, y] = row + (255,)
    return img


def make_glow(center: tuple[int, int], radius: int, color: tuple[int, int, int], strength: int = 150) -> Image.Image:
    small_r = max(1, radius // 4)
    sw, sh = small_r * 2, small_r * 2
    glow = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    gp = glow.load()
    for y in range(sh):
        for x in range(sw):
            dist = math.hypot(x - small_r, y - small_r) / small_r
            if dist < 1:
                a = int(strength * (1 - dist) ** 2)
                gp[x, y] = color + (a,)
    return glow.resize((radius * 2, radius * 2), Image.Resampling.BICUBIC)


def make_field_bg() -> Image.Image:
    img = make_gradient((9, 42, 31), (232, 170, 96), (18, 74, 48))
    glow = make_glow((820, 760), 620, (255, 206, 120), 130)
    img.alpha_composite(glow, (200, 140))

    d = ImageDraw.Draw(img, "RGBA")
    # Distant hills.
    d.polygon([(0, 1180), (180, 1080), (390, 1170), (650, 1030), (900, 1140), (1080, 1060), (1080, 1920), (0, 1920)], fill=(22, 78, 50, 130))
    # Field rows.
    for i in range(14):
        y = 1190 + i * 58
        d.arc((-220 - i * 10, y - 130, W + 220 + i * 10, y + 190), 190, 350, fill=(54, 137, 83, 150), width=5)
    for i in range(9):
        y = 1340 + i * 82
        d.arc((-320 - i * 12, y - 170, W + 320 + i * 12, y + 240), 195, 345, fill=(29, 103, 60, 170), width=7)
    return img


def make_cream_bg() -> Image.Image:
    img = make_gradient((250, 246, 234), (247, 243, 231), (229, 239, 228))
    glow = make_glow((150, 1700), 520, (120, 180, 130), 60)
    img.alpha_composite(glow, (-110, 1200))
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(7):
        y = 1640 + i * 48
        d.arc((-180 - i * 10, y - 100, W + 180 + i * 10, y + 150), 195, 345, fill=(116, 170, 130, 45), width=4)
    return img


def make_grain() -> Image.Image:
    rng = random.Random(9)
    grain = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = grain.load()
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            a = rng.randint(0, 12)
            px[x, y] = (255, 255, 255, a)
    return grain


def wrap(text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if probe.textbbox((0, 0), trial, font=fnt)[2] <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text_lines(
    img: Image.Image,
    text: str,
    xy: tuple[int, int],
    fnt: ImageFont.FreeTypeFont,
    color: tuple[int, int, int],
    alpha_value: int = 255,
    max_width: int | None = None,
    line_gap: int = 12,
    stroke: int = 0,
) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    lines = wrap(text, fnt, max_width or W) if max_width else [text]
    lh = fnt.size + line_gap
    for i, line in enumerate(lines):
        d.text(
            (xy[0], xy[1] + i * lh),
            line,
            font=fnt,
            fill=rgb(color, alpha_value),
            stroke_width=stroke,
            stroke_fill=rgb((0, 0, 0), min(alpha_value, 150)),
        )


def round_rect(
    img: Image.Image,
    box: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int] | None = None,
    width: int = 1,
) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def glow_outline(img: Image.Image, box: tuple[int, int, int, int], radius: int, color: tuple[int, int, int], strength: int = 120) -> None:
    x0, y0, x1, y1 = box
    pad = 24
    patch = Image.new("RGBA", (x1 - x0 + pad * 2, y1 - y0 + pad * 2), (0, 0, 0, 0))
    pd = ImageDraw.Draw(patch, "RGBA")
    pd.rounded_rectangle((pad, pad, patch.width - pad, patch.height - pad), radius=radius, outline=rgb(color, strength), width=12)
    patch = patch.filter(ImageFilter.GaussianBlur(16))
    img.alpha_composite(patch, (x0 - pad, y0 - pad))
    round_rect(img, box, radius, (0, 0, 0, 0), outline=rgb(color, 255), width=5)


def make_screenshot(name: str) -> Image.Image:
    src = Image.open(ASSETS / name).convert("RGBA")
    src = src.crop((0, 0, src.width, int(src.width * 9 / 16)))
    return src.resize((1000, 563), Image.Resampling.LANCZOS)


def paste_screenshot(img: Image.Image, src: Image.Image, box: tuple[int, int, int, int], scale: float = 1.0) -> None:
    x, y, w, h = box
    cw = min(src.width, int(w / scale))
    ch = min(src.height, int(h / scale))
    left = (src.width - cw) // 2
    top = (src.height - ch) // 2
    shot = src.crop((left, top, left + cw, top + ch)).resize((w, h), Image.Resampling.LANCZOS)

    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow, "RGBA")
    sd.rounded_rectangle((x + 12, y + 18, x + w + 12, y + h + 18), radius=28, fill=(0, 0, 0, 80))
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    img.alpha_composite(shadow)

    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, w - 1, h - 1), radius=28, fill=255)
    img.paste(shot, (x, y), mask)
    round_rect(img, (x, y, x + w - 1, y + h - 1), 28, (0, 0, 0, 0), outline=(255, 255, 255, 210), width=3)


def draw_logo(img: Image.Image, x: int, y: int, scale: float = 1.0, light: bool = True, a: int = 255) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    s = scale
    d.ellipse((x, y, x + 46 * s, y + 46 * s), fill=rgb(AMBER, a))
    d.ellipse((x + 12 * s, y + 12 * s, x + 34 * s, y + 34 * s), fill=rgb(WHITE if light else CREAM, a))
    d.text((x + 60 * s, y - 4 * s), "AgriTwin", font=font(int(38 * s), bold=True), fill=rgb(WHITE if light else INK, a))


def draw_caption(img: Image.Image, text: str) -> None:
    fnt = font(42, bold=True)
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    bbox = probe.textbbox((0, 0), text, font=fnt)
    tw = bbox[2] - bbox[0]
    box = (54, 1620, W - 54, 1770)
    round_rect(img, box, 34, (10, 43, 31, 225), outline=(255, 255, 255, 45), width=2)
    d = ImageDraw.Draw(img, "RGBA")
    d.text(((W - tw) / 2, 1660), text, font=fnt, fill=rgb(WHITE, 255))


def draw_progress(img: Image.Image, t: float) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle((0, H - 10, W, H), fill=(255, 255, 255, 45))
    d.rectangle((0, H - 10, int(W * clamp(t / DURATION)), H), fill=rgb(AMBER, 255))


def draw_particles(img: Image.Image, t: float, rng: random.Random, color: tuple[int, int, int] = (255, 214, 140), count: int = 46) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(count):
        x = (rng.random() * W + t * (8 + i % 5)) % W
        y = (rng.random() * H - t * (18 + i % 7)) % H
        r = 2 + (i % 4)
        a = int(90 * (0.5 + 0.5 * math.sin(t * 2 + i)))
        d.ellipse((x, y, x + r, y + r), fill=rgb(color, a))


def draw_sun_rays(img: Image.Image, t: float) -> None:
    cx, cy = 820, 760
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(18):
        ang = math.radians(i * 20 + t * 8)
        length = 620 + 80 * math.sin(t * 1.4 + i)
        x2 = cx + math.cos(ang) * length
        y2 = cy + math.sin(ang) * length
        d.line((cx, cy, x2, y2), fill=(255, 226, 160, 18), width=26)


def draw_light_sweep(img: Image.Image, t: float) -> None:
    x = (t * 420) % (W + 500) - 250
    sweep = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sweep, "RGBA")
    sd.rectangle((x, 0, x + 180, H), fill=(255, 255, 255, 22))
    img.alpha_composite(sweep)


def draw_flash(img: Image.Image, local: float, dur: float) -> None:
    edge = min(local, dur - local)
    if edge < 0.22:
        a = int(120 * (1 - edge / 0.22))
        d = ImageDraw.Draw(img, "RGBA")
        d.rectangle((0, 0, W, H), fill=(8, 34, 24, a))


def scene_0(img: Image.Image, t: float, local: float, rng: random.Random) -> None:
    draw_sun_rays(img, t)
    draw_particles(img, t, rng)
    a = alpha(ease_out(local / 0.7))
    text_lines(img, "A farmer’s day", (72, 300), font(46, bold=True), AMBER, a, stroke=2)
    text_lines(img, "starts with", (72, 380), font(86, bold=True), WHITE, a, stroke=2)
    text_lines(img, "questions.", (72, 490), font(86, bold=True), WHITE, a, stroke=2)
    draw_logo(img, 72, 130, 1.0, True, a)


def scene_1(img: Image.Image, t: float, local: float, rng: random.Random) -> None:
    draw_particles(img, t, rng)
    draw_logo(img, 72, 120)
    text_lines(img, "Three questions.", (72, 260), font(70, bold=True), WHITE, 255, stroke=2)
    cards = [
        (0.35, "01", "Is my crop sick?"),
        (1.45, "02", "What will I harvest?"),
        (2.55, "03", "Where should I sell?"),
    ]
    for delay, num, text in cards:
        p = ease_out_back((local - delay) / 0.55)
        if p <= 0:
            continue
        w, h = int(900 * min(p, 1.05)), int(190 * min(p, 1.05))
        x = (W - w) // 2
        y = 480 + (int(num) - 1) * 240 + int((1 - p) * 50)
        round_rect(img, (x, y, x + w, y + h), 34, (255, 249, 235, int(235 * clamp(p))), outline=(244, 174, 78, 220), width=3)
        d = ImageDraw.Draw(img, "RGBA")
        d.text((x + 34, y + 48), num, font=font(56, bold=True), fill=rgb(GREEN, alpha(p)))
        d.text((x + 150, y + 52), text, font=font(48, bold=True), fill=rgb(INK, alpha(p)))


def scene_2(img: Image.Image, t: float, local: float, rng: random.Random) -> None:
    draw_particles(img, t, rng, color=(170, 230, 190), count=60)
    p = ease_out_back(local / 0.8)
    scale = 0.82 + 0.18 * clamp(p)
    draw_logo(img, int(W / 2 - 190 * scale), int(520 * scale), scale, True, alpha(p))
    text_lines(img, "One app.", (90, 760), font(76, bold=True), WHITE, alpha(ease_out(local / 0.9)), stroke=2)
    text_lines(img, "Every field answer.", (90, 860), font(76, bold=True), AMBER, alpha(ease_out((local - 0.3) / 0.9)), stroke=2)
    pills = ["Health", "Yield", "Mandi rate", "Decision"]
    for i, pill in enumerate(pills):
        q = ease_out_back((local - 0.9 - i * 0.22) / 0.5)
        if q <= 0:
            continue
        x = 90 + i * 235
        y = 1120 + int((1 - q) * 60)
        f = font(32, bold=True)
        tw = ImageDraw.Draw(Image.new("RGB", (10, 10))).textbbox((0, 0), pill, font=f)[2]
        round_rect(img, (x, y, x + tw + 52, y + 76), 38, (255, 249, 235, int(230 * clamp(q))))
        ImageDraw.Draw(img, "RGBA").text((x + 26, y + 16), pill, font=f, fill=rgb(INK, alpha(q)))


def app_scene_base(img: Image.Image, title: str, subtitle: str, chip: str, t: float, rng: random.Random) -> None:
    draw_particles(img, t, rng, color=(80, 150, 110), count=30)
    draw_logo(img, 70, 90, 0.86, False, 255)
    text_lines(img, title, (70, 230), font(62, bold=True), INK, 255, max_width=940)
    text_lines(img, subtitle, (70, 420), font(34), MUTED, 255, max_width=930)
    f = font(30, bold=True)
    tw = ImageDraw.Draw(Image.new("RGB", (10, 10))).textbbox((0, 0), chip, font=f)[2]
    round_rect(img, (70, 540, 70 + tw + 48, 606), 33, (34, 122, 76, 235))
    ImageDraw.Draw(img, "RGBA").text((94, 554), chip, font=f, fill=rgb(WHITE, 255))


def scene_3(img: Image.Image, t: float, local: float, rng: random.Random, shot: Image.Image) -> None:
    app_scene_base(img, "One screen. One clear decision.", "Health, yield and today’s sell / wait signal together.", "DECISION FIRST", t, rng)
    scale = 1.0 + 0.07 * ease_out(local / 4.4)
    paste_screenshot(img, shot, (70, 690, 1010, 1200), scale)
    pulse = 0.5 + 0.5 * math.sin(t * 4)
    glow_outline(img, (610, 1030, 990, 1170), 24, AMBER, int(80 + 100 * pulse))
    d = ImageDraw.Draw(img, "RGBA")
    round_rect(img, (760, 1240, 1010, 1360), 28, (34, 122, 76, 245))
    d.text((802, 1264), "SELL", font=font(48, bold=True), fill=rgb(WHITE, 255))
    d.text((800, 1320), "medium risk", font=font(24), fill=rgb((220, 240, 228), 255))


def scene_4(img: Image.Image, t: float, local: float, rng: random.Random, shot: Image.Image) -> None:
    app_scene_base(img, "A leaf photo becomes an answer.", "The scan says what needs attention, in plain words.", "NEEDS ATTENTION", t, rng)
    scale = 1.03 - 0.03 * ease_out(local / 2.4)
    paste_screenshot(img, shot, (70, 690, 1010, 1200), scale)
    scan_y = 700 + ((t * 260) % 480)
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle((82, scan_y, 998, scan_y + 8), fill=(120, 230, 170, 150))
    d.rectangle((82, scan_y - 18, 998, scan_y + 26), fill=(120, 230, 170, 30))
    glow_outline(img, (300, 830, 980, 1090), 26, (120, 230, 170), 140)
    round_rect(img, (70, 1250, 560, 1370), 28, (244, 174, 78, 245))
    ImageDraw.Draw(img, "RGBA").text((100, 1278), "93% confidence", font=font(38, bold=True), fill=rgb(INK, 255))


def scene_5(img: Image.Image, t: float, local: float, rng: random.Random, shot: Image.Image) -> None:
    app_scene_base(img, "Plan with a range, not a guess.", "An 80% interval gives an honest planning band.", "80% RANGE", t, rng)
    paste_screenshot(img, shot, (70, 690, 1010, 1200), 1.02)
    p = ease_out(local / 2.0)
    d = ImageDraw.Draw(img, "RGBA")
    for i, (label, frac) in enumerate([("Low", 0.72), ("Estimate", 0.88), ("High", 1.0)]):
        y = 1270 + i * 72
        d.text((80, y), label, font=font(28, bold=True), fill=rgb(INK, 255))
        round_rect(img, (250, y + 4, 250 + int(680 * frac * p), y + 42), 19, (34, 122, 76, 220))
    d.text((740, 1270), "331–453 q", font=font(34, bold=True), fill=rgb(GREEN, 255))


def scene_6(img: Image.Image, t: float, local: float, rng: random.Random, shot: Image.Image) -> None:
    app_scene_base(img, "Real mandi rates near his farm.", "District-first government prices. No guesswork.", "BEST NEARBY PRICE", t, rng)
    paste_screenshot(img, shot, (70, 690, 1010, 1200), 1.0 + 0.05 * ease_out(local / 5.0))
    pulse = 0.5 + 0.5 * math.sin(t * 5)
    glow_outline(img, (90, 900, 560, 1130), 26, AMBER, int(90 + 110 * pulse))
    count = int(15 * ease_out(local / 1.8))
    d = ImageDraw.Draw(img, "RGBA")
    round_rect(img, (70, 1240, 640, 1410), 32, (244, 174, 78, 250))
    d.text((100, 1268), f"₹{count}/kg", font=font(72, bold=True), fill=rgb(INK, 255))
    d.text((104, 1352), "best nearby price today", font=font(28), fill=rgb(INK, 220))
    for i in range(9):
        x = (120 + i * 108 + t * 34) % W
        y = 1500 - ((t * 90 + i * 130) % 520)
        d.text((x, y), "₹", font=font(36, bold=True), fill=rgb(AMBER, int(50 + 60 * math.sin(t + i))))

    if local > SCENE_SECONDS[6] - 1.5:
        a = alpha((local - (SCENE_SECONDS[6] - 1.5)) / 0.5)
        round_rect(img, (70, 280, 1010, 600), 36, (10, 43, 31, int(235 * a)), outline=(255, 255, 255, int(60 * a)), width=2)
        text_lines(img, "AgriTwin", (120, 330), font(78, bold=True), WHITE, a)
        text_lines(img, "crop-to-cash decisions", (124, 440), font(38), AMBER, a)


def build_narration() -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    params = None
    chunks: list[bytes] = []
    for i, seconds in enumerate(SCENE_SECONDS):
        mp3 = ASSETS / f"voice_{i}.mp3"
        wav_path = ASSETS / f"voice_{i}.wav"
        subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-i", str(mp3), "-ar", "22050", "-ac", "1", str(wav_path)],
            check=True,
        )
        with wave.open(str(wav_path), "rb") as w:
            if params is None:
                params = w.getparams()
            raw = bytearray(w.readframes(w.getnframes()))
        target = int(seconds * params.framerate)
        have = len(raw) // (params.sampwidth * params.nchannels)
        if have < target:
            raw.extend(b"\x00" * ((target - have) * params.sampwidth * params.nchannels))
        else:
            raw = raw[: target * params.sampwidth * params.nchannels]
        chunks.append(bytes(raw))

    assert params is not None
    with wave.open(str(NARRATION), "wb") as out:
        out.setparams(params)
        for chunk in chunks:
            out.writeframes(chunk)


def render() -> None:
    field = make_field_bg()
    cream = make_cream_bg()
    grain = make_grain()
    shots = {
        "dashboard": make_screenshot("dashboard.png"),
        "crop": make_screenshot("crop-health.png"),
        "yield": make_screenshot("yield.png"),
        "market": make_screenshot("market.png"),
    }
    rng = random.Random(21)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{W}x{H}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-i",
        str(NARRATION),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-t",
        str(DURATION),
        "-movflags",
        "+faststart",
        str(OUTPUT),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None

    for frame_no in range(TOTAL_FRAMES):
        t = frame_no / FPS
        idx = max(i for i, start in enumerate(SCENE_STARTS) if start <= t)
        local = t - SCENE_STARTS[idx]
        frame = (field if idx in (0, 1, 2) else cream).copy()

        if idx == 0:
            scene_0(frame, t, local, rng)
        elif idx == 1:
            scene_1(frame, t, local, rng)
        elif idx == 2:
            scene_2(frame, t, local, rng)
        elif idx == 3:
            scene_3(frame, t, local, rng, shots["dashboard"])
        elif idx == 4:
            scene_4(frame, t, local, rng, shots["crop"])
        elif idx == 5:
            scene_5(frame, t, local, rng, shots["yield"])
        else:
            scene_6(frame, t, local, rng, shots["market"])

        draw_light_sweep(frame, t)
        draw_flash(frame, local, SCENE_SECONDS[idx])
        draw_caption(frame, CAPTIONS[idx])
        draw_progress(frame, t)
        frame.alpha_composite(grain)

        proc.stdin.write(frame.convert("RGB").tobytes())

    proc.stdin.close()
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"ffmpeg failed with exit code {rc}")


if __name__ == "__main__":
    build_narration()
    render()
    print(f"Wrote {OUTPUT}")

"""Build the final AgriTwin deck in the same style as Review 1.

Run:  backend\\.venv\\Scripts\\python.exe scripts\\build_final_presentation.py
Out:  presentation/AgriTwin_Final_Presentation_Review1_Style.pptx
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "presentation" / "assets"
VIDEO_ASSETS = ROOT / "docs" / "video" / "assets"
OUT = ROOT / "presentation" / "AgriTwin_Final_Presentation_Review1_Style.pptx"

# ---------------------------------------------------------------- design tokens
DEEP = RGBColor(0x14, 0x53, 0x2D)
FOREST = RGBColor(0x16, 0x65, 0x34)
GREEN = RGBColor(0x16, 0xA3, 0x4A)
LIGHT = RGBColor(0xDC, 0xFC, 0xE7)
PALE = RGBColor(0xF0, 0xFD, 0xF4)
NAVY = RGBColor(0x0F, 0x17, 0x2A)
SLATE = RGBColor(0x33, 0x41, 0x55)
GRAY = RGBColor(0x64, 0x74, 0x8B)
LINE = RGBColor(0xE2, 0xE8, 0xF0)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
AMBER = RGBColor(0xB4, 0x53, 0x09)
AMBER_BG = RGBColor(0xFF, 0xFB, 0xEB)
AMBER_LINE = RGBColor(0xF5, 0x9E, 0x0B)
MINT = RGBColor(0xBB, 0xF7, 0xD0)

FONT = "Segoe UI"
W, H = 13.333, 7.5
TOTAL = 13


def rgb(hex_value: str) -> RGBColor:
    value = hex_value.lstrip("#")
    return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def add_slide(prs: Presentation):
    return prs.slides.add_slide(prs.slide_layouts[6])


def rect(slide, x, y, w, h, fill=None, line=None, line_w=1.0, shape=MSO_SHAPE.RECTANGLE, radius=None):
    item = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    item.shadow.inherit = False
    if fill is None:
        item.fill.background()
    else:
        item.fill.solid()
        item.fill.fore_color.rgb = fill
    if line is None:
        item.line.fill.background()
    else:
        item.line.color.rgb = line
        item.line.width = Pt(line_w)
    if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        item.adjustments[0] = radius
    item.text_frame.text = ""
    return item


def text(
    slide,
    x,
    y,
    w,
    h,
    runs,
    size=12,
    color=NAVY,
    bold=False,
    align=PP_ALIGN.LEFT,
    anchor=MSO_ANCHOR.TOP,
    font=FONT,
    line_spacing=1.0,
    space_after=0,
    italic=False,
):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.word_wrap = True
    frame.margin_left = Inches(0.02)
    frame.margin_right = Inches(0.02)
    frame.margin_top = Inches(0.01)
    frame.margin_bottom = Inches(0.01)
    frame.vertical_anchor = anchor
    if isinstance(runs, str):
        runs = [runs]
    first = True
    for entry in runs:
        if isinstance(entry, str):
            entry = {"text": entry}
        paragraph = frame.paragraphs[0] if first else frame.add_paragraph()
        first = False
        paragraph.alignment = align
        paragraph.line_spacing = line_spacing
        paragraph.space_after = Pt(space_after)
        run = paragraph.add_run()
        run.text = entry["text"]
        run.font.name = entry.get("font", font)
        run.font.size = Pt(entry.get("size", size))
        run.font.bold = entry.get("bold", bold)
        run.font.italic = entry.get("italic", italic)
        run.font.color.rgb = entry.get("color", color)
    return box


def title_size(title: str) -> float:
    """Keep long section titles inside the 11.9 in header band."""
    if len(title) <= 34:
        return 27
    if len(title) <= 50:
        return 24.5
    return 23


def chrome(slide, index, title, kicker, subtitle=None):
    rect(slide, 0, 0, W, 0.07, fill=DEEP)
    text(slide, 0.6, 0.26, 8.5, 0.24, kicker.upper(), size=9, color=GREEN, bold=True)
    text(slide, 0.6, 0.5, 11.9, 0.55, title, size=title_size(title), color=NAVY, bold=True)
    if subtitle:
        text(slide, 0.6, 1.0, 12.1, 0.3, subtitle, size=11.5, color=GRAY)
    rect(slide, 0.6, 7.02, 12.13, 0.012, fill=LINE)
    text(slide, 0.6, 7.09, 8.0, 0.24, "AgriTwin · AI-Driven Crop Health & Market Intelligence", size=8, color=GRAY)
    text(
        slide,
        10.4,
        7.09,
        2.33,
        0.24,
        f"Final · 27 Nov 2026 · {index:02d}/{TOTAL}",
        size=8,
        color=GRAY,
        align=PP_ALIGN.RIGHT,
    )


def card(slide, x, y, w, h, fill=WHITE, line=LINE, accent=None, accent_w=0.05):
    rect(slide, x, y, w, h, fill=fill, line=line, line_w=0.9, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.05)
    if accent:
        rect(slide, x, y, accent_w, h, fill=accent)


def pill(slide, x, y, w, h, label, fill=LIGHT, color=DEEP, size=8.5, bold=True):
    rect(slide, x, y, w, h, fill=fill, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
    text(slide, x, y, w, h, label, size=size, color=color, bold=bold, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def badge(slide, x, y, d, label, fill=DEEP, color=WHITE, size=12):
    rect(slide, x, y, d, d, fill=fill, line=None, shape=MSO_SHAPE.OVAL)
    text(slide, x, y, d, d, label, size=size, color=color, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def picture(slide, name, x, y, w, h, border=True):
    path = VIDEO_ASSETS / name if (VIDEO_ASSETS / name).exists() else ASSETS / name
    with Image.open(path) as image:
        iw, ih = image.size
    scale = min(w / iw, h / ih)
    pw, ph = iw * scale, ih * scale
    px, py = x + (w - pw) / 2, y + (h - ph) / 2
    pic = slide.shapes.add_picture(str(path), Inches(px), Inches(py), Inches(pw), Inches(ph))
    if border:
        pic.line.color.rgb = LINE
        pic.line.width = Pt(0.75)
    return pic


def notes(slide, body):
    slide.notes_slide.notes_text_frame.text = body.strip()


def bullets(slide, x, y, w, h, items, size=10.5, color=SLATE, gap=4, bullet_color=GREEN):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.word_wrap = True
    frame.margin_left = Inches(0.02)
    frame.margin_right = Inches(0.02)
    for index, item in enumerate(items):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.space_after = Pt(gap)
        paragraph.line_spacing = 1.02
        dot = paragraph.add_run()
        dot.text = "•  "
        dot.font.name = FONT
        dot.font.size = Pt(size)
        dot.font.bold = True
        dot.font.color.rgb = bullet_color
        run = paragraph.add_run()
        run.text = item
        run.font.name = FONT
        run.font.size = Pt(size)
        run.font.color.rgb = color
    return box


# ------------------------------------------------------------------------ deck
prs = Presentation()
prs.slide_width = Inches(W)
prs.slide_height = Inches(H)

# ============================================================ 1 — TITLE
s = add_slide(prs)
rect(s, 0, 0, 0.22, 7.5, fill=DEEP)
text(s, 0.9, 0.7, 7.6, 0.3, "B.TECH CSE (AI & ML)  ·  MAJOR PROJECT  ·  FINAL", size=10, color=GREEN, bold=True)
text(s, 0.9, 1.05, 7.9, 0.9, "AgriTwin", size=58, color=DEEP, bold=True)
text(
    s,
    0.9,
    2.02,
    7.4,
    1.0,
    "AI-Driven Crop Health and\nMarket Intelligence System",
    size=26,
    color=NAVY,
    bold=True,
    line_spacing=1.02,
)
text(
    s,
    0.9,
    3.02,
    7.3,
    0.55,
    "A real-data digital twin for crop health, yield, market and decision support.",
    size=12,
    color=GRAY,
)
rect(s, 0.9, 3.7, 5.1, 0.02, fill=GREEN)
details = [
    ("Students", "Aravapalli Jashwanth 245523748071 · Kolluru Sai Vamshi 245523748097 · Mandula Sri Sreshta 245523748103"),
    ("Department", "Computer Science and Engineering (AI & ML)"),
    ("College", "Keshav Memorial Engineering College"),
    ("Academic year", "2026–27  ·  Submitted July 2026"),
    ("Project guide", "Mrs. D . Padmaja Usha Rani, Assistant Professor"),
]
for index, (label, value) in enumerate(details):
    y = 3.86 + index * 0.42
    text(s, 0.9, y, 1.35, 0.3, label.upper(), size=7.8, color=GRAY, bold=True)
    text(s, 2.3, y - 0.01, 5.6, 0.4, value, size=8.4 if index == 0 else 10.2, color=NAVY, bold=index == 0)

picture(s, "leaf.jpg", 8.55, 1.1, 3.35, 3.35)
picture(s, "gradcam.png", 10.55, 3.55, 1.55, 1.55)
text(s, 8.55, 4.52, 3.9, 0.3, "Real leaf image · ConvNeXt-Tiny + Grad-CAM", size=8, color=GRAY, align=PP_ALIGN.CENTER)
rect(s, 0, 6.55, W, 0.95, fill=DEEP)
text(s, 0.9, 6.72, 7.2, 0.55, "From Fields to Better Decisions.", size=21, color=WHITE, bold=True, italic=True)
text(s, 9.2, 6.82, 3.2, 0.3, "Final  ·  27 November 2026", size=10, color=MINT, align=PP_ALIGN.RIGHT)
notes(
    s,
    """This is the final AgriTwin presentation. Farmers already receive many predictions, but they still have to decide what to do. AgriTwin connects crop health, yield, market prices, buyers and transport into one explainable recommendation: sell, wait, or inspect.

The project is a working full-stack prototype, not a slide concept. This deck shows the final architecture, the deployed models, the deterministic decision engine and the verified results. Demo data, fallbacks and limitations are labelled explicitly.""",
)

# ============================================================ 2 — INTRODUCTION
s = add_slide(prs)
chrome(
    s,
    2,
    "Introduction",
    "Why this project",
    "Four disconnected signals decide a farmer's income — and they are rarely considered together.",
)
pains = [
    ("01", "Crop disease", "Losses grow before symptoms are obvious; expert advice is not immediate."),
    ("02", "Uncertain yield", "A single number hides the range that determines financial risk."),
    ("03", "Volatile prices", "Mandi prices move daily and differ by market, district and variety."),
    ("04", "Hidden costs", "Transport, commission and other charges change the real take-home price."),
]
for index, (number, title, body) in enumerate(pains):
    y = 1.5 + index * 0.95
    card(s, 0.6, y, 5.7, 0.85, accent=GREEN)
    badge(s, 0.78, y + 0.2, 0.42, number, fill=LIGHT, color=DEEP, size=9)
    text(s, 1.35, y + 0.1, 4.7, 0.25, title, size=11.5, color=NAVY, bold=True)
    text(s, 1.35, y + 0.36, 4.8, 0.42, body, size=9, color=GRAY)

card(s, 0.6, 5.45, 5.7, 1.35, fill=PALE, line=MINT, accent=GREEN, accent_w=0.06)
text(s, 0.85, 5.55, 5.2, 0.24, "PROJECT VISION", size=8.5, color=GREEN, bold=True)
text(
    s,
    0.85,
    5.8,
    5.25,
    0.85,
    "“Transform agricultural data into explainable and economically informed farming decisions.”",
    size=12.5,
    color=DEEP,
    bold=True,
    italic=True,
    line_spacing=1.05,
)

text(s, 6.75, 1.42, 5.9, 0.24, "SYSTEM CONCEPT", size=8.5, color=GREEN, bold=True)
flow = [
    ("Farmer", "crop, location, harvest intent", LIGHT, DEEP),
    ("Data collection", "leaf image · district · prices · buyers", LIGHT, DEEP),
    ("AI / ML analysis", "health · yield · market · transport", LIGHT, DEEP),
    ("Decision engine", "risk + net realization + rules", AMBER_BG, AMBER),
    ("Actionable recommendation", "SELL · WAIT · INSPECT", DEEP, WHITE),
]
for index, (title, body, fill, color) in enumerate(flow):
    y = 1.72 + index * 0.94
    rect(s, 6.75, y, 5.85, 0.78, fill=fill, line=AMBER_LINE if fill == AMBER_BG else LINE, line_w=1.4 if fill == AMBER_BG else 0.8, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
    text(s, 6.95, y + 0.08, 3.0, 0.26, title, size=11.5, color=color, bold=True)
    text(s, 6.95, y + 0.36, 5.4, 0.3, body, size=9, color=GRAY if fill != DEEP else MINT)
    if index < 4:
        rect(s, 9.55, y + 0.8, 0.22, 0.12, fill=GREEN, shape=MSO_SHAPE.DOWN_ARROW)
text(s, 6.75, 6.48, 5.9, 0.35, "The decision engine is the research contribution — not another prediction screen.", size=9, color=AMBER, bold=True)
notes(
    s,
    """Indian farmers make one high-stakes decision every season: when and where to sell. The information needed for that decision is fragmented across a leaf photo, a yield expectation, a mandi price, a buyer's phone call and a transport quote.

Each of those signals can be correct in isolation and still lead to a bad economic decision. For example, the highest quoted buyer price may be the worst choice after transport and commission.

AgriTwin's vision is to convert those scattered data points into one explainable, economically informed recommendation. The next slide states the problem and the objectives precisely.""",
)

# ============================================================ 3 — PROBLEM & OBJECTIVES
s = add_slide(prs)
chrome(
    s,
    3,
    "Problem Statement & Objectives",
    "What we solve",
    "The gap is not prediction accuracy alone — it is turning predictions into an economically sound action.",
)
rect(s, 0.6, 1.48, 5.15, 4.55, fill=NAVY, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.04)
text(s, 0.9, 1.65, 4.6, 0.3, "PROBLEM STATEMENT", size=8.5, color=MINT, bold=True)
text(
    s,
    0.9,
    1.98,
    4.55,
    3.2,
    [
        "Farmers decide what to grow, when to harvest and where to sell using disconnected sources: a leaf photo, a yield guess, yesterday's mandi price, a phone offer and a transport quote.",
        "Individual predictions do not automatically produce the best economic decision.",
        "AgriTwin integrates these sources into a unified, uncertainty-aware decision-support system.",
    ],
    size=10.5,
    color=WHITE,
    line_spacing=1.12,
    space_after=9,
)
rect(s, 0.9, 5.2, 4.55, 0.62, fill=AMBER_BG, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
text(s, 1.05, 5.2, 4.3, 0.62, "Fragmented predictions  ≠  optimal decision", size=11, color=AMBER, bold=True, anchor=MSO_ANCHOR.MIDDLE)

objectives = [
    ("1", "Crop-health detection"),
    ("2", "Grad-CAM explanation"),
    ("3", "Yield + 80% interval"),
    ("4", "Market forecasting"),
    ("5", "District/state rates"),
    ("6", "Buyer offer comparison"),
    ("7", "Transport cost estimation"),
    ("8", "Net realization + risk"),
    ("9", "SELL / WAIT / INSPECT"),
]
text(s, 6.05, 1.44, 6.7, 0.24, "OBJECTIVES", size=8.5, color=GREEN, bold=True)
for index, (number, label) in enumerate(objectives):
    col, row = index % 3, index // 3
    x = 6.05 + col * 2.24
    y = 1.72 + row * 1.32
    card(s, x, y, 2.1, 1.18, fill=WHITE)
    badge(s, x + 0.12, y + 0.13, 0.34, number, fill=LIGHT, color=DEEP, size=9)
    text(s, x + 0.12, y + 0.52, 1.88, 0.58, label, size=9.5, color=NAVY, bold=True, line_spacing=1.0)
rect(s, 6.05, 5.78, 6.68, 0.62, fill=PALE, line=MINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.14)
text(
    s,
    6.2,
    5.78,
    6.4,
    0.62,
    "Objective: one explainable recommendation — not five disconnected predictions.",
    size=10.5,
    color=DEEP,
    bold=True,
    anchor=MSO_ANCHOR.MIDDLE,
)
notes(
    s,
    """The problem statement is deliberately narrow. It is not that India lacks agricultural data or ML models. It is that the outputs are fragmented and do not answer the farmer's actual question: what should I do now?

So the objectives follow the decision chain. Detect disease from an image, explain it, estimate yield with a range, forecast price, compare buyers, estimate transport, compute net realization, quantify risk, and finally recommend sell, wait or inspect with reasons.

The ninth objective is the one that ties everything together. That is why the decision engine is treated as the core contribution rather than an add-on.""",
)

# ============================================================ 4 — ARCHITECTURE
s = add_slide(prs)
chrome(
    s,
    4,
    "Proposed Architecture",
    "Seven-layer design",
    "Data flows top-down; every layer exposes typed outputs. Layer 5 is the research contribution.",
)
layers = [
    ("1", "Input data", "Farmer & user · leaf image · crop, season, area, district/state · mandi prices · buyers · transport", False),
    ("2", "Data processing", "Image preprocessing · missing-value handling · encoding & scaling · time-series preparation · distance and cost", False),
    ("3", "Crop health", "ConvNeXt-Tiny · 38 classes / 14 crops · 4-view TTA · Grad-CAM evidence", False),
    ("4", "Yield & market intelligence", "ExtraTrees yield + 80% interval · crop-calendar harvest window · five forecasters · buyer analysis · transport", False),
    ("5", "Uncertainty-aware decision engine", "Rule policy v1.0.1 · 8-component risk · completeness · buyer vs mandi net realization · INSPECT / WAIT / SELL", True),
    ("6", "Output layer — farmer dashboard", "Health + Grad-CAM · yield interval · harvest window · buyer comparison · net realization · SELL / WAIT / INSPECT", False),
    ("7", "Impact", "Healthier crops · higher income · lower risk · data-driven farming · empowered farmers", False),
]
heights = [0.58, 0.58, 0.58, 0.58, 0.86, 0.58, 0.46]
y = 1.44
for index, ((number, title, body, highlight), height) in enumerate(zip(layers, heights)):
    fill = AMBER_BG if highlight else WHITE
    line = AMBER_LINE if highlight else LINE
    rect(s, 0.75, y, 11.85, height, fill=fill, line=line, line_w=1.6 if highlight else 0.9, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    badge(s, 0.9, y + (height - 0.38) / 2, 0.38, number, fill=AMBER if highlight else DEEP, size=10)
    text(s, 1.42, y + 0.06, 2.35, height - 0.1, title, size=11.5 if not highlight else 12.5, color=AMBER if highlight else NAVY, bold=True, anchor=MSO_ANCHOR.MIDDLE, line_spacing=0.98)
    text(s, 3.85, y + 0.05, 7.9 if highlight else 8.5, height - 0.08, body, size=9.2 if not highlight else 9.6, color=SLATE, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.0)
    if highlight:
        pill(s, 11.05, y + 0.1, 1.42, 0.24, "PRIMARY CONTRIBUTION", fill=AMBER, color=WHITE, size=7)
        text(s, 11.05, y + 0.4, 1.45, 0.4, "unit-tested,\nno I/O", size=8, color=AMBER, bold=True, align=PP_ALIGN.CENTER)
    if index < 6:
        rect(s, 1.0, y + height + 0.008, 0.18, 0.085, fill=GREEN, shape=MSO_SHAPE.DOWN_ARROW)
    y += height + 0.1
notes(
    s,
    """This is the seven-layer architecture. Reading top-down: raw inputs, then processing, then the prediction families, then the decision engine, then outputs and impact.

Layer 3 is crop health: a ConvNeXt-Tiny classifier over 38 classes covering 14 crops, with 4-view TTA and Grad-CAM. Layer 4 covers yield and market intelligence, including a config-driven crop-calendar harvest window, buyer analysis and transport estimate.

Layer 5 is the contribution. It is a deterministic rule policy v1.0.1, not an LLM. It converts each prediction into an uncertainty and risk term, computes net realization for every eligible buyer and for the mandi, applies ordered rules and records reasons.

Layer 6 is what the farmer sees. Layer 7 is the intended impact. Every layer is implemented in the repository; the following slides show the evidence.""",
)

# ============================================================ 5 — METHODOLOGY
s = add_slide(prs)
chrome(
    s,
    5,
    "Methodology",
    "End-to-end pipeline",
    "Seven stages, all implemented. The sequence is deliberate: decisions are only as good as the weakest upstream input.",
)
steps = [
    ("1", "Data collection", "Leaf image, farm, crop, district, season, area, buyers and transport details."),
    ("2", "Preprocessing", "Validate, clean, encode, scale, build chronological series, compute distance."),
    ("3", "Crop health", "ConvNeXt-Tiny classifies 38 classes; 4-view TTA and Grad-CAM provide evidence."),
    ("4", "Yield & market", "ExtraTrees + conformal interval; five forecasters compared chronologically."),
    ("5", "Buyer & transport", "Eligibility, distance, trips, cost; net realization per buyer."),
    ("6", "Uncertainty fusion", "8 risk components, completeness, confidence, revenue bounds."),
    ("7", "Decision generation", "Ordered rules output SELL / WAIT / INSPECT with reasons."),
]
positions_top = [(0.55, 1.48), (3.72, 1.48), (6.89, 1.48), (10.06, 1.48)]
positions_bottom = [(9.35, 3.98), (6.18, 3.98), (3.01, 3.98)]
positions = positions_top + positions_bottom
for index, (number, title, body) in enumerate(steps):
    x, y = positions[index]
    card(s, x, y, 2.72, 2.02, fill=WHITE)
    badge(s, x + 0.14, y + 0.14, 0.36, number, fill=DEEP, size=9.5)
    text(s, x + 0.58, y + 0.17, 2.0, 0.3, title, size=10.8, color=NAVY, bold=True)
    text(s, x + 0.16, y + 0.62, 2.42, 0.95, body, size=8.8, color=GRAY, line_spacing=1.03)
    pill(s, x + 0.16, y + 1.64, 1.5, 0.24, "IMPLEMENTED · TESTED", fill=LIGHT, color=DEEP, size=6.8)
for x in (3.3, 6.47, 9.64):
    rect(s, x, 2.4, 0.22, 0.16, fill=GREEN, shape=MSO_SHAPE.RIGHT_ARROW)
rect(s, 11.3, 3.56, 0.2, 0.36, fill=GREEN, shape=MSO_SHAPE.DOWN_ARROW)
for x in (9.0, 5.83):
    rect(s, x, 4.9, 0.22, 0.16, fill=GREEN, shape=MSO_SHAPE.LEFT_ARROW)
rect(s, 0.6, 6.25, 12.13, 0.5, fill=PALE, line=MINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.14)
text(
    s,
    0.75,
    6.25,
    11.8,
    0.5,
    "All seven stages run end-to-end today. 17 decision-engine unit tests; 115 backend + 32 frontend tests pass.",
    size=9.5,
    color=DEEP,
    bold=True,
    anchor=MSO_ANCHOR.MIDDLE,
)
notes(
    s,
    """The methodology follows the order in which information actually becomes a decision.

We collect the raw signals, preprocess them, run the three prediction families, then compare buyers and transport, then fuse uncertainty and finally apply decision rules.

I want to highlight one design choice: the pipeline is chronological wherever time matters. Yield validation uses a future year, and market forecasts validate on a held-out tail. We never shuffle time-series data, because that leaks the future.

The serpentine layout shows the order: steps one to four across the top, then down and back for five to seven. All seven are implemented and exercised by the smoke tests.""",
)

# ============================================================ 6 — TECHNOLOGIES
s = add_slide(prs)
chrome(
    s,
    6,
    "Technologies Used",
    "Actual implementation",
    "Only technologies present in the repository are listed. Planned items are labelled separately.",
)
tech = [
    ("Frontend", "React 18 · TypeScript · Vite · Tailwind CSS · TanStack Query · Recharts · React Hook Form + Zod"),
    ("Backend & API", "Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 · Alembic · JWT (bcrypt + PyJWT)"),
    ("AI / ML", "PyTorch + torchvision · ConvNeXt-Tiny · scikit-learn · NumPy · Pandas · custom Grad-CAM · PIL"),
    ("Data & storage", "PostgreSQL 16 (Docker) · SQLite (dev) · data.gov.in / Agmarknet + five-state fallback · PlantVillage + PlantDoc · crop production 1997–2015"),
    ("External services", "Open-Meteo weather (live, graceful fallback) · OSRM routing (implemented; geodesic fallback tested)"),
    ("Deployment & quality", "Docker Compose · Pytest (115) · Vitest (32) · structured JSON logs · rate limiting · CORS"),
]
for index, (title, body) in enumerate(tech):
    col, row = index % 3, index // 3
    x = 0.6 + col * 4.15
    y = 1.48 + row * 2.18
    card(s, x, y, 3.95, 2.02, fill=WHITE, accent=GREEN)
    text(s, x + 0.2, y + 0.16, 3.5, 0.28, title, size=12, color=DEEP, bold=True)
    text(s, x + 0.2, y + 0.55, 3.55, 1.3, body, size=9.2, color=SLATE, line_spacing=1.12)
rect(s, 0.6, 5.95, 12.13, 0.75, fill=AMBER_BG, line=AMBER_LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.1)
text(
    s,
    0.78,
    6.0,
    11.8,
    0.65,
    [
        {"text": "Planned, not implemented: ", "bold": True, "color": AMBER},
        {"text": "IoT soil sensors, verified live buyer networks, payment or logistics booking.   ", "color": SLATE},
        {"text": "Verified caveat: ", "bold": True, "color": AMBER},
        {"text": "OSRM road routing is coded but only the geodesic fallback is covered by automated tests.", "color": SLATE},
    ],
    size=9,
    line_spacing=1.1,
)
notes(
    s,
    """This slide is a technology inventory, not a wish list. Everything in the six cards is actually imported and used by the code in this repository.

Frontend: React with TypeScript, Vite, Tailwind, TanStack Query and Recharts. Backend: FastAPI, Pydantic, SQLAlchemy and Alembic, with JWT authentication.

AI: PyTorch for ConvNeXt-Tiny, scikit-learn for yield and market models, and a custom Grad-CAM implementation. Data: PostgreSQL in Docker, SQLite for development, real public datasets and official mandi feeds.

The amber box is important for honesty. IoT sensors and verified live buyer networks are planned, not built. Official mandi rates are implemented; OSRM routing is coded, but automated tests only cover the geodesic fallback.""",
)

# ============================================================ 7 — MODULES
s = add_slide(prs)
chrome(
    s,
    7,
    "Module Description",
    "Functional components",
    "Seven modules with explicit inputs and outputs; all share typed service interfaces.",
)
modules = [
    ("Input & data management", "Farms, crops, images, market imports", "In: user data, files, CSV", "Out: validated records"),
    ("Data processing", "Validation, encoding, scaling, series, distance", "In: raw records", "Out: model-ready features"),
    ("Crop health detection", "ConvNeXt-Tiny, 38 classes + Grad-CAM", "In: leaf image", "Out: label, confidence, overlay"),
    ("Yield & market intelligence", "Yield interval, crop-calendar window, forecasts", "In: crop, state, series", "Out: quintals, INR/quintal"),
    ("Buyer & transport", "Offers, eligibility, distance, trips, cost", "In: offers, locations", "Out: net realization per buyer"),
    ("Decision engine", "Risk fusion, channel economics, ordered rules", "In: all module outputs", "Out: SELL / WAIT / INSPECT"),
    ("Farmer dashboard", "10 pages, charts, reports, notifications", "In: REST API", "Out: actionable UI + report"),
]
positions = [(0.55 + i * 3.13, 1.48) for i in range(4)] + [(2.1 + i * 3.13, 3.92) for i in range(3)]
for index, (title, purpose, inp, out) in enumerate(modules):
    x, y = positions[index]
    highlight = index == 5
    card(s, x, y, 3.0, 2.2, fill=AMBER_BG if highlight else WHITE, line=AMBER_LINE if highlight else LINE)
    text(s, x + 0.16, y + 0.14, 2.7, 0.3, f"{index + 1}. {title}", size=10.8, color=AMBER if highlight else NAVY, bold=True, line_spacing=0.95)
    text(s, x + 0.16, y + 0.58, 2.68, 0.5, purpose, size=8.8, color=GRAY, line_spacing=1.02)
    text(s, x + 0.16, y + 1.18, 2.68, 0.28, inp, size=8.2, color=GREEN, bold=True)
    text(s, x + 0.16, y + 1.46, 2.68, 0.28, out, size=8.2, color=SLATE, bold=True)
    if highlight:
        pill(s, x + 1.72, y + 1.84, 1.12, 0.22, "CORE", fill=AMBER, color=WHITE, size=7)
rect(s, 0.6, 6.3, 12.13, 0.45, fill=PALE, line=MINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.14)
text(
    s,
    0.75,
    6.3,
    11.8,
    0.45,
    [
        {
            "text": "Functional view: buyer & transport is a sub-module of Layer 4; the dashboard is Layer 6.  ",
            "bold": False,
            "color": SLATE,
        },
        {
            "text": "The decision engine is pure Python — deterministic and unit-testable.",
            "bold": True,
            "color": DEEP,
        },
    ],
    size=9.0,
    anchor=MSO_ANCHOR.MIDDLE,
    line_spacing=1.0,
)
notes(
    s,
    """The system is split into seven functional modules, and each one has a clear contract.

Modules one and two handle data. Module three is crop health. Module four is yield and market. Module five is buyer and transport. Module six is the decision engine, highlighted here because it consumes every other module's output. Module seven is the dashboard.

The key architectural point is that modules do not reach into each other's internals. The decision engine receives typed dataclasses, not database rows. That is what allows us to test the policy without a server, and it is why the engine can be reused behind a different UI or API.""",
)

# ============================================================ 8 — CROP HEALTH
s = add_slide(prs)
chrome(
    s,
    8,
    "Implementation & Progress: Crop Health",
    "Module 3 · verified",
    "A trained 38-class classifier with Grad-CAM, served in real mode by the API.",
)
card(s, 0.6, 1.45, 5.0, 2.32, fill=WHITE, accent=GREEN)
text(s, 0.8, 1.55, 4.6, 0.24, "DATASET & TRAINING", size=8.5, color=GREEN, bold=True)
facts = [
    ("Dataset", "PlantVillage + PlantDoc, mixed training"),
    ("Field test", "236 labelled PlantDoc images"),
    ("Model", "crop-health-v3.0.0-convnext · convnext_tiny"),
    ("Input", "240 resize · 192 centre crop · 4-view TTA"),
    ("Training", "seed 42 · AMP · 12 epochs · 1,602 s"),
    ("Explainability", "Grad-CAM on last ConvNeXt block"),
]
for index, (label, value) in enumerate(facts):
    y = 1.84 + index * 0.31
    text(s, 0.8, y, 1.1, 0.26, label, size=8.3, color=GRAY, bold=True)
    text(s, 1.95, y, 3.5, 0.26, value, size=8.6, color=NAVY)

metrics = [("0.7161", "field accuracy"), ("0.7093", "field macro-F1"), ("0.8093", "with crop hint"), ("0.9812", "lab baseline")]
for index, (value, label) in enumerate(metrics):
    x = 0.6 + index * 1.27
    card(s, x, 3.9, 1.17, 0.82, fill=PALE, line=MINT)
    text(s, x, 3.97, 1.17, 0.34, value, size=14, color=DEEP, bold=True, align=PP_ALIGN.CENTER)
    text(s, x, 4.32, 1.17, 0.3, label, size=7.4, color=GRAY, align=PP_ALIGN.CENTER)

rect(s, 0.6, 4.9, 5.0, 1.78, fill=AMBER_BG, line=AMBER_LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.05)
text(s, 0.78, 4.98, 4.65, 0.24, "CHANGE CONTROL & LIMITS", size=8, color=AMBER, bold=True)
text(
    s,
    0.78,
    5.24,
    4.65,
    1.35,
    "Later candidates scored 0.6864, 0.6695, 0.6864 and 0.6822 on the field gate; none beat 0.7161, so deployed weights and checksum are unchanged. Grad-CAM is a coarse explanation overlay, not segmentation or a definitive diagnosis.",
    size=8.6,
    color=SLATE,
    line_spacing=1.06,
)

picture(s, "crop-health.png", 5.85, 1.45, 4.15, 3.55)
text(s, 5.85, 5.02, 4.15, 0.22, "Live API result — real model mode with Grad-CAM", size=7.8, color=GRAY, align=PP_ALIGN.CENTER)
picture(s, "gradcam.png", 10.2, 1.45, 1.35, 1.35)
text(s, 10.2, 2.82, 1.35, 0.22, "Grad-CAM overlay", size=7.6, color=GRAY, align=PP_ALIGN.CENTER)
text(s, 10.2, 3.12, 2.55, 1.45, "4-view TTA fixed 9 and broke 3 images versus single view. Low-confidence cases are routed to INSPECT.", size=8.2, color=SLATE, line_spacing=1.05)
text(s, 10.2, 4.95, 2.55, 1.55, "Crop-hint 0.8093 is a serving aid only, not a promotion baseline. Lab images reach 0.9812 but are not field performance.", size=8.2, color=SLATE, line_spacing=1.05)
notes(
    s,
    """Module three is complete and running in real mode.

The deployed artifact is crop-health-v3.0.0-convnext with a ConvNeXt-Tiny backbone. It was trained jointly on PlantVillage and PlantDoc, resized to 240 pixels, centre-cropped to 192, normalised with ImageNet statistics and served with four-view test-time augmentation.

The honest field number is 0.7161 accuracy and 0.7093 macro-F1 on 236 labelled PlantDoc images. Single-view accuracy is 0.6907. With a correct crop hint the serving accuracy is 0.8093, but that is a serving aid, not a promotion baseline. A controlled lab split reaches 0.9812 and is not field performance.

Grad-CAM targets the last ConvNeXt block and uses the first TTA view. The overlay is 55 percent original image and 45 percent heat map. It is a coarse explanation for review, not a segmentation mask or a diagnosis.

Later candidates were rejected because none beat the 0.7161 unconstrained field gate. The deployed weights and SHA-256 checksum remain unchanged.""",
)

# ============================================================ 9 — YIELD & MARKET
s = add_slide(prs)
chrome(
    s,
    9,
    "Implementation & Progress: Yield & Market Intelligence",
    "Module 4 · verified",
    "Chronological validation, explicit uncertainty, and forecasts that refuse to run on insufficient data.",
)
card(s, 0.6, 1.45, 5.95, 5.35, fill=WHITE, accent=GREEN)
text(s, 0.82, 1.55, 5.4, 0.24, "YIELD PREDICTION", size=8.5, color=GREEN, bold=True)
for index, (value, label) in enumerate([("14.7151", "MAE q/ha"), ("0.9533", "R² (2015)"), ("84.92%", "80% coverage")]):
    x = 0.82 + index * 1.9
    card(s, x, 1.85, 1.75, 0.8, fill=PALE, line=MINT)
    text(s, x, 1.9, 1.75, 0.34, value, size=15, color=DEEP, bold=True, align=PP_ALIGN.CENTER)
    text(s, x, 2.25, 1.75, 0.3, label, size=7.6, color=GRAY, align=PP_ALIGN.CENTER)
text(
    s,
    0.82,
    2.78,
    5.45,
    1.1,
    [
        {"text": "Features: ", "bold": True, "color": NAVY},
        {"text": "state, district, crop, season and area; one-hot encoding and scaling inside the training pipeline.", "color": SLATE},
    ],
    size=8.8,
    line_spacing=1.1,
)
text(
    s,
    0.82,
    3.5,
    5.45,
    1.1,
    [
        {"text": "Split: ", "bold": True, "color": NAVY},
        {"text": "train ≤ 2012 (80,000 rows) · validation 2013–14 (9,867, conformal calibration) · test 2015 (305). ExtraTrees won.", "color": SLATE},
    ],
    size=8.8,
    line_spacing=1.1,
)
picture(s, "chart_yield_models.png", 0.82, 4.55, 5.5, 1.95)
text(s, 0.82, 6.5, 5.5, 0.2, "Validation RMSE — lower is better", size=7.4, color=GRAY)

card(s, 6.8, 1.45, 5.93, 5.35, fill=WHITE, accent=GREEN)
text(s, 7.02, 1.55, 5.4, 0.24, "MARKET FORECASTING", size=8.5, color=GREEN, bold=True)
for index, (value, label) in enumerate([("14/14", "crops verified"), ("5/5", "South India states"), ("5", "candidate models")]):
    x = 7.02 + index * 1.9
    card(s, x, 1.85, 1.75, 0.8, fill=PALE, line=MINT)
    text(s, x, 1.9, 1.75, 0.34, value, size=15, color=DEEP, bold=True, align=PP_ALIGN.CENTER)
    text(s, x, 2.25, 1.75, 0.3, label, size=7.6, color=GRAY, align=PP_ALIGN.CENTER)
text(
    s,
    7.02,
    2.78,
    5.45,
    1.05,
    [
        {"text": "Method: ", "bold": True, "color": NAVY},
        {"text": "fit five forecasters on the chronological series, validate on the last tail, refit the best on full history.", "color": SLATE},
    ],
    size=8.8,
    line_spacing=1.1,
)
text(
    s,
    7.02,
    3.48,
    5.45,
    0.8,
    [
        {"text": "Selected: ", "bold": True, "color": NAVY},
        {"text": "Best of five by chronological tail error; refitted on full history; empirical intervals widen with horizon.", "color": SLATE},
    ],
    size=8.8,
    line_spacing=1.1,
)
picture(s, "chart_market_models.png", 7.02, 4.1, 5.45, 1.85)
rect(s, 7.02, 6.05, 5.45, 0.55, fill=PALE, line=MINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
text(
    s,
    7.15,
    6.05,
    5.2,
    0.55,
    "Official rates: 14/14 crops · 5/5 South India states · 0-day freshness on 25 Nov 2026",
    size=8.6,
    color=DEEP,
    bold=True,
    anchor=MSO_ANCHOR.MIDDLE,
)
text(
    s,
    0.6,
    6.82,
    12.13,
    0.18,
    "Limitations: yield has no soil/weather inputs and MAPE is 57.52% on right-skewed small plots; the bundled market window is short and the keyless fallback is about 40 days behind.",
    size=7.4,
    color=GRAY,
    italic=True,
)
notes(
    s,
    """Module four has two halves.

Yield prediction uses only state, district, crop, season and area. The target is quintals per hectare. The split is chronological: train up to 2012 with 80,000 rows, validate on 2013–14 with 9,867 rows for conformal calibration, and test on 2015 with 305 rows. ExtraTrees won validation. On the held-out year it achieved MAE 14.7151 q/ha, R-squared 0.9533 and 84.92 percent coverage for the nominal 80 percent interval.

I will be honest about the weakness: MAPE is 57.52 percent because yields are right-skewed and small plots dominate percentage error. Soil and weather are displayed elsewhere but are not model inputs because the historical dataset has no paired records.

Market forecasting compares five candidates on a chronological tail and refits the best on full history. Empirical intervals widen with horizon, and Sugarcane returns insufficient-data instead of a weak forecast. On 25 November 2026 the official feed returned 14/14 crops and 5/5 South India states with 0-day freshness; the keyless five-state mirror remains a labelled fallback.""",
)

# ============================================================ 10 — DECISION ENGINE
s = add_slide(prs)
chrome(
    s,
    10,
    "Implementation & Progress: Decision Engine & Integration",
    "Module 6 · primary contribution",
    "Deterministic, explainable, Decimal money arithmetic. Every factor is persisted for audit.",
)
card(s, 0.6, 1.45, 5.0, 2.12, fill=WHITE, accent=GREEN)
text(s, 0.8, 1.55, 4.6, 0.24, "BUYER-WISE NET REALIZATION", size=8.5, color=GREEN, bold=True)
text(
    s,
    0.8,
    1.86,
    4.6,
    1.6,
    [
        {"text": "gross = quantity × offered price\n", "color": NAVY},
        {"text": "net = gross − transport − commission − other costs\n", "color": NAVY},
        {"text": "net/q = net ÷ quantity\n", "color": NAVY},
        {"text": "wait = price move − holding − deterioration", "color": NAVY},
    ],
    size=9.6,
    line_spacing=1.28,
    bold=True,
)
text(s, 0.8, 3.18, 4.6, 0.3, "Risk-adjusted ranking: net − λ × offer-risk × gross, λ = 0.5", size=8.2, color=GRAY)

card(s, 0.6, 3.7, 5.0, 2.95, fill=WHITE, accent=GREEN)
text(s, 0.8, 3.8, 4.6, 0.24, "8-COMPONENT RISK (WEIGHTS SUM TO 1.0)", size=8.5, color=GREEN, bold=True)
weights = [
    ("Yield uncertainty", "0.20"),
    ("Price uncertainty", "0.18"),
    ("Crop health", "0.18"),
    ("Market freshness", "0.12"),
    ("Buyer offer", "0.10"),
    ("Data completeness", "0.10"),
    ("Weather", "0.07"),
    ("Transport", "0.05"),
]
for index, (label, value) in enumerate(weights):
    col, row = index % 2, index // 2
    x = 0.8 + col * 2.4
    y = 4.12 + row * 0.34
    text(s, x, y, 1.85, 0.26, label, size=8.4, color=SLATE)
    text(s, x + 1.85, y, 0.45, 0.26, value, size=8.4, color=DEEP, bold=True, align=PP_ALIGN.RIGHT)
text(s, 0.8, 5.52, 4.6, 0.95, "Composite score 0.44 → medium. Risk preference caps the decision separately from the category.", size=8.4, color=GRAY, line_spacing=1.06)

card(s, 5.85, 1.45, 6.88, 1.72, fill=WHITE)
text(s, 6.02, 1.54, 6.5, 0.24, "RECORDED DOCKER SMOKE EXAMPLE — ONION, 392 q", size=8.2, color=GREEN, bold=True)
rows = [
    ("Channel", "Offer ₹/q", "Net ₹/q", "Result"),
    ("Mandi — Ammapet", "6,441", "6,371.67", "SELECTED"),
    ("Nashik Fresh Produce", "6,150", "6,071.75", "rank 2"),
    ("Sahyadri FPC", "6,030", "5,946.94", "rank 3"),
]
col_x = [6.02, 8.35, 9.95, 11.5]
col_w = [2.25, 1.5, 1.45, 1.1]
for row_index, row in enumerate(rows):
    y = 1.82 + row_index * 0.31
    if row_index == 0:
        rect(s, 6.02, y - 0.03, 6.5, 0.3, fill=DEEP)
    elif row_index == 1:
        rect(s, 6.02, y - 0.03, 6.5, 0.3, fill=LIGHT)
    for col_index, value in enumerate(row):
        color = WHITE if row_index == 0 else (DEEP if row_index == 1 else SLATE)
        text(
            s,
            col_x[col_index],
            y,
            col_w[col_index],
            0.26,
            value,
            size=7.9,
            color=color,
            bold=row_index == 0 or (row_index == 1 and col_index == 3),
            align=PP_ALIGN.RIGHT if col_index > 0 else PP_ALIGN.LEFT,
        )

picture(s, "chart_buyer_net.png", 5.85, 3.3, 4.4, 1.85)
text(s, 5.85, 5.18, 4.4, 0.22, "Mandi wins after costs, despite a higher buyer headline offer on some crops.", size=7.6, color=GRAY)

rect(s, 10.45, 3.3, 2.28, 2.28, fill=DEEP, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
text(s, 10.6, 3.42, 2.0, 0.24, "OUTPUT", size=7.6, color=MINT, bold=True)
text(s, 10.6, 3.66, 2.0, 0.45, "SELL", size=20, color=WHITE, bold=True)
text(s, 10.6, 4.15, 2.0, 0.25, "medium risk · policy 1.0.1", size=7.2, color=MINT)
text(s, 10.6, 4.45, 2.0, 0.42, "₹6,371.67", size=16, color=WHITE, bold=True)
text(s, 10.6, 4.86, 2.0, 0.22, "per quintal", size=7.4, color=MINT)
text(s, 10.6, 5.08, 2.0, 0.4, "policy 1.0.1", size=7.2, color=MINT)

rect(s, 5.85, 5.5, 6.88, 1.15, fill=AMBER_BG, line=AMBER_LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.07)
text(s, 6.0, 5.56, 6.6, 0.22, "ORDERED RULES — FIRST MATCH WINS", size=7.8, color=AMBER, bold=True)
text(
    s,
    6.0,
    5.8,
    6.55,
    0.8,
    "INSPECT checks first → WAIT checks next → SELL if net ≥ 0 → reasons recorded. First matching rule wins.",
    size=8.2,
    color=SLATE,
    line_spacing=1.05,
)
text(s, 0.6, 6.72, 12.1, 0.22, "Demo buyer offers are illustrative. Values are a recorded smoke example, not a current market quote.", size=7.6, color=GRAY, italic=True)
notes(
    s,
    """This is the slide I would defend most carefully, because it is the contribution.

For every eligible buyer we compute gross revenue, subtract transport, commission and other selling costs, and divide by quantity. That gives net realization per quintal. We also rank by a risk-adjusted net, so a risky offer does not automatically win.

The table is a recorded Docker smoke example, not a live quote. The mandi nets 6,371.67 rupees per quintal. The best demo buyer offer is 6,150, which nets 6,071 after transport. So the highest headline offer is not the best choice here — this is exactly the mistake the engine prevents.

On the left is the risk model: eight weighted components summing to one. At the bottom are the ordered rules. The first matching rule wins, which makes policy v1.0.1 auditable.

The output is SELL, with 6,371.67 per quintal and medium risk 0.44. The engine is deterministic Python rules, not an LLM, and no farmer field-trial accuracy is claimed.""",
)

# ============================================================ 11 — RESULTS
s = add_slide(prs)
chrome(
    s,
    11,
    "Results — Final Output",
    "Verified 25–27 Nov 2026",
    "Every value below is tied to the final report; screenshots come from the running application.",
)
kpis = [("0.7161", "field accuracy · 4-view"), ("0.9533", "yield R² (2015)"), ("14/14", "official crops verified"), ("SELL", "₹6,371.67/q · risk 0.44")]
for index, (value, label) in enumerate(kpis):
    x = 0.6 + index * 3.06
    card(s, x, 1.42, 2.9, 0.72, fill=PALE, line=MINT)
    text(s, x + 0.12, 1.46, 1.2, 0.38, value, size=15 if index < 3 else 14, color=DEEP, bold=True)
    text(s, x + 0.12, 1.83, 2.65, 0.24, label, size=7.6, color=GRAY)

results = [
    ("crop-health.png", "Crop health", "ConvNeXt-Tiny + Grad-CAM", "236-image field test: 0.7161 accuracy. Grad-CAM is a coarse explanation, not a diagnosis."),
    ("yield.png", "Yield & harvest", "ExtraTrees + 80% interval", "MAE 14.7151 q/ha, R² 0.9533. No soil/weather model inputs."),
    ("market.png", "Market rates", "Official data.gov.in first", "14/14 crops, 5/5 states, 0-day freshness. Keyless fallback is labelled."),
    ("decision-engine.png", "Decision engine", "SELL via mandi", "₹6,371.67/q, risk 0.44 in a recorded example; demo buyers illustrative."),
]
for index, (image, title, subtitle, caption) in enumerate(results):
    col, row = index % 2, index // 2
    x = 0.6 + col * 6.12
    y = 2.3 + row * 2.3
    card(s, x, y, 6.0, 2.12, fill=WHITE)
    picture(s, image, x + 0.1, y + 0.08, 2.35, 1.95)
    text(s, x + 2.55, y + 0.12, 3.3, 0.26, title, size=10.5, color=NAVY, bold=True)
    text(s, x + 2.55, y + 0.4, 3.3, 0.22, subtitle, size=8.4, color=GREEN, bold=True)
    text(s, x + 2.55, y + 0.68, 3.3, 1.3, caption, size=8.1, color=GRAY, line_spacing=1.05)
text(s, 0.6, 6.92, 12.1, 0.2, "Screenshots captured from the running Docker Compose stack; figures are verified against the final report.", size=7.4, color=GRAY, italic=True)
notes(
    s,
    """This slide is the evidence page. Each screenshot is from the running application, and each number is tied to the final report.

Top left is crop health: a 38-class ConvNeXt-Tiny prediction with Grad-CAM. The honest field accuracy is 0.7161 on 236 PlantDoc images. Top right is yield: MAE 14.7151 q/ha, R-squared 0.9533 and an 80 percent conformal interval.

Bottom left is market intelligence: official data.gov.in rates for 14/14 crops and 5/5 South India states with 0-day freshness, plus a labelled five-state fallback. Bottom right is the decision: SELL through the mandi at 6,371.67 rupees per quintal, risk 0.44, from a recorded smoke example.

I have paired each result with its limitation, because a review is not credible if we only show the good numbers. The crop model is weakest on real field photos, the yield model lacks soil and weather, the market window is short, and buyer offers are demo data.

What these results do prove is that the full chain runs: image in, models, database, decision, UI and report.""",
)

# ============================================================ 12 — FUTURE WORK
s = add_slide(prs)
chrome(
    s,
    12,
    "Future Work",
    "Current vs next",
    "The prototype is complete end-to-end; the next phase is evidence, data breadth and field validation.",
)
card(s, 0.6, 1.45, 3.55, 5.35, fill=PALE, line=MINT, accent=GREEN)
text(s, 0.82, 1.58, 3.1, 0.24, "ALREADY IN PLACE", size=8.5, color=GREEN, bold=True)
delivered = [
    "Working 7-layer full stack",
    "ConvNeXt-Tiny + Grad-CAM",
    "Trained yield model + interval",
    "Chronological market forecasts",
    "Buyer & transport comparison",
    "Deterministic decision engine",
    "115 backend + 32 frontend tests",
    "Docker Compose deployment",
]
for index, item in enumerate(delivered):
    text(s, 0.82, 1.92 + index * 0.52, 3.1, 0.45, "✓  " + item, size=9, color=DEEP, bold=True, line_spacing=1.0)

future = [
    ("Expand disease datasets across crops and regions", "Data"),
    ("Improve model generalisation and calibration", "Model"),
    ("Add soil, weather and irrigation to yield features", "Model"),
    ("Expand official mandi coverage to more states", "Data"),
    ("Improve price forecasting with arrivals and rainfall", "Model"),
    ("Integrate real buyer networks", "Data"),
    ("Add route-based logistics optimisation", "Deploy"),
    ("Validate recommendations with farmer field trials", "Evidence"),
    ("Add IoT soil sensors where available", "Deploy"),
    ("Deploy for field-level evaluation", "Evidence"),
]
text(s, 4.45, 1.42, 4.0, 0.24, "NEXT MILESTONES", size=8.5, color=GREEN, bold=True)
for index, (item, tag) in enumerate(future):
    col, row = index % 2, index // 2
    x = 4.45 + col * 4.22
    y = 1.72 + row * 0.98
    card(s, x, y, 4.05, 0.84, fill=WHITE)
    badge(s, x + 0.1, y + 0.2, 0.32, str(index + 1), fill=LIGHT, color=DEEP, size=8)
    text(s, x + 0.52, y + 0.1, 2.8, 0.62, item, size=8.6, color=NAVY, bold=True, line_spacing=0.98)
    pill(s, x + 3.12, y + 0.5, 0.82, 0.22, tag.upper(), fill=PALE, color=GREEN, size=6)
text(s, 4.45, 6.45, 8.2, 0.3, "Phase 2 will prioritise field data and validation over adding new model families.", size=8.6, color=GRAY, italic=True)
notes(
    s,
    """The left column is what already exists, so future work is clearly separated from current capability.

The next phase has four themes. Data: broader disease images, wider official mandi coverage and real buyer networks. Models: better calibration, richer yield features including soil and weather, and price models with arrivals and rainfall. Deployment: route-based logistics and IoT sensors where available. Evidence: field trials and a real deployment.

If a faculty member asks what is missing, this is the honest list. The prototype proves the integration; the next phase proves the impact.""",
)

# ============================================================ 13 — CONCLUSION
s = add_slide(prs)
rect(s, 0, 0, W, 0.07, fill=DEEP)
text(s, 0.6, 0.3, 6.0, 0.24, "CONCLUSION", size=9, color=GREEN, bold=True)
text(s, 0.6, 0.55, 12.0, 0.6, "Conclusion", size=28, color=NAVY, bold=True)
text(
    s,
    0.6,
    1.02,
    11.0,
    0.32,
    "From prediction to a defensible decision.",
    size=14,
    color=GREEN,
    bold=True,
    italic=True,
)
text(
    s,
    0.6,
    1.45,
    6.9,
    1.4,
    "AgriTwin bridges the gap between agricultural prediction and practical decision-making by combining crop health, yield, market intelligence, buyer comparison and transport into one uncertainty-aware recommendation.",
    size=11.5,
    color=SLATE,
    line_spacing=1.15,
)
contrib = [
    ("Uncertainty-aware", "Every recommendation carries intervals, completeness and an 8-component risk score."),
    ("Explainable", "Ordered rules, factor contributions and assumptions — never a black-box answer."),
    ("Economically grounded", "Buyer vs mandi net realization in Decimal rupees, not headline price."),
]
for index, (title, body) in enumerate(contrib):
    x = 0.6 + index * 2.35
    card(s, x, 2.95, 2.2, 1.75, fill=WHITE, accent=GREEN)
    text(s, x + 0.15, 3.05, 1.95, 0.5, title, size=10.5, color=DEEP, bold=True, line_spacing=0.98)
    text(s, x + 0.15, 3.62, 1.95, 0.95, body, size=8.2, color=GRAY, line_spacing=1.05)

rect(s, 7.75, 1.25, 4.98, 4.1, fill=DEEP, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.04)
text(s, 8.05, 1.5, 4.4, 0.3, "THE CLOSING LINE", size=8.5, color=MINT, bold=True)
text(s, 8.05, 1.9, 4.35, 1.2, "From Fields to\nBetter Decisions.", size=27, color=WHITE, bold=True, line_spacing=1.02)
rect(s, 8.05, 3.2, 1.5, 0.04, fill=GREEN)
text(s, 8.05, 3.45, 4.3, 0.6, "AgriTwin · Final · 27 November 2026", size=9.5, color=MINT)
text(s, 8.05, 4.0, 4.3, 0.3, "Thank you  ·  Questions welcome", size=14, color=WHITE, bold=True)

rect(s, 0, 6.55, W, 0.95, fill=PALE)
text(s, 0.6, 6.72, 12.1, 0.55, "The prototype is running end-to-end today; the next phase is field validation and broader data.", size=10.5, color=DEEP, bold=True, italic=True)
text(s, 10.6, 7.12, 2.1, 0.22, f"13/{TOTAL}", size=8, color=GRAY, align=PP_ALIGN.RIGHT)
notes(
    s,
    """To conclude: AgriTwin is not another prediction dashboard. It is a decision-support system that treats uncertainty as a first-class input.

The three contributions are uncertainty-awareness, explainability and economic grounding. The engine compares net realization, not headline prices, and it shows the farmer why.

The prototype is running end-to-end today: trained models, real data, a tested decision engine, a complete UI and a Docker deployment. The next phase is field validation.

From fields to better decisions. Thank you — I am happy to take questions.""",
)

prs.save(OUT)
print(f"saved {OUT} ({OUT.stat().st_size:,} bytes, {len(prs.slides)} slides)")

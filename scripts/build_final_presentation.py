"""Build the final AgriTwin presentation as a PowerPoint file.

Run from the repository root:
    backend\\.venv\\Scripts\\python.exe scripts\\build_final_presentation.py

The slide text is kept here so the PPTX can be regenerated from one source.
All numbers are taken from docs/AgriTwin_Mini_Project_Report.md.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "presentation" / "AgriTwin_Final_Presentation.pptx"

NAVY = RGBColor(11, 31, 51)
TEAL = RGBColor(18, 168, 157)
GREEN = RGBColor(46, 125, 50)
ORANGE = RGBColor(245, 158, 11)
LIGHT = RGBColor(246, 250, 252)
CARD = RGBColor(255, 255, 255)
TEXT = RGBColor(51, 65, 85)
MUTED = RGBColor(100, 116, 139)
WHITE = RGBColor(255, 255, 255)

SW = 13.333
SH = 7.5


def base_slide(prs: Presentation, dark: bool = False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = NAVY if dark else LIGHT
    return slide


def add_text(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    size: float = 16,
    color: RGBColor = TEXT,
    bold: bool = False,
    align=PP_ALIGN.LEFT,
    valign=MSO_ANCHOR.TOP,
    italic: bool = False,
):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = align
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.italic = italic
    p.font.color.rgb = color
    p.font.name = "Aptos"
    return box


def add_paragraphs(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    items: list[str],
    size: float = 15,
    color: RGBColor = TEXT,
    bullet: bool = True,
    gap: float = 8,
):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(0.04)
    tf.margin_right = Inches(0.04)
    tf.margin_top = Inches(0.02)
    for index, item in enumerate(items):
        p = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        p.text = f"•  {item}" if bullet else item
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.font.name = "Aptos"
        p.space_after = Pt(gap)
    return box


def add_header(slide, kicker: str, title: str, subtitle: str = ""):
    add_text(slide, 0.6, 0.35, 12.1, 0.3, kicker.upper(), 11, TEAL, True)
    add_text(slide, 0.6, 0.7, 12.1, 0.55, title, 27, NAVY, True)
    if subtitle:
        add_text(slide, 0.6, 1.28, 12.1, 0.5, subtitle, 14, MUTED)


def add_footer(slide, page: int, dark: bool = False):
    color = RGBColor(180, 200, 215) if dark else MUTED
    add_text(slide, 0.6, 7.05, 8.5, 0.25, "AgriTwin  |  Final Presentation", 9, color)
    add_text(slide, 11.6, 7.05, 1.1, 0.25, f"{page:02d}/14", 9, color, align=PP_ALIGN.RIGHT)


def add_card(slide, x, y, w, h, title, body, accent=TEAL, title_size=15, body_size=12.5):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = CARD
    shape.line.color.rgb = accent
    shape.line.width = Pt(1.5)
    add_text(slide, x + 0.18, y + 0.14, w - 0.36, 0.35, title, title_size, accent, True)
    add_text(slide, x + 0.18, y + 0.55, w - 0.36, h - 0.65, body, body_size, TEXT)


def add_pill(slide, x, y, w, text, color=TEAL, size=12):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(0.42)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    add_text(
        slide,
        x,
        y + 0.06,
        w,
        0.3,
        text,
        size,
        WHITE,
        True,
        align=PP_ALIGN.CENTER,
    )


def add_image_fit(slide, path: Path, x, y, max_w, max_h):
    with Image.open(path) as im:
        iw, ih = im.size
    scale = min(max_w / iw, max_h / ih)
    w, h = iw * scale, ih * scale
    px = x + (max_w - w) / 2
    py = y + (max_h - h) / 2
    slide.shapes.add_picture(str(path), Inches(px), Inches(py), Inches(w), Inches(h))


def add_table(slide, x, y, w, h, headers, rows, col_widths):
    shape = slide.shapes.add_table(len(rows) + 1, len(headers), Inches(x), Inches(y), Inches(w), Inches(h))
    table = shape.table
    for i, cw in enumerate(col_widths):
        table.columns[i].width = Inches(cw)
    for c, head in enumerate(headers):
        cell = table.cell(0, c)
        cell.text = head
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = WHITE
    for r, row in enumerate(rows, start=1):
        for c, value in enumerate(row):
            cell = table.cell(r, c)
            cell.text = str(value)
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if r % 2 else RGBColor(236, 244, 248)
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(10.5)
            p.font.color.rgb = TEXT
    return table


def build() -> None:
    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)

    # 1 — Title
    s = base_slide(prs, dark=True)
    add_text(s, 0.8, 0.55, 11.7, 0.3, "A MINI PROJECT REPORT  •  FINAL PRESENTATION", 12, RGBColor(125, 211, 252), True)
    add_text(s, 0.8, 1.05, 11.7, 1.0, "AgriTwin", 44, WHITE, True)
    add_text(s, 0.8, 2.05, 11.7, 0.7, "Real-Data Digital Twin for Crop Health, Yield, Market and Decision Support", 20, RGBColor(125, 211, 252))
    add_text(s, 0.8, 3.0, 11.7, 0.35, "Submitted to OSMANIA UNIVERSITY", 15, WHITE, True)
    add_text(s, 0.8, 3.4, 11.7, 0.3, "Bachelor of Engineering in Computer Science and Engineering (AI & ML)", 13, WHITE)
    add_text(s, 0.8, 4.05, 11.7, 0.3, "By", 12, MUTED)
    add_text(s, 0.8, 4.4, 11.7, 0.95, "Aravapalli Jashwanth 245523748071\nKolluru Sai Vamshi 245523748097\nMandula Sri Sreshta 245523748103", 14, WHITE)
    add_text(s, 0.8, 5.55, 11.7, 0.6, "Under the guidance of Mrs. D . Padmaja Usha Rani, Assistant Professor", 14, WHITE, True)
    add_text(s, 0.8, 6.05, 11.7, 0.5, "Department of Computer Science and Engineering  |  Keshav Memorial Engineering College  |  July 2026", 11, RGBColor(180, 200, 215))
    add_footer(s, 1, dark=True)

    # 2 — Problem
    s = base_slide(prs)
    add_header(s, "Why this project", "Four disconnected signals decide one farmer’s income", "AgriTwin brings them together instead of showing four separate predictions.")
    cards = [
        ("01  Crop disease", "Losses grow before symptoms are obvious; expert advice is not immediate.", TEAL),
        ("02  Uncertain yield", "One number hides the range that actually determines financial risk.", GREEN),
        ("03  Volatile prices", "Mandi prices move daily and differ by market, district and variety.", ORANGE),
        ("04  Hidden costs", "Transport, commission and other charges change the real take-home price.", RGBColor(37, 99, 235)),
    ]
    for i, (title, body, accent) in enumerate(cards):
        add_card(s, 0.6 + i * 3.12, 2.05, 2.9, 2.3, title, body, accent)
    add_pill(s, 0.6, 4.85, 3.0, "PROJECT VISION", TEAL)
    add_text(s, 0.6, 5.45, 12.0, 0.9, "“Transform agricultural data into explainable and economically informed farming decisions.”", 19, NAVY, True)
    add_text(s, 0.6, 6.35, 12.0, 0.4, "The decision engine is the research contribution — not another prediction screen.", 13, MUTED)
    add_footer(s, 2)

    # 3 — What we built
    s = base_slide(prs)
    add_header(s, "What we solve", "One explainable recommendation, not five disconnected predictions", "The system ends with a single clear action: SELL, WAIT or INSPECT.")
    add_card(s, 0.6, 1.95, 4.0, 4.55, "Problem statement", "Farmers combine a leaf photo, a yield guess, yesterday’s price, a phone offer and a transport quote by hand. Individual predictions do not automatically produce the best economic decision.", ORANGE, 16, 14)
    add_card(s, 4.85, 1.95, 7.85, 4.55, "Objectives achieved", "1  Image-based crop-health detection\n2  Grad-CAM visual explanation\n3  Yield estimate with 80% interval\n4  Market price forecast\n5  District/state live mandi rates\n6  Buyer and transport comparison\n7  Buyer-wise net realisation\n8  Uncertainty-aware risk score\n9  SELL / WAIT / INSPECT decision", TEAL, 16, 14)
    add_footer(s, 3)

    # 4 — Architecture
    s = base_slide(prs)
    add_header(s, "System design", "Final architecture", "Farmer-facing web app, FastAPI services, persistent storage and external evidence.")
    boxes = [
        (0.6, 2.0, 2.1, "Farmer", "Leaf photo\nFarm + crop details", TEAL),
        (3.0, 2.0, 2.3, "Web App", "React + Vite\nDashboard pages", TEAL),
        (5.6, 2.0, 2.5, "FastAPI Backend", "Auth · Crop health\nYield · Market · Reports", GREEN),
        (8.4, 1.55, 4.25, "Storage & evidence", "PostgreSQL 16\nUploads disk · ML artifacts", RGBColor(37, 99, 235)),
        (8.4, 3.0, 4.25, "External APIs", "data.gov.in · Open-Meteo\nOSRM · keyless fallback", ORANGE),
    ]
    for x, y, w, title, body, accent in boxes:
        add_card(s, x, y, w, 1.5, title, body, accent, 14, 11.5)
    for x in (2.75, 5.35, 8.15):
        add_text(s, x, 2.45, 0.28, 0.4, "→", 22, NAVY, True, align=PP_ALIGN.CENTER)
    add_card(s, 4.4, 4.95, 4.4, 1.5, "Decision engine v1.0.1", "Deterministic ordered rules; risk + net realisation; INSPECT → WAIT → SELL.", GREEN, 15, 12)
    add_text(s, 9.15, 5.2, 3.4, 0.9, "Output shown first:\none clear decision\nwith evidence behind it", 14, NAVY, True)
    add_footer(s, 4)

    # 5 — Workflow
    s = base_slide(prs)
    add_header(s, "Methodology", "End-to-end workflow", "Seven stages run today; decisions are only as good as the weakest upstream input.")
    steps = [
        ("1  Collect", "Leaf photo, farm, crop, district, buyer and transport details."),
        ("2  Prepare", "Validate inputs; resize/crop image; encode and scale tabular features."),
        ("3  Crop health", "ConvNeXt-Tiny + 4-view TTA; Grad-CAM explains the prediction."),
        ("4  Yield & market", "ExtraTrees with 80% interval; chronological price forecast."),
        ("5  Buyer & transport", "Eligibility, distance, trips and cost; net realisation per buyer."),
        ("6  Risk fusion", "Eight risk components, data completeness and confidence."),
        ("7  Decide", "Ordered rules produce SELL / WAIT / INSPECT with reasons."),
    ]
    for i, (title, body) in enumerate(steps):
        col = 0 if i < 4 else 1
        row = i if i < 4 else i - 4
        x = 0.6 + col * 6.4
        y = 1.95 + row * 1.18
        add_card(s, x, y, 6.0, 1.0, title, body, TEAL if col == 0 else GREEN, 13, 11.5)
    add_footer(s, 5)

    # 6 — Crop health
    s = base_slide(prs)
    add_header(s, "Module 3", "Crop health and Grad-CAM", "A real 38-class classifier with an explanation overlay — not a segmentation mask.")
    add_card(s, 0.6, 1.95, 3.9, 4.6, "Deployed model", "crop-health-v3.0.0-convnext\nconvnext_tiny backbone\n38 classes · 14 crop species\n192 px centre crop from 240\n4-view test-time augmentation\nsoft crop prior α = 0.95", TEAL, 15, 13)
    add_card(s, 4.7, 1.95, 3.9, 4.6, "Measured field evidence", "236 PlantDoc field images\n4-view accuracy 0.7161\n4-view macro-F1 0.7093\nsingle-view 0.6907\nwith correct crop hint 0.8093\ncontrolled lab baseline 0.9812", GREEN, 15, 13)
    add_card(s, 8.8, 1.95, 3.9, 4.6, "Grad-CAM", "Last ConvNeXt block\nFirst/base TTA view\nHeat map normalised 0–1\n55% image + 45% heat map\nServed as gradcam_url\nCoarse explanation only", ORANGE, 15, 13)
    add_text(s, 0.6, 6.65, 12.0, 0.3, "Low-confidence predictions are routed to INSPECT; the overlay is evidence for review, not a definitive diagnosis.", 12, MUTED, italic=True)
    add_footer(s, 6)

    # 7 — Yield
    s = base_slide(prs)
    add_header(s, "Module 4", "Yield intelligence", "Chronological validation and an 80% interval — reported with its limits.")
    add_card(s, 0.6, 1.95, 4.0, 4.5, "What the model uses", "yield-v1.0.0 · ExtraTrees\nIndia district-level crop production, 1997–2015\nTrain ≤ 2012: 80,000 rows\nValidation 2013–2014: 9,867 rows\nTest 2015: 305 rows\nInputs: state, district, crop, season, area only", TEAL, 15, 13)
    add_card(s, 4.85, 1.95, 3.9, 4.5, "Held-out results", "MAE 14.7151 q/ha\nRMSE 36.5968 q/ha\nR² 0.9533\nMAPE 57.52%\n80% conformal coverage 84.92%\nmean half-width 17.4339 q/ha", GREEN, 15, 13)
    add_card(s, 9.0, 1.95, 3.7, 4.5, "Honest limits", "Soil and weather are displayed but are not model inputs — the historical dataset has no paired records. Percentage error is inflated on small plots, so MAPE is reported openly.", ORANGE, 15, 13)
    add_footer(s, 7)

    # 8 — Market
    s = base_slide(prs)
    add_header(s, "Module 4", "Market intelligence and live mandi rates", "Official provenance first; fallback sources are clearly labelled.")
    add_card(s, 0.6, 1.95, 4.0, 4.5, "Live rates", "data.gov.in / Agmarknet daily + variety-wise resources.\nDistrict first, then state fallback.\nTelangana and Andhra Pradesh use official data.gov.in rates.\nCache 15 minutes; Refresh bypasses it.\n30-second upstream timeout.", TEAL, 15, 13)
    add_card(s, 4.85, 1.95, 3.9, 4.5, "Keyless fallback", "Five states only:\nMaharashtra, Uttar Pradesh, Punjab, Madhya Pradesh, Karnataka.\nObserved about 40 days behind the official feed.\nAlways labelled as non-official.", ORANGE, 15, 13)
    add_card(s, 9.0, 1.95, 3.7, 4.5, "Forecast", "Five candidate forecasters compared on a chronological tail. Best model refitted; empirical residual intervals widen with horizon. Sugarcane returns insufficient-data instead of a weak forecast.", GREEN, 15, 13)
    add_text(s, 0.6, 6.6, 12.0, 0.4, "Verified on 25–26 Nov 2026: 14/14 crops, 5/5 South India states, 0-day freshness, district rows filtered correctly.", 12, MUTED, italic=True)
    add_footer(s, 8)

    # 9 — Decision engine
    s = base_slide(prs)
    add_header(s, "Primary contribution", "Uncertainty-aware decision engine", "Deterministic rule policy v1.0.1 — explainable, testable and auditable.")
    add_pill(s, 0.6, 1.9, 2.1, "INSPECT")
    add_pill(s, 2.9, 1.9, 2.1, "WAIT", GREEN)
    add_pill(s, 5.2, 1.9, 2.1, "SELL", ORANGE)
    add_text(s, 7.6, 1.9, 5.1, 0.5, "First matching rule wins; reasons are stored with every decision.", 13, MUTED)
    add_card(s, 0.6, 2.6, 5.9, 3.8, "What it combines", "Crop-health severity and confidence\nYield interval and data completeness\nMarket freshness and price direction\nHarvest readiness from crop calendar\nBuyer offer risk and transport cost\nNet realisation after selling costs\nEight weighted risk components (sum = 1.0)", TEAL, 15, 13)
    add_card(s, 6.75, 2.6, 5.95, 3.8, "Recorded example — not a live quote", "Docker smoke example: SELL via mandi.\nNet realisation ₹6,371.67 per quintal.\nComposite risk 0.44 → medium.\nPolicy version 1.0.1.\nNo farmer field-trial accuracy is claimed for the engine.\nDemo buyer offers are labelled as illustrative.", GREEN, 15, 13)
    add_footer(s, 9)

    # 10 — Results
    s = base_slide(prs)
    add_header(s, "Evaluation", "Results at a glance", "Every number is shown with the condition under which it was measured.")
    add_table(
        s,
        0.6,
        1.95,
        12.1,
        4.55,
        ["Check", "Verified value", "Context"],
        [
            ["Crop health — field", "0.7161 accuracy / 0.7093 macro-F1", "236 PlantDoc images, 4-view TTA"],
            ["Crop health — with crop hint", "0.8093 accuracy / 0.8024 macro-F1", "Serving aid only, not a promotion baseline"],
            ["Crop health — lab", "0.9812 accuracy", "Controlled images; not field performance"],
            ["Yield — held-out 2015", "MAE 14.7151 q/ha · R² 0.9533", "80% interval coverage 84.92%"],
            ["Official rates", "14/14 crops · 5/5 South India states", "0-day freshness on 25 Nov 2026"],
            ["Software", "115 backend + 32 frontend tests", "Production build and API smoke passed"],
        ],
        [3.3, 4.4, 4.4],
    )
    add_text(s, 0.6, 6.6, 12.0, 0.35, "Demo mode, fallback sources and illustrative buyers are explicitly labelled in the product; no hidden approximations are presented as real data.", 12, MUTED, italic=True)
    add_footer(s, 10)

    # 11 — Working UI
    s = base_slide(prs)
    add_header(s, "Working system", "Screens from the running application", "The prototype is live end to end in Docker Compose.")
    assets = ROOT / "docs" / "video" / "assets"
    screens = [
        (assets / "dashboard.png", "Dashboard"),
        (assets / "crop-health.png", "Crop Health + Grad-CAM"),
        (assets / "market.png", "Market rates"),
        (assets / "yield.png", "Yield"),
    ]
    for i, (path, caption) in enumerate(screens):
        if not path.exists():
            continue
        x = 0.6 + i * 3.12
        add_card(s, x, 2.0, 2.9, 4.6, caption, "", TEAL, 13, 11)
        add_image_fit(s, path, x + 0.18, 2.55, 2.54, 3.55)
    add_footer(s, 11)

    # 12 — Data and APIs
    s = base_slide(prs)
    add_header(s, "Evidence", "Data, APIs and provenance", "Real sources are recorded; the personal data.gov.in key is never stored in the repository.")
    add_card(s, 0.6, 1.95, 3.9, 4.6, "Datasets", "PlantVillage + PlantDoc for crop health (mixed training; 236 field test images).\nIndia district-level crop production 1997–2015 for yield.\nHistorical mandi series for forecasting.\nProvenance and licences in backend/app/data/DATASETS.md.", TEAL, 15, 13)
    add_card(s, 4.7, 1.95, 3.9, 4.6, "External APIs", "data.gov.in / Agmarknet daily and variety-wise resources.\nKeyless Mandi API mirror for five states.\nOpen-Meteo weather and geocoding.\nOSRM routing with geodesic fallback.", GREEN, 15, 13)
    add_card(s, 8.8, 1.95, 3.9, 4.6, "Safety", "Demo mode and fallback sources are labelled.\nModel mode is shown in the UI.\nNo API key, .env file or backend log is committed.\nGrad-CAM is not presented as a diagnosis.", ORANGE, 15, 13)
    add_footer(s, 12)

    # 13 — Future scope
    s = base_slide(prs)
    add_header(s, "Future scope", "What comes next", "Phase 2 prioritises field evidence and broader data over adding new model families.")
    future = [
        "Validate recommendations with farmer field trials",
        "Add soil, weather and irrigation features to yield",
        "Expand disease data across crops and regions",
        "Improve calibration and low-confidence handling",
        "Integrate verified live buyer networks",
        "Add route-based logistics optimisation",
        "Improve forecasts with arrivals and rainfall",
        "Explore IoT soil sensing where available",
    ]
    for i, item in enumerate(future):
        col = i % 2
        row = i // 2
        x = 0.6 + col * 6.4
        y = 2.0 + row * 1.1
        add_card(s, x, y, 6.0, 0.92, f"{i + 1:02d}", item, TEAL if col == 0 else GREEN, 12, 12)
    add_footer(s, 13)

    # 14 — Conclusion
    s = base_slide(prs, dark=True)
    add_text(s, 0.8, 0.6, 11.7, 0.35, "CONCLUSION", 12, RGBColor(125, 211, 252), True)
    add_text(s, 0.8, 1.1, 11.7, 0.8, "From prediction to a defensible decision", 33, WHITE, True)
    add_text(s, 0.8, 2.15, 11.7, 0.9, "AgriTwin combines crop health, yield, market intelligence, buyer comparison and transport into one uncertainty-aware recommendation.", 18, RGBColor(210, 230, 240))
    for i, (title, body) in enumerate([
        ("Uncertainty-aware", "Intervals, completeness and a weighted risk score travel with every recommendation."),
        ("Explainable", "Ordered rules, Grad-CAM evidence and recorded reasons — never a black-box answer."),
        ("Economically grounded", "Buyer versus mandi net realisation in rupees, not headline price."),
    ]):
        x = 0.8 + i * 4.15
        add_card(s, x, 3.4, 3.85, 2.1, title, body, TEAL if i == 0 else (GREEN if i == 1 else ORANGE), 14, 12)
    add_text(s, 0.8, 5.95, 11.7, 0.5, "The prototype runs end to end today. The next phase is field validation.", 17, WHITE, True)
    add_text(s, 0.8, 6.55, 11.7, 0.4, "Thank you  •  Questions welcome", 15, RGBColor(125, 211, 252))
    add_footer(s, 14, dark=True)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUTPUT)
    print(f"Saved {OUTPUT.relative_to(ROOT)} with {len(prs.slides)} slides")


if __name__ == "__main__":
    build()

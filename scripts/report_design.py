"""Shared document generator for the AgriTwin mini project report.

The report content lives in scripts/build_mini_report.py.  This module renders
that content to both DOCX (python-docx) and PDF (ReportLab) and generates the
architecture/UML figures with Matplotlib so no stale image assets are needed.
"""

from __future__ import annotations

import html
import os
import re
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, FancyBboxPatch

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)


# ---------------------------------------------------------------------------
# Block helpers
# ---------------------------------------------------------------------------

Block = tuple


def h1(text: str) -> Block:
    return ("h1", text)


def h2(text: str) -> Block:
    return ("h2", text)


def h3(text: str) -> Block:
    return ("h3", text)


def p(text: str) -> Block:
    return ("p", text)


def bullets(items: Sequence[str]) -> Block:
    return ("bullets", list(items))


def numbered(items: Sequence[str]) -> Block:
    return ("numbered", list(items))


def table(caption: str, headers: Sequence[str], rows: Sequence[Sequence[str]], widths: Sequence[float] | None = None) -> Block:
    return ("table", caption, list(headers), [list(r) for r in rows], list(widths) if widths else None)


def code(caption: str, text: str) -> Block:
    return ("code", caption, text.strip("\n"))


def figure(caption: str, path: str | Path, width: float = 6.25) -> Block:
    return ("fig", caption, str(path), width)


def spacer(points: float = 10) -> Block:
    return ("spacer", points)


def page_break() -> Block:
    return ("pb",)


def centered(text: str, style: str = "p") -> Block:
    return ("center", text, style)


def _inline_md(text: str) -> list[tuple[str, bool]]:
    """Split **bold** markdown into (text, bold) runs."""
    parts: list[tuple[str, bool]] = []
    for i, chunk in enumerate(re.split(r"\*\*", text)):
        if chunk:
            parts.append((chunk, i % 2 == 1))
    return parts


def _md_html(text: str) -> str:
    out: list[str] = []
    for chunk, bold in _inline_md(text):
        escaped = html.escape(chunk)
        out.append(f"<b>{escaped}</b>" if bold else escaped)
    return "".join(out)


# ---------------------------------------------------------------------------
# Figure generation
# ---------------------------------------------------------------------------

BLUE = "#DCEBFA"
GREEN = "#E4F4E7"
ORANGE = "#FFF0D6"
PURPLE = "#EDE4FA"
GREY = "#F2F4F7"
EDGE = "#315A82"


def _figure(title: str, width: float = 10.0, height: float = 6.0):
    fig, ax = plt.subplots(figsize=(width, height), dpi=180)
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.axis("off")
    ax.set_title(title, fontsize=14, fontweight="bold", color="#17365D", pad=14)
    return fig, ax


def _box(ax, x: float, y: float, w: float, h: float, text: str, color: str = BLUE, size: float = 8.8) -> None:
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.035,rounding_size=0.08",
        linewidth=1.2,
        edgecolor=EDGE,
        facecolor=color,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, color="#14263B")


def _arrow(ax, x1: float, y1: float, x2: float, y2: float, label: str = "", color: str = "#4A4A4A") -> None:
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.15,
            color=color,
            shrinkA=2,
            shrinkB=2,
        )
    )
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, label, ha="center", va="bottom", fontsize=7.4, color="#444")


def _diamond(ax, x: float, y: float, w: float, h: float, text: str, color: str = ORANGE) -> None:
    pts = [(x, y + h / 2), (x + w / 2, y + h), (x + w, y + h / 2), (x + w / 2, y)]
    xs, ys = zip(*pts)
    ax.fill(xs, ys, facecolor=color, edgecolor=EDGE, linewidth=1.2)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8.2)


def _save(fig, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=0.6)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


def make_diagrams(out_dir: str | Path) -> dict[str, str]:
    """Generate all figures used by the report and return caption -> path."""
    out = Path(out_dir)
    figs: dict[str, str] = {}

    # System architecture ---------------------------------------------------
    fig, ax = _figure("Fig 4.1  System Architecture of AgriTwin", 10, 6.4)
    layers = [
        (5.0, 0.15, "CLIENT LAYER", "Browser UI: HTML5 / CSS3 / React\nFarmer-first forms, maps and dashboards", BLUE),
        (3.65, 1.75, "API & SECURITY LAYER", "FastAPI / REST · JWT auth · CORS\nValidation · rate limiting · audit logs", GREEN),
        (2.35, 3.35, "SERVICE LAYER", "Crop Health · Yield · Market Rates · Decisions\nWeather · Transport · Chat · Evidence export", ORANGE),
        (1.05, 4.95, "DATA & MODEL LAYER", "SQLite · model.pt · yield model.joblib\nVerified CSVs · data.gov.in · Open-Meteo · OSRM", PURPLE),
    ]
    for x, y, title, body, color in layers:
        _box(ax, x, y, 7.4, 1.05, f"{title}\n{body}", color, 8.6)
    for y1, y2 in [(1.20, 1.75), (2.80, 3.35), (4.40, 4.95)]:
        _arrow(ax, 8.7, y1 + 0.25, 8.7, y2 - 0.05)
    figs["architecture"] = _save(fig, out / "fig_4_1_architecture.png")

    # Use case --------------------------------------------------------------
    fig, ax = _figure("Fig 5.1  Use Case Diagram of AgriTwin", 10, 6.2)
    ax.add_patch(FancyBboxPatch((3.2, 0.7), 6.3, 4.9, boxstyle="round,pad=0.04", linewidth=1.2, edgecolor=EDGE, facecolor="#FAFCFF"))
    ax.text(6.35, 5.25, "AgriTwin System", ha="center", fontsize=10, fontweight="bold")
    use_cases = [
        (3.65, 4.05, "Upload leaf photo"),
        (6.75, 4.05, "View crop health"),
        (3.65, 2.85, "Check live mandi rate"),
        (6.75, 2.85, "Compare buyer offers"),
        (3.65, 1.65, "Get farm decision"),
        (6.75, 1.65, "Ask AI advisor"),
    ]
    ax.plot([2.05, 2.05], [1.2, 4.9], color="#333", lw=1.2)
    ax.plot([2.05, 2.05], [3.05, 3.05], color="#333", lw=1.2)
    ax.add_patch(Circle((2.05, 5.05), 0.24, fill=False, ec="#333", lw=1.2))
    ax.plot([2.05, 2.05], [4.81, 3.3], color="#333", lw=1.2)
    ax.plot([1.55, 2.55], [4.45, 3.95], color="#333", lw=1.2)
    ax.plot([1.55, 2.55], [2.15, 2.65], color="#333", lw=1.2)
    ax.text(2.05, 5.48, "Farmer / Field Officer", ha="center", fontsize=9, fontweight="bold")
    for x, y, label in use_cases:
        ax.add_patch(Ellipse((x + 1.1, y + 0.35), 2.2, 0.7, facecolor=BLUE, edgecolor=EDGE, lw=1.1))
        ax.text(x + 1.1, y + 0.35, label, ha="center", va="center", fontsize=8.3)
    for x, y, _ in use_cases:
        _arrow(ax, 2.55, 3.05 if y > 3 else 3.05, x, y + 0.35)
    figs["usecase"] = _save(fig, out / "fig_5_1_usecase.png")

    # Sequence --------------------------------------------------------------
    fig, ax = _figure("Fig 5.2  Sequence Diagram - Crop Health to Decision", 10, 6.2)
    lifelines = [("Farmer", 1.2), ("Frontend", 3.2), ("FastAPI", 5.2), ("Services", 7.2), ("Data / APIs", 9.0)]
    for name, x in lifelines:
        _box(ax, x - 0.75, 5.35, 1.5, 0.42, name, GREEN if x < 5 else BLUE, 8.2)
        ax.plot([x, x], [0.8, 5.35], ls="--", lw=0.9, color="#888")
    steps = [
        (1.2, 3.2, 4.95, "1. Enter farm + upload leaf"),
        (3.2, 5.2, 4.55, "2. POST /crop-health/predict"),
        (5.2, 7.2, 4.15, "3. Run ConvNeXT + TTA"),
        (7.2, 9.0, 3.75, "4. Load model.pt / prior"),
        (5.2, 3.2, 3.25, "5. JSON: disease + confidence"),
        (3.2, 5.2, 2.85, "6. POST /decision/rank"),
        (5.2, 7.2, 2.45, "7. Market + weather + yield"),
        (7.2, 9.0, 2.05, "8. Verify live rates / cache"),
        (5.2, 3.2, 1.55, "9. Ranked actions + evidence"),
        (3.2, 1.2, 1.10, "10. Farmer-first decision shown"),
    ]
    for x1, x2, y, label in steps:
        _arrow(ax, x1, y, x2, y, label)
    figs["sequence"] = _save(fig, out / "fig_5_2_sequence.png")

    # Activity --------------------------------------------------------------
    fig, ax = _figure("Fig 5.3  Activity Diagram - AgriTwin Processing Flow", 10, 6.2)
    _box(ax, 4.05, 5.35, 1.9, 0.45, "START", GREEN, 9)
    _box(ax, 3.55, 4.55, 2.9, 0.6, "Farmer enters farm details", BLUE)
    _diamond(ax, 4.05, 3.45, 1.9, 0.85, "Leaf photo\nuploaded?")
    _box(ax, 0.65, 2.35, 2.6, 0.65, "Crop-health inference\n(4-view TTA)", ORANGE)
    _box(ax, 6.75, 2.35, 2.6, 0.65, "Skip image branch\n(keep other signals)", GREY)
    _box(ax, 3.55, 2.15, 2.9, 0.65, "Yield + live mandi rates", BLUE)
    _diamond(ax, 4.05, 1.05, 1.9, 0.8, "Decision\nconfidence OK?")
    _box(ax, 0.65, 0.25, 3.0, 0.55, "Show top action + evidence", GREEN)
    _box(ax, 6.35, 0.25, 3.0, 0.55, "Ask for one more input", ORANGE)
    _arrow(ax, 5.0, 5.35, 5.0, 5.15)
    _arrow(ax, 5.0, 4.55, 5.0, 4.30)
    _arrow(ax, 5.0, 3.45, 2.0, 3.0, "yes")
    _arrow(ax, 5.0, 3.45, 8.05, 3.0, "no")
    _arrow(ax, 1.95, 2.35, 3.55, 2.48)
    _arrow(ax, 8.05, 2.35, 6.45, 2.48)
    _arrow(ax, 5.0, 2.15, 5.0, 1.85)
    _arrow(ax, 4.05, 1.45, 2.15, 0.8, "yes")
    _arrow(ax, 5.95, 1.45, 7.85, 0.8, "no")
    figs["activity"] = _save(fig, out / "fig_5_3_activity.png")

    # Class -----------------------------------------------------------------
    fig, ax = _figure("Fig 5.4  Class Diagram - Core AgriTwin Objects", 10, 6.2)
    classes = [
        (0.6, 3.65, 2.6, 1.5, "FarmerProfile\n+crop / state / soil\n+irrigation / sowing", BLUE),
        (3.7, 3.65, 2.6, 1.5, "CropHealthResult\n+class_name\n+confidence\n+evidence", GREEN),
        (6.8, 3.65, 2.6, 1.5, "LiveRatesResponse\n+provider\n+is_demo\n+points[]", ORANGE),
        (0.6, 1.15, 2.6, 1.5, "DecisionRequest\n+profile\n+options\n+constraints", PURPLE),
        (3.7, 1.15, 2.6, 1.5, "DecisionService\n+rank_actions()\n+explain()\n+guardrails", BLUE),
        (6.8, 1.15, 2.6, 1.5, "EvidenceBundle\n+source_ids\n+freshness\n+licence", GREEN),
    ]
    for x, y, w, h, text, color in classes:
        _box(ax, x, y, w, h, text, color, 8.2)
    _arrow(ax, 3.2, 4.4, 3.7, 4.4, "uses")
    _arrow(ax, 6.3, 4.4, 6.8, 4.4, "feeds")
    _arrow(ax, 3.2, 1.9, 3.7, 1.9, "input")
    _arrow(ax, 6.3, 1.9, 6.8, 1.9, "returns")
    _arrow(ax, 5.0, 3.65, 5.0, 2.65, "produces")
    figs["class"] = _save(fig, out / "fig_5_4_class.png")

    # Component -------------------------------------------------------------
    fig, ax = _figure("Fig 5.5  Component Diagram - AgriTwin Modules", 10, 5.6)
    comps = [
        (0.5, 3.45, 2.7, 0.95, "Frontend\nfarmer-first UI", BLUE),
        (3.65, 3.45, 2.7, 0.95, "API Controller\nFastAPI routers", GREEN),
        (6.8, 3.45, 2.7, 0.95, "Auth + Config\nJWT, env, keys", PURPLE),
        (0.5, 1.55, 2.7, 0.95, "Crop Health\npredict + Grad-CAM", ORANGE),
        (3.65, 1.55, 2.7, 0.95, "Market + Decision\nrates, ranking", BLUE),
        (6.8, 1.55, 2.7, 0.95, "SQLite + Cache\nTTL 900 s", GREEN),
    ]
    for x, y, w, h, text, color in comps:
        _box(ax, x, y, w, h, text, color, 8.5)
    _arrow(ax, 3.2, 3.92, 3.65, 3.92)
    _arrow(ax, 6.35, 3.92, 6.8, 3.92)
    _arrow(ax, 5.0, 3.45, 1.85, 2.50)
    _arrow(ax, 5.0, 3.45, 5.0, 2.50)
    _arrow(ax, 5.0, 2.50, 8.15, 2.50)
    figs["component"] = _save(fig, out / "fig_5_5_component.png")

    # Deployment ------------------------------------------------------------
    fig, ax = _figure("Fig 5.6  Deployment Diagram - AgriTwin Runtime", 10, 5.4)
    nodes = [
        (0.45, 3.55, 2.1, 1.0, "Farmer browser\nHTTPS", BLUE),
        (3.0, 3.55, 2.2, 1.0, "Vite / Nginx\nstatic UI", GREEN),
        (5.65, 3.55, 2.2, 1.0, "FastAPI + Uvicorn\nDocker / cloud", ORANGE),
        (8.3, 3.55, 1.25, 1.0, "SQLite\nmodels", PURPLE),
        (2.0, 1.15, 2.6, 0.9, "data.gov.in\nofficial mandi APIs", BLUE),
        (5.0, 1.15, 2.6, 0.9, "Open-Meteo · OSRM\nweather / route", GREEN),
        (8.0, 1.15, 1.75, 0.9, "Gemini\nadvisor", ORANGE),
    ]
    for x, y, w, h, text, color in nodes:
        _box(ax, x, y, w, h, text, color, 8.2)
    _arrow(ax, 2.55, 4.05, 3.0, 4.05)
    _arrow(ax, 5.2, 4.05, 5.65, 4.05)
    _arrow(ax, 7.85, 4.05, 8.3, 4.05)
    _arrow(ax, 6.75, 3.55, 3.3, 2.05, "verified rates")
    _arrow(ax, 6.75, 3.55, 6.3, 2.05, "weather / route")
    _arrow(ax, 6.75, 3.55, 8.5, 2.05, "chat")
    figs["deployment"] = _save(fig, out / "fig_5_6_deployment.png")

    return figs


# ---------------------------------------------------------------------------
# DOCX renderer
# ---------------------------------------------------------------------------

def _set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def _set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def _set_page_number(section, fmt: str, start: int) -> None:
    sect_pr = section._sectPr
    pg = sect_pr.find(qn("w:pgNumType"))
    if pg is None:
        pg = OxmlElement("w:pgNumType")
        sect_pr.append(pg)
    pg.set(qn("w:fmt"), fmt)
    pg.set(qn("w:start"), str(start))


def _add_page_field(paragraph) -> None:
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    txt = OxmlElement("w:t")
    txt.text = "1"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    for node in (fld_begin, instr, fld_sep, txt, fld_end):
        run._r.append(node)


def _docx_section(doc: Document, fmt: str, start: int) -> None:
    section = doc.sections[-1]
    section.top_margin = Inches(0.9)
    section.bottom_margin = Inches(0.85)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)
    _set_page_number(section, fmt, start)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.text = ""
    r = footer.add_run("AgriTwin Mini Project Report  |  ")
    r.font.size = Pt(8)
    r.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    _add_page_field(footer)
    for run in footer.runs:
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)


def _docx_blocks(doc: Document, blocks: Iterable[Block]) -> None:
    for block in blocks:
        kind = block[0]
        if kind == "h1":
            para = doc.add_heading(block[1], level=1)
            para.paragraph_format.space_before = Pt(16)
            para.paragraph_format.space_after = Pt(8)
            para.paragraph_format.keep_with_next = True
            for run in para.runs:
                run.font.color.rgb = RGBColor(0x17, 0x36, 0x5D)
        elif kind == "h2":
            para = doc.add_heading(block[1], level=2)
            para.paragraph_format.space_before = Pt(11)
            para.paragraph_format.space_after = Pt(5)
            para.paragraph_format.keep_with_next = True
            for run in para.runs:
                run.font.color.rgb = RGBColor(0x24, 0x4E, 0x7A)
        elif kind == "h3":
            para = doc.add_heading(block[1], level=3)
            para.paragraph_format.space_before = Pt(8)
            para.paragraph_format.space_after = Pt(4)
        elif kind == "p":
            para = doc.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            para.paragraph_format.space_after = Pt(6)
            for text, bold in _inline_md(block[1]):
                run = para.add_run(text)
                run.bold = bold
        elif kind in ("bullets", "numbered"):
            style = "List Bullet" if kind == "bullets" else "List Number"
            for item in block[1]:
                para = doc.add_paragraph(style=style)
                para.paragraph_format.space_after = Pt(3)
                for text, bold in _inline_md(item):
                    run = para.add_run(text)
                    run.bold = bold
        elif kind == "table":
            _, caption, headers, rows, widths = block
            cap = doc.add_paragraph()
            cap.paragraph_format.space_before = Pt(6)
            cap.paragraph_format.space_after = Pt(3)
            r = cap.add_run(caption)
            r.bold = True
            r.font.size = Pt(9.5)
            t = doc.add_table(rows=1, cols=len(headers))
            t.style = "Table Grid"
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            hdr = t.rows[0]
            _set_repeat_table_header(hdr)
            for i, text in enumerate(headers):
                cell = hdr.cells[i]
                cell.text = ""
                para = cell.paragraphs[0]
                for chunk, bold in _inline_md(text):
                    run = para.add_run(chunk)
                    run.bold = True
                    run.font.size = Pt(9)
                _set_cell_shading(cell, "DCEBFA")
            for row in rows:
                cells = t.add_row().cells
                for i, value in enumerate(row):
                    cells[i].text = ""
                    para = cells[i].paragraphs[0]
                    for chunk, bold in _inline_md(str(value)):
                        run = para.add_run(chunk)
                        run.bold = bold
                        run.font.size = Pt(8.7)
            if widths:
                for row in t.rows:
                    for i, w in enumerate(widths):
                        row.cells[i].width = Inches(w)
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
        elif kind == "code":
            _, caption, text = block
            cap = doc.add_paragraph()
            cap.paragraph_format.space_after = Pt(3)
            r = cap.add_run(caption)
            r.bold = True
            r.font.size = Pt(9.5)
            for line in text.split("\n"):
                para = doc.add_paragraph()
                para.paragraph_format.left_indent = Inches(0.22)
                para.paragraph_format.space_after = Pt(0)
                para.paragraph_format.line_spacing = 1.0
                run = para.add_run(line if line else " ")
                run.font.name = "Consolas"
                run.font.size = Pt(8)
                _set_cell_shading(para._p.getparent(), "FFFFFF") if False else None
            doc.add_paragraph().paragraph_format.space_after = Pt(2)
        elif kind == "fig":
            _, caption, path, width = block
            para = doc.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para.paragraph_format.space_before = Pt(6)
            para.paragraph_format.space_after = Pt(2)
            para.add_run().add_picture(path, width=Inches(width))
            cap = doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap.paragraph_format.space_after = Pt(8)
            r = cap.add_run(caption)
            r.bold = True
            r.font.size = Pt(9)
        elif kind == "center":
            _, text, style_name = block
            para = doc.add_paragraph(style=style_name if style_name in ("Title", "Subtitle") else None)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for chunk, bold in _inline_md(text):
                run = para.add_run(chunk)
                run.bold = bold or style_name.lower() == "bold"
                if style_name.lower() == "bold":
                    run.font.size = Pt(12)
        elif kind == "spacer":
            doc.add_paragraph().paragraph_format.space_after = Pt(block[1])
        elif kind == "pb":
            doc.add_page_break()


def build_docx(path: str | Path, cover: Sequence[Block], front: Sequence[Block], body: Sequence[Block]) -> None:
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.paragraph_format.line_spacing = 1.12
    normal.paragraph_format.space_after = Pt(5)
    for name, size in (("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11)):
        st = doc.styles[name]
        st.font.name = "Calibri"
        st.font.size = Pt(size)
        st.font.bold = True

    _docx_section(doc, "lowerRoman", 1)
    _docx_blocks(doc, cover)
    _docx_blocks(doc, front)

    doc.add_section(WD_SECTION.NEW_PAGE)
    _docx_section(doc, "decimal", 1)
    _docx_blocks(doc, body)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)


# ---------------------------------------------------------------------------
# PDF renderer
# ---------------------------------------------------------------------------

_FONT_REGISTERED = False


def _register_fonts() -> tuple[str, str, str]:
    global _FONT_REGISTERED
    if not _FONT_REGISTERED:
        font_dir = Path(r"C:\Windows\Fonts")
        candidates = {
            "AgriSans": font_dir / "segoeui.ttf",
            "AgriSans-Bold": font_dir / "segoeuib.ttf",
            "AgriMono": font_dir / "consola.ttf",
        }
        for name, path in candidates.items():
            if path.exists():
                pdfmetrics.registerFont(TTFont(name, str(path)))
            else:
                fallback = "Courier" if "Mono" in name else "Helvetica"
                pdfmetrics.registerFont(TTFont(name, str(font_dir / (fallback + ".ttf")))) if (font_dir / (fallback + ".ttf")).exists() else None
        _FONT_REGISTERED = True
    return "AgriSans", "AgriSans-Bold", "AgriMono"


def _pdf_styles():
    sans, bold, mono = _register_fonts()
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("ReportTitle", parent=base["Title"], fontName=bold, fontSize=22, leading=27, alignment=TA_CENTER, textColor=colors.HexColor("#17365D"), spaceAfter=16),
        "subtitle": ParagraphStyle("ReportSubtitle", parent=base["Normal"], fontName=sans, fontSize=13, leading=18, alignment=TA_CENTER, spaceAfter=10),
        "h1": ParagraphStyle("H1", parent=base["Heading1"], fontName=bold, fontSize=15, leading=19, textColor=colors.HexColor("#17365D"), spaceBefore=12, spaceAfter=7, keepWithNext=True),
        "h2": ParagraphStyle("H2", parent=base["Heading2"], fontName=bold, fontSize=12, leading=16, textColor=colors.HexColor("#244E7A"), spaceBefore=9, spaceAfter=5, keepWithNext=True),
        "h3": ParagraphStyle("H3", parent=base["Heading3"], fontName=bold, fontSize=10.5, leading=14, spaceBefore=7, spaceAfter=4, keepWithNext=True),
        "p": ParagraphStyle("Body", parent=base["BodyText"], fontName=sans, fontSize=9.6, leading=13.6, alignment=TA_JUSTIFY, spaceAfter=6),
        "center": ParagraphStyle("Center", parent=base["Normal"], fontName=sans, fontSize=10, leading=14, alignment=TA_CENTER, spaceAfter=5),
        "centerbold": ParagraphStyle("CenterBold", parent=base["Normal"], fontName=bold, fontSize=12, leading=16, alignment=TA_CENTER, spaceBefore=4, spaceAfter=8),
        "bullet": ParagraphStyle("Bullet", parent=base["BodyText"], fontName=sans, fontSize=9.6, leading=13.4, leftIndent=14, bulletIndent=4, spaceAfter=3),
        "number": ParagraphStyle("Number", parent=base["BodyText"], fontName=sans, fontSize=9.6, leading=13.4, leftIndent=16, bulletIndent=4, spaceAfter=3),
        "caption": ParagraphStyle("Caption", parent=base["Normal"], fontName=bold, fontSize=8.8, leading=11, alignment=TA_CENTER, spaceBefore=3, spaceAfter=7),
        "code": ParagraphStyle("Code", parent=base["Code"], fontName=mono, fontSize=7.6, leading=9.6, backColor=colors.HexColor("#F4F6F8"), borderPadding=6, leftIndent=4, spaceAfter=8),
        "table": ParagraphStyle("Table", parent=base["Normal"], fontName=sans, fontSize=8.1, leading=10.5),
        "tablehdr": ParagraphStyle("TableHeader", parent=base["Normal"], fontName=bold, fontSize=8.2, leading=10.5, textColor=colors.HexColor("#17365D")),
    }
    return styles


def _pdf_footer(canvas, doc, roman: bool) -> None:
    canvas.saveState()
    canvas.setFont("AgriSans", 7.5)
    canvas.setFillColor(colors.HexColor("#666666"))
    n = canvas.getPageNumber()
    label = f"{n}" if not roman else _roman(n)
    canvas.drawCentredString(A4[0] / 2, 0.42 * inch, f"AgriTwin Mini Project Report  |  {label}")
    canvas.restoreState()


def _roman(n: int) -> str:
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for value, sym in vals:
        while n >= value:
            out += sym
            n -= value
    return out


def _pdf_blocks(blocks: Sequence[Block], styles) -> list:
    flow: list = []
    for block in blocks:
        kind = block[0]
        if kind == "h1":
            flow.append(Paragraph(_md_html(block[1]), styles["h1"]))
        elif kind == "h2":
            flow.append(Paragraph(_md_html(block[1]), styles["h2"]))
        elif kind == "h3":
            flow.append(Paragraph(_md_html(block[1]), styles["h3"]))
        elif kind == "p":
            flow.append(Paragraph(_md_html(block[1]), styles["p"]))
        elif kind == "bullets":
            for item in block[1]:
                flow.append(Paragraph(_md_html(item), styles["bullet"], bulletText="•"))
        elif kind == "numbered":
            for idx, item in enumerate(block[1], start=1):
                flow.append(Paragraph(_md_html(item), styles["number"], bulletText=f"{idx}."))
        elif kind == "table":
            _, caption, headers, rows, widths = block
            data = [[Paragraph(_md_html(str(h)), styles["tablehdr"]) for h in headers]]
            for row in rows:
                data.append([Paragraph(_md_html(str(v)), styles["table"]) for v in row])
            avail = 7.0 * inch
            if widths:
                total = sum(widths)
                col_widths = [avail * w / total for w in widths]
            else:
                col_widths = [avail / len(headers)] * len(headers)
            t = Table(data, colWidths=col_widths, repeatRows=1, hAlign="CENTER")
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCEBFA")),
                        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#7A93AC")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFCFF")]),
                    ]
                )
            )
            flow.append(KeepTogether([Paragraph(_md_html(caption), styles["caption"]), t, Spacer(1, 8)]))
        elif kind == "code":
            _, caption, text = block
            flow.append(Paragraph(_md_html(caption), styles["caption"]))
            flow.append(Preformatted(text, styles["code"]))
            flow.append(Spacer(1, 6))
        elif kind == "fig":
            _, caption, path, width = block
            img = Image(path)
            img.drawWidth = width * inch
            img.drawHeight = img.drawWidth * img.imageHeight / img.imageWidth
            flow.append(KeepTogether([img, Paragraph(_md_html(caption), styles["caption"])]))
        elif kind == "center":
            _, text, style_name = block
            key = "title" if style_name.lower() == "title" else "subtitle" if style_name.lower() == "subtitle" else "centerbold" if style_name.lower() == "bold" else "center"
            flow.append(Paragraph(_md_html(text), styles[key]))
        elif kind == "spacer":
            flow.append(Spacer(1, block[1]))
        elif kind == "pb":
            flow.append(PageBreak())
    return flow


def build_markdown(path: str | Path, cover: Sequence[Block], front: Sequence[Block], body: Sequence[Block]) -> None:
    """Render the same blocks to a single GitHub-flavoured Markdown file."""

    def render(blocks: Sequence[Block]) -> list[str]:
        out: list[str] = []
        for block in blocks:
            kind = block[0]
            if kind == "h1":
                out.extend([f"# {block[1]}", ""])
            elif kind == "h2":
                out.extend([f"## {block[1]}", ""])
            elif kind == "h3":
                out.extend([f"### {block[1]}", ""])
            elif kind == "p":
                out.extend([block[1], ""])
            elif kind == "bullets":
                out.extend([f"- {item}" for item in block[1]] + [""])
            elif kind == "numbered":
                out.extend([f"{i}. {item}" for i, item in enumerate(block[1], start=1)] + [""])
            elif kind == "table":
                _, caption, headers, rows, _widths = block
                if caption:
                    out.extend([f"**{caption}**", ""])
                head = "| " + " | ".join(str(h).replace("|", "\\|").replace("\n", "<br>") for h in headers) + " |"
                sep = "| " + " | ".join("---" for _ in headers) + " |"
                lines = [head, sep]
                for row in rows:
                    lines.append("| " + " | ".join(str(v).replace("|", "\\|").replace("\n", "<br>") for v in row) + " |")
                out.extend(lines + [""])
            elif kind == "code":
                _, caption, text = block
                if caption:
                    out.extend([f"**{caption}**", ""])
                out.extend(["```python", text, "```", ""])
            elif kind == "fig":
                _, caption, image_path, _width = block
                name = Path(image_path).name
                out.extend([f"![{caption}](figures/{name})", "", f"*{caption}*", ""])
            elif kind == "center":
                _, text, style_name = block
                if style_name.lower() == "title":
                    out.extend([f"# {text}", ""])
                elif style_name.lower() == "bold":
                    out.extend([f"## {text}", ""])
                else:
                    out.extend([f"> **{text}**" if style_name.lower() == "subtitle" else f"> {text}", ""])
            elif kind == "pb":
                out.extend(["---", ""])
            elif kind == "spacer":
                continue
        return out

    lines: list[str] = []
    lines.extend(render(cover))
    lines.extend(render(front))
    lines.extend(render(body))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def build_pdf(path: str | Path, cover: Sequence[Block], front: Sequence[Block], body: Sequence[Block]) -> None:
    _register_fonts()
    styles = _pdf_styles()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    frame = Frame(0.85 * inch, 0.7 * inch, A4[0] - 1.7 * inch, A4[1] - 1.55 * inch, id="normal")
    doc = BaseDocTemplate(str(path), pagesize=A4, title="AgriTwin Mini Project Report", author="Aravapalli Jashwanth, Kolluru Sai Vamshi, Mandula Sri Sreshta")
    doc.addPageTemplates(
        [
            PageTemplate(id="front", frames=[frame], onPage=lambda c, d: _pdf_footer(c, d, True)),
            PageTemplate(id="body", frames=[frame], onPage=lambda c, d: _pdf_footer(c, d, False)),
        ]
    )
    flow: list = []
    flow.extend(_pdf_blocks(cover, styles))
    flow.extend(_pdf_blocks(front, styles))
    flow.append(NextPageTemplate("body"))
    flow.append(PageBreak())
    flow.extend(_pdf_blocks(body, styles))
    doc.build(flow)

"""Validate the generated deck: slide count, text bounds, image presence, overflow."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import ImageFont
from pptx import Presentation
from pptx.util import Emu

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "presentation" / "AgriTwin_Project_Review_1.pptx"
EMU_IN = 914400

REG = "C:/Windows/Fonts/segoeui.ttf"
BOLD = "C:/Windows/Fonts/segoeuib.ttf"


def wrap_height(shape) -> tuple[float, float]:
    """Approximate rendered text height in inches."""
    width_in = shape.width / EMU_IN - 0.06
    total = 0.0
    for paragraph in shape.text_frame.paragraphs:
        text = "".join(run.text for run in paragraph.runs)
        if not text:
            total += 0.12
            continue
        size = max((run.font.size.pt if run.font.size else 12) for run in paragraph.runs)
        bold = any(run.font.bold for run in paragraph.runs)
        font = ImageFont.truetype(BOLD if bold else REG, int(size * 4))
        # greedy wrap at ~4x resolution, then convert back
        words = text.split()
        lines, current = 1, ""
        limit = width_in * 4 * 72
        for word in words:
            candidate = (current + " " + word).strip()
            if font.getlength(candidate) <= limit:
                current = candidate
            else:
                lines += 1
                current = word
        spacing = paragraph.line_spacing or 1.0
        total += lines * size * 1.2 * spacing / 72
        total += (paragraph.space_after.pt / 72) if paragraph.space_after else 0
    return total, shape.height / EMU_IN


def main() -> int:
    prs = Presentation(DECK)
    problems = 0
    print(f"slides: {len(prs.slides)}")
    for index, slide in enumerate(prs.slides, start=1):
        pictures = sum(1 for shape in slide.shapes if shape.shape_type == 13)
        texts = [shape for shape in slide.shapes if shape.has_text_frame and shape.text_frame.text.strip()]
        title = max(texts, key=lambda shape: max((r.font.size.pt if r.font.size else 0) for p in shape.text_frame.paragraphs for r in p.runs) if texts else 0)
        title_text = title.text_frame.text.strip().split("\n")[0][:70]
        overflow = []
        for shape in texts:
            needed, available = wrap_height(shape)
            if needed > available * 1.08 and needed - available > 0.06:
                overflow.append((shape.text_frame.text.strip().split("\n")[0][:38], round(needed, 2), round(available, 2)))
        offslide = [
            shape.name
            for shape in slide.shapes
            if shape.left < 0 or shape.top < 0 or shape.left + shape.width > prs.slide_width + 10000 or shape.top + shape.height > prs.slide_height + 10000
        ]
        status = "OK" if not overflow and not offslide else "CHECK"
        print(f"{index:02d} [{status}] pictures={pictures} shapes={len(slide.shapes)} title={title_text!r}")
        if overflow:
            problems += len(overflow)
            for item in overflow:
                print(f"     overflow {item[0]!r}: needs {item[1]}in, box {item[2]}in")
        if offslide:
            problems += len(offslide)
            print(f"     off-slide: {offslide[:3]}")
    print(f"potential problems: {problems}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

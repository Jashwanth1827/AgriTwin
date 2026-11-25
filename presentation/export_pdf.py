"""Export the deck to PDF with PowerPoint and verify page count / blank pages."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "presentation" / "AgriTwin_Project_Review_1.pptx"
PDF = ROOT / "presentation" / "AgriTwin_Project_Review_1.pdf"

ppSaveAsPDF = 32


def export() -> None:
    import win32com.client  # type: ignore

    app = win32com.client.Dispatch("PowerPoint.Application")
    app.Visible = True
    presentation = app.Presentations.Open(str(DECK), WithWindow=False)
    try:
        presentation.SaveAs(str(PDF), ppSaveAsPDF)
    finally:
        presentation.Close()
        app.Quit()
    print(f"exported {PDF} ({PDF.stat().st_size:,} bytes)")


def verify() -> int:
    try:
        import fitz  # type: ignore
    except ImportError:
        print("PyMuPDF not installed; skipping page inspection")
        return 0
    document = fitz.open(PDF)
    print(f"pages: {document.page_count}")
    problems = 0
    for index, page in enumerate(document, start=1):
        pixmap = page.get_pixmap(dpi=72)
        samples = pixmap.samples
        unique = len(set(samples))
        text = page.get_text().strip()
        status = "OK"
        if unique < 12 or len(text) < 20:
            status = "BLANK?"
            problems += 1
        first = text.split("\n")[0][:60] if text else "(no text)"
        print(f"{index:02d} [{status}] colors={unique} chars={len(text)} first={first!r}")
    return problems


if __name__ == "__main__":
    if "--verify" not in sys.argv:
        export()
    sys.exit(verify())

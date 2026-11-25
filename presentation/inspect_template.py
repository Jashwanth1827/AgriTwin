import re
import sys
from pptx import Presentation
from pptx.util import Emu

path = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\arvap\Downloads\AgriTwin_Project_Review_Revised (2).pptx"
prs = Presentation(path)

print("FILE:", path)
print("slides:", len(prs.slides), "size:", round(Emu(prs.slide_width).inches, 2), "x", round(Emu(prs.slide_height).inches, 2))

master = prs.slide_masters[0]
print("MASTER shapes:", [(str(sh.shape_type), sh.name) for sh in master.shapes])

for lay in master.slide_layouts:
    pics = [sh.name for sh in lay.shapes if sh.shape_type == 13]
    txts = [sh.text_frame.text.strip() for sh in lay.shapes if sh.has_text_frame and sh.text_frame.text.strip()]
    print("LAYOUT", repr(lay.name), "pics:", pics, "placeholders:", len(lay.placeholders), "text:", txts[:3])

theme = master.part.part_related_by("http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme")
xml = theme.blob.decode("utf8")
print("theme:", re.search(r'name="([^"]+)"', xml).group(1))
print("scheme colors:", re.findall(r"<a:(dk1|lt1|dk2|lt2|accent1|accent2|accent3|accent4|accent5|accent6)>.*?val=\"([0-9A-Fa-f]{6})\"", xml))
print("major latin:", re.findall(r"<a:majorFont>.*?<a:latin typeface=\"([^\"]*)\"", xml, re.S))
print("minor latin:", re.findall(r"<a:minorFont>.*?<a:latin typeface=\"([^\"]*)\"", xml, re.S))

for i, slide in enumerate(prs.slides, 1):
    print("=" * 20, "SLIDE", i)
    print("  layout:", slide.slide_layout.name)
    for sh in slide.shapes:
        kind = str(sh.shape_type)
        if sh.has_text_frame and sh.text_frame.text.strip():
            print("  T", sh.name, "|", sh.text_frame.text.strip().replace("\n", " / ")[:300])
        elif sh.shape_type == 13:
            print("  P", sh.name, "|", round(Emu(sh.width).inches, 2), "x", round(Emu(sh.height).inches, 2))

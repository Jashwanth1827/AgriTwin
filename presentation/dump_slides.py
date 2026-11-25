import sys
from pptx import Presentation

path = sys.argv[1]
prs = Presentation(path)
wanted = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else range(1, len(prs.slides) + 1)

for i, slide in enumerate(prs.slides, 1):
    if i not in wanted:
        continue
    print("=" * 30, "SLIDE", i)
    for sh in slide.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip():
            print("---", sh.name, "---")
            print(sh.text_frame.text.strip())

"""Generate natural Indian-English narration for the AgriTwin Instagram Reel."""

from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

ASSETS = Path(__file__).resolve().parent / "assets"
VOICE = "en-IN-NeerjaNeural"
RATE = "+22%"

LINES = [
    "At sunrise, a farmer has three questions.",
    "Crop sick? Harvest? Where should I sell?",
    "AgriTwin puts the answers in one place.",
    "One screen shows crop health, yield, and a clear sell or wait decision.",
    "A leaf photo says what needs attention.",
    "The harvest comes with an honest range, not a fake exact number.",
    "Real mandi rates near his farm help him sell better. AgriTwin, crop to cash.",
]


async def main() -> None:
    for i, line in enumerate(LINES):
        path = ASSETS / f"voice_{i}.mp3"
        await edge_tts.Communicate(line, VOICE, rate=RATE).save(str(path))
        print(f"{path.name}: {len(line)} chars")


if __name__ == "__main__":
    asyncio.run(main())

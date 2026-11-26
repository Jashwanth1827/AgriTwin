# AgriTwin Instagram Reel — farmer story with VFX

**Output:** `AgriTwin_Instagram_Reel.mp4`  
**Format:** 1080×1920 vertical, 24 fps, H.264/AAC, exactly 30.00 seconds.  
**Voice:** Natural Indian-English neural voice (`en-IN-NeerjaNeural`) generated with `edge-tts`.  
**Style:** Animated sunrise field, moving light rays, drifting particles, scan-line VFX, pulsing price highlights, animated counters and large readable app screenshots.

## Story beat

The reel follows one farmer from sunrise to selling decision: three questions in the morning, one app that answers them, a leaf scan, an honest yield range and real mandi prices near his farm.

## Scene plan

| Time | Visual / VFX | On-screen text | Narration |
|---|---|---|---|
| 00:00–00:03.4 | Animated sunrise field, rotating sun rays, drifting golden particles, title fades in | “A farmer’s day starts with questions.” | “At sunrise, a farmer has three questions.” |
| 00:03.4–00:08.0 | Three cards pop in one by one with bounce animation | “Is my crop sick?” / “What will I harvest?” / “Where should I sell?” | “Crop sick? Harvest? Where should I sell?” |
| 00:08.0–00:11.1 | Logo reveal with zoom, orbiting particles, four pills fly in | “One app. Every field answer.” | “AgriTwin puts the answers in one place.” |
| 00:11.1–00:16.3 | Dashboard screenshot with slow push-in, glowing decision highlight, SELL badge | “One screen. One clear decision.” / “DECISION FIRST” | “One screen shows crop health, yield, and a clear sell or wait decision.” |
| 00:16.3–00:19.3 | Crop Health screenshot with moving scan line and pulsing highlight | “A leaf photo becomes an answer.” / “NEEDS ATTENTION · 93% confidence” | “A leaf photo says what needs attention.” |
| 00:19.3–00:23.6 | Yield screenshot with animated three-bar range and label reveal | “Plan with a range, not a guess.” / “331–453 q” | “The harvest comes with an honest range, not a fake exact number.” |
| 00:23.6–00:30.0 | Market screenshot, glowing price card, ₹0→₹15 counter, floating ₹ particles, final brand card | “Real mandi rates near his farm.” / “₹15/kg” / “AgriTwin — crop-to-cash decisions” | “Real mandi rates near his farm help him sell better. AgriTwin, crop to cash.” |

## Real screenshots used

Captured from `http://127.0.0.1:5173` with the seeded demo account.

- `assets/dashboard.png` — health, yield and latest decision in one view.
- `assets/crop-health.png` — leaf screening result with plain-language attention label.
- `assets/yield.png` — yield estimate with an 80% uncertainty range.
- `assets/market.png` — “Best nearby price today” with district-first government mandi rows.

Demo farms and scans are labelled as demo data in the application. Market prices and historical yield data shown in the app come from real public government feeds.

## Regenerate

```powershell
# 1. Generate natural Indian-English narration clips.
python docs\video\generate_voice.py

# 2. Align narration to the scene plan, render frames with VFX and encode the MP4.
python docs\video\build_reel.py
```

`edge-tts` provides the voice; `imageio-ffmpeg` provides the FFmpeg binary. No `.env`, API key, backend log or deployed crop-health artifact is used by the video build.

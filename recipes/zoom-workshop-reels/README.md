# Zoom workshop → reels

Turns a long Zoom recording into vertical reels in two formats:
- **face** — Collier's full camera, fixed 9:16 crop (no tracking, no shake).
- **split** — slide on top + Collier's Zoom tile below on navy (`A`, the approved look), or tile on
  top + slide below on light grey (`B`). Split clips alternate A/B.

Only Collier's face and voice. Participants, their names, client-result slides and the phone-number
slide are left out by clip choice and checked by the gates below.

## Project folder (`PROJECT=...`)
    source.mp4                 # the recording (a symlink is fine)
    tx/ws.json                 # Groq whisper-large-v3 verbose_json with word timestamps
    work/layout.json           # per-second layout map (C=Collier cam, S=share w/ Collier tile, o/s=other)
    work/lowres.rgb            # 1 fps 192x108 frames used for the layout map + QC
    scripts/clips.json         # the clip list (see clips.example.json)
    overrides.json             # hand settings: face crops, per-segment crops, hand-checked cut points
    deliver/                   # finished reels land here

## Steps
1. **Transcribe** — 16 kHz mono mp3 → Groq `whisper-large-v3`, `timestamp_granularities[]=word`.
2. **Layout map** — 1 fps frames: share = black letterbox on the left edge; Collier cam = close to a
   median Collier frame; Collier's tile = close to a reference crop of the tile. Check flags by eye —
   Collier moving his laptop reads as "other".
3. **Pick clips** — read the transcript; write `clips.json`. Each part is
   `[approx_start, "first words", approx_end, "last words"]`. End on a finished thought.
4. `resolve.py` — anchors each part to exact word indices and prints the text + any layout problems.
5. **Face crops** — grid a frame per clip, set `face_x` (centre x in the 1920 frame) in `overrides.json`.
6. `build.py [clip ...]` — waveform-snapped cuts, silence tightening, layout, captions mapped from the
   source word stamps (spoken order), two-pass −14 LUFS, burn.
7. `qc.py` — Collier-only gate at 5 fps + loudness + 5-frame strips in `frames/qc/`.
8. `verify_text.py [clip ...]` — transcribes every clip and diffs it against the intended words.
   Any extra word at a start, end or join = fix it (add a hand-checked `bound` in `overrides.json`).

## Zoom-specific numbers (in `build.py`)
`SLIDE = (221, 170, 1419, 767)` and `THUMB = (1650, 76, 254, 140)` are for a 1920x1080 Zoom
recording with a shared window and the speaker tile top-right. Re-measure from one frame if the
layout differs.

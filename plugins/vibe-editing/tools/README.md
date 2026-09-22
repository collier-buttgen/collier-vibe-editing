# tools/ — additions to the stock kit

## caption_place.py — drag caption position before the burn
Added 2026-08-26 for Collier. The stock kit could only position captions two ways: the preset's
static Y, or the automatic per-shot track from `layout_analyze.py`. Neither lets you move one
caption by hand. This does.

```
.venv/bin/python tools/caption_place.py <video.mp4> <subs.ass> --out layout.json
```

Opens a local page (127.0.0.1 only — nothing leaves the machine). Drag any caption up or down
over the real video; `space` plays, `←/→` jump cue to cue, `↑/↓` nudge by 0.5%. "Apply to all
after" pushes the current height onto every later caption. **Save & close** writes `layout.json`
and shuts the server down.

Then re-burn with the placement applied:

```
.venv/bin/python skills/caption-clips/scripts/generate_spice.py <transcript.json> \
    --preset skills/caption-clips/presets/<preset>.json \
    --layout layout.json --out subs.ass \
    --burn <video.mp4> --burn-out <final.mp4>
```

**How it works:** it writes the same layout-track format `generate_spice.py --layout` already
consumes — `{"meta":{"fps":N},"segments":[{"start_i":F,"end_i":F,"safe_y_pct":0..1}]}` — one
segment per caption cue. So it's not a new rendering path; it feeds the one that already exists.

**Notes**
- Reads cues from the `.ass` layer 1 only (layer 0 is the blurred shadow copy; the bubble layer
  draws vector shapes). Text is de-duplicated by timecode.
- The video is served with HTTP Range support so scrubbing works.
- Verified end-to-end 2026-08-26: three captions dragged to 72% / 28% / 50% burned at exactly
  those heights.

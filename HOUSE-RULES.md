# House rules — Collier's editing standards

Claude: read this before cutting anything. These are corrections Collier has given in real sessions
(Aug–Sep 2026). They override the kit's defaults. Claude's memory does not travel between Macs;
this file does.

## Who can be in a clip
- **Only Collier's face AND Collier's voice.** No participants, callers, or audience — not their
  video, not their audio, not their names. On Zoom recordings, check at 5 fps that the frame never
  flips to someone else (`recipes/zoom-workshop-reels/qc.py` does this).
- **Cut around names spoken mid-sentence** ("…fired from your own company, Chris"). Verify with
  a full-clip transcript diff; timestamp-based cuts miss these.

## Never publish
- Collier's personal cell number (it appears on workshop slides and is read aloud).
- Client / member names paired with their numbers, client revenue slides, case-study slides.
- Collier's salary and Facility Coach's margin.
- Facility Coach ad performance (ROAS etc.).
- **Cold ads:** no earnings, income or profit claims (no substantiation file exists). Flag
  "six-figure / seven-figure", "$40K", "profit you deserve"-type lines to Collier rather than
  cutting them silently.

## Picture
- **No shake.** Seated/stationary speaker → static crop, never a face tracker.
  (`reframe_yunet.py ... --static`, or a fixed crop set by eye from a gridded frame.)
- If the camera moves mid-clip, change the crop only on an existing jump cut.
- Screen-share reels are composites (slide + Collier's tile), not crops. Keep the tile out of the
  slide crop so he never appears twice.

## Captions
- **No bounce:** no drop-in, no pop, no per-word size change. Static, one line, max 4–5 words.
- Bigger is better for Reels (he asked twice): ~82–90 px libass size on 1080x1920.
- Keep words in **spoken order** — never sort by timestamp (whisper stamps can be out of order).
- libass sizes Poppins ≈0.57× what PIL reports; measure width guards at the libass-true size.

## Cuts & endings
- Clean but never clipping a word. Tighten real silences (>~0.45 s) to ~0.24 s.
- **Every clip ends on a finished sentence or thought** — never trails into the next words
  ("That's why you managed…"). Cap ends before the next word; verify by transcribing the clip.
- At hard cuts, whisper edges drift ±0.2–0.5 s. Split hook/body and find joins by TEXT, then
  confirm by ear (transcribe a snippet up to/from the cut).

## Audio
- Clean, no music unless asked. Two-pass loudnorm to −14 LUFS, −1 dBTP.

## Brand
- Facility Coach = navy `#101726`, ice `#4CC8F0`, yellow `#FFD400`, Poppins. Gold/Bebas is retired.
- Collier Buttgen (personal) = "quiet twin": Poppins, no accent colour.
- Profiles: `brand/profiles/`. Caption presets: `plugins/vibe-editing/skills/caption-clips/presets/`.

## Delivery
- Only polished, ready files in the delivery folder; no long-form/landscape unless asked.
- Never delete source footage. Never overwrite a delivered export — move the old one into a
  subfolder (`_v1`, `_superseded/`) first.
- Names: `<idea-slug>.mp4` naming the idea (`five-families`, `the-bridge`), never `clip1`.
- Collier is non-technical: do the work yourself; don't hand him terminal commands.
- Don't ask permission for reasonable in-scope steps — just do them and report.

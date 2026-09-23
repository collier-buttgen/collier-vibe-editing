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

## Audio — do not touch (set 2026-09-23)
- Keep the current audio handling exactly as it is: two-pass loudnorm to −14 LUFS / −1 dBTP, nothing else.
- **No audio processing of any kind**: no Adobe Enhance Speech, no ElevenLabs voice isolation, no
  denoise or de-reverb. Collier is happy with the audio; don't "improve" it.
- No music unless asked.

## Quality — never downscale (set 2026-09-23)
- Everything is filmed in **4K and stays 4K**. Deliver at the source's native resolution: a 3840x2160
  camera file → **2160x3840** vertical, never a 1080 downscale. Zoom/1080p sources stay 1080x1920 —
  match the source, never reduce it (upscaling adds nothing, so don't).
- Encode: H.264 CRF ≤18 (default 16), preset slow, AAC 192k. Intermediates at CRF 12.
- `recipes/zoom-workshop-reels/build.py` takes `OUT_W` (1080 default, 2160 for 4K source). Captions are
  authored in 1080x1920 ASS space and libass scales them, so nothing changes at 4K.
- Compressed previews are for showing progress only — the delivered file is always full quality.
- **Premiere Pro extension: colour grading only.**
- **Grain:** check footage with `plugins/vibe-editing/tools/denoise.py --detect <file>`; clean it with
  `denoise.py IN OUT` (auto strength). Keeps resolution and frame rate, copies audio untouched.
  Measure the SOURCE, not a delivered mp4 — h.264 already smooths flat areas, so encoded files read 0.
  Reference: the 2026-09-14 camera files (C9821/C9822) score 1.48 = light grain.

## Delivery to Google Drive (set 2026-09-23)
Every finished clip goes to `Ready to Post` (`1T9vZhwfwt83jzhJLEMU2_U-5_Tu5cNWd`) automatically:
| Kind | Folder | ID |
|---|---|---|
| Ads | `Ads` | `107Lu-vZkqa4J-wdBEFusU58kHNwRRQHE` |
| Organic | `Organic Content` | `1XfoE5rWgu36fy62nzjWm03m9r-mKmKBj` |

    rclone copy "<local folder>" "gdrive:<subfolder>" --drive-root-folder-id <id> --exclude ".DS_Store"
    rclone check "<local folder>" "gdrive:<subfolder>" --drive-root-folder-id <id> --size-only

The `gdrive` remote is authorised on Collier's Mac (2026-09-23). On a new Mac, run
`rclone config create gdrive drive scope=drive` — it opens a browser for him to approve.

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

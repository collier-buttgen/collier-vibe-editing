# Vibe Editing — how to run this project

This folder is **Vibe Editing**: a pipeline that turns a long video into finished, captioned,
face-tracked **vertical clips**, in the creator's own brand. It's built to be run by
**non-technical creators** — so when you help someone here, do the work yourself, never make them
run terminal commands or hand-edit files, and explain what's happening in plain English.

## Making clips (the main job)
When the user gives you a video — a YouTube/URL link or a local file — and asks for clips in ANY
plain-English way ("make clips from this", "cut this up", "shorts from this", "/edit <link>"):

1. Read **`plugins/vibe-editing/skills/edit/SKILL.md`** and follow its spine end-to-end.
2. Put source footage in the project's `00_SOURCE/`, scratch in `10_WORK/`, and finished clips in
   **`20_DELIVER/`**. Show the user the delivered clips when you're done.
3. The pipeline mines the strongest moments, hand-cuts, face-tracks to 9:16, captions, mixes music,
   renders, and runs a 6-gate self-audit — a clip that fails a gate doesn't ship.

You do **not** need the `/edit` slash command or any plugin install — run the workflow directly
from the scripts in `plugins/vibe-editing/`. (A `/edit` shortcut is available if the user wants it:
`/plugin marketplace add .` then `/plugin install vibe-editing@vibe-editing-marketplace`.)

## Horizontal "mid" videos (the highlight skill)
If the user wants HORIZONTAL 16:9 "mid" videos for SUBSCRIBER growth from a long recording —
"mine highlights", "make mids", "highlights channel", "post and schedule these" — read
`plugins/vibe-editing/skills/highlight/SKILL.md` and follow it. These are regular 16:9 videos,
NOT 9:16 shorts (shorts = the edit pipeline above). The CTA outro is user-supplied and optional
at `brand/cta/outro.mp4`. POST mode titles + schedules to the user's OWN YouTube via their own
Google sign-in — never any other account.

## First-time setup (only if it isn't set up yet)
If `plugins/vibe-editing/.venv` is missing, or `python3 plugins/vibe-editing/doctor.py` reports
missing tools, set it up first: install only what's missing yourself (ffmpeg, yt-dlp, tesseract,
rclone via Homebrew; a `.venv` with the kit's deps + faster-whisper). A free Groq key in
`plugins/vibe-editing/config/keys.env` makes transcription ~10× faster; without it, it uses free
offline transcription. Full first-run + brand interview: **`ONBOARDING.md`**.

## Brand it / change it
Brand assets live in `brand/` (logos, fonts, music, caption-style, animations). When the user wants
their brand applied, or any change ("captions bigger", "use this logo", "cut tighter", "don't open
on a question"), update the right config and re-run:
- captions → `plugins/vibe-editing/skills/caption-clips/presets/spice.json`
- font → bundled `plugins/vibe-editing/skills/caption-clips/fonts/` (or their own in `brand/fonts/`)
- what makes a clip worth cutting → `plugins/vibe-editing/skills/edit/prompts/clip_select.md`
- music → `brand/music/`

## Rules
- Only use this kit — don't pull tools or keys from anywhere else on the machine.
- Never delete the user's source footage. Re-renders overwrite the delivered clip in place.
- Be patient and plain-spoken; assume they've never used a terminal.

## Read first
`HOUSE-RULES.md` — Collier's standing corrections (who can be in a clip, what never gets published,
no shake, no caption bounce, clean sentence endings). They override kit defaults.
`recipes/` — the pipelines behind delivered work (workshop reels, webinar ads).

## Machine setup (portable — `./setup-mac.sh`)
Homebrew is NOT used (it needs an admin password). `setup-mac.sh` installs everything password-free
into the home folder; re-running it is safe.

- **Python for this kit:** always use `plugins/vibe-editing/.venv/bin/python` (Python 3.12, packages
  pinned in `requirements.lock.txt`). The system `python3` does **not** have the kit's libraries.
  Health check: `plugins/vibe-editing/.venv/bin/python plugins/vibe-editing/doctor.py`.
- **Command-line tools** live in `~/.local/bin` (on PATH via `~/.zshrc`): `ffmpeg`/`ffprobe`
  (evermeet build with libass), `uv`, `yt-dlp`, `tesseract` + `pdftotext` (conda-forge builds under
  `~/.local/share/vibe-tools`, installed with micromamba).
- **To add a tool later:** don't reach for `brew`. Python packages:
  `uv pip install --python plugins/vibe-editing/.venv/bin/python <pkg>`. System binaries:
  `~/.local/share/vibe-tools/mamba/bin/micromamba create -p ~/.local/share/vibe-tools/<name> -c conda-forge <pkg>`.
- `keys.env` is never committed; `keys.env.example` is the blank template.
- A harmless `objc[...] Class AVFFrameReceiver is implemented in both ...` warning prints on
  startup (opencv and av each bundle ffmpeg libs). Ignore it.
- cv2 5.x here has no Haar cascades — set static face crops by eye from a gridded frame, or use the
  kit's YuNet path (`reframe_yunet.py --static`).
- The user is non-technical: do the work yourself, never hand them a terminal command.

## Brand profiles (added 2026-08-26)
Two brands, both live. Read `brand/profiles/` before making anything:
- `facility-coach.json` — the COMPANY. Poppins; navy #101726 / ice #4CC8F0 / yellow #FFD400.
  NOTE: this supersedes the gold + Bebas palette in the user's older `fc-master-reference.md`.
- `collier-buttgen.json` — the PERSON. "Quiet twin": same Poppins, NO accent colour at all.
  Never put ice/yellow/gold in a Collier caption.
- `editing.json` — cut tightness, clip length, caption prefs, bans.

Ask which brand a video is for if it isn't obvious. Caption look is chosen PER CLIP — there is
no single locked default. 18 presets live in `skills/caption-clips/presets/` (`fc-*`, `collier-*`).

Logos: `brand/logos/FC-logos-transparent-png/` (9 transparent 2400x1945 variants).
Fonts: all caption faces are consolidated in `skills/caption-clips/fonts/_all/`.

## Hand-placing captions
The user explicitly asked to drag caption position before burning. Use
`tools/caption_place.py` — see `tools/README.md`. Offer it whenever a caption collides with a
face, a lower-third, or on-screen text.

## Clip selection
`skills/edit/prompts/clip_select.md` has a BRAND OVERLAY appended. Key point: `contrarian` is
the top opener at lift 3.99 (the prose table in that file omits it; `config/clip_lift.json`
scores it). Original prompt preserved at `clip_select.md.orig`.

## Reframing: seated speakers (added 2026-08-31)
**Default to `--static` for any seated / stationary speaker.** The face tracker follows gestures and
micro head movements; on a locked-off interview shot that reads as shake, and Collier called it out.
On C9802 the tracker panned across ~23% of frame width on footage where the subject never moved.

    reframe_yunet.py IN OUT --res 1080 --face-y 0.30 --static

Use the tracking path only when the subject actually moves through the frame (stage, walking, roaming).
Also: convert 60fps source to 30fps before reframing — halves reframe AND caption-burn time, and 30fps
is standard for social talking-head.

## Delivery naming (locked 2026-09-09)
Every delivered clip is `<clip-slug>_<format>.mp4`:
- `_reel`      — 1080x1920 vertical, the one that gets posted
- `_landscape` — the original 16:9, kept whole. Produced for SCREEN-SHARE moments only, where a
                 vertical crop would cut off slide content. Collier asked for both formats on those.

Slug is 2-4 lowercase words, hyphenated, naming the IDEA not the source
(`date-night`, `one-door`, `menu-is-a-tax`, `owner-pay`) — never `clip1` or a timestamp.
No suffix-less files: `four-dimensions.mp4` had to be renamed after the fact.

Screen-share reels are a composite, not a crop: slide letterboxed on FC navy (#101726), Collier's
Zoom thumbnail pinned above it, and the thumbnail MASKED OUT of the slide region — otherwise he
appears twice in one frame.

# Talking-head batch → two 9:16 cuts (the production spec)

Locked 2026-09-24 after the C9841–C9845 batch. Build it exactly this way unless Collier says otherwise.
Working script: `projects/_c984x/build.py` (+ `verify.py`). Every number below was measured, not guessed.

## Intake
Collier drops 4K camera files into `~/Desktop/Master Content Folder/Clips to Edit/`. **His audio is already
finished** (Adobe Podcast — enhanced speech + music bed, names look like `C9845-esv2-50p-bg-m-music-10p.MP4`).

## Two deliverables per clip
| Cut | What | For |
|---|---|---|
| **Reels Cut** (`full`) | vertical crop of the 4K frame | Reels / trial reels |
| **Feed Cut** (`boxed`) | partial landscape crop floated on a blurred, darkened copy of itself, **FC white logo top centre** | feed |

## Picture
- **Output 2160x3840.** The native 9:16 slice of a 3840x2160 sensor is 1216 wide, so 4K delivery upscales —
  say so, don't pretend it adds detail.
- **Framing is measured, not eyeballed**: skin-tone centroid over ~16 frames, head band only (`face_x.json`).
  Centre BOTH cuts on him — in the boxed cut he sits left of frame centre, so the partial crop must follow him.
- **Punch-in on every cut** (`PUNCH_CYCLE`): the crop width changes at each cut so a jump cut reads as a
  deliberate punch. This is what "flat" usually means — ask before touching the grade.
- **Denoise/degrain**: `atadenoise` (temporal — the camera is locked off) + `hqdn3d` + a little `unsharp`.
  Measured grain 3.19 → 1.65 with face detail held (10.73 vs 10.82 raw). Stronger smooths the beard.
- **Grade** (looks good on its own, not matched to anyone): skin ~149, blacks ~3, top 5% ~196, nothing clipped.

      curves=master='0/0 0.22/0.15 0.5/0.47 0.78/0.81 1/0.98',eq=saturation=1.04:gamma=0.96

## Cuts
- Trim head/tail to a finished thought; **cap the out point before the next spoken word**.
- Pauses from `silencedetect` (NOT whisper gaps): squeeze anything over 0.20 s down to 0.10 s.
- Flubs and restarts go in `DROP` with hand-checked source times, each verified by transcribing to the cut.

## Captions
Poppins SemiBold 88 (ExtraBold + brand yellow on emphasis), max 4 words, static, sentence case.
`MarginV 540`, `MarginL/R 120` in 1080x1920 ASS space → ~29% up from the bottom, clear of Instagram's
caption/profile row (bottom 20%) and the right-hand button rail (~12%). libass scales to the 4K frame.

## Audio — never processed
Stream-copy when there is a single trim. Internal cuts force ONE re-encode at 256k AAC with 12 ms fades.
No loudness pass, no cleanup, no music. The bed sits ~36 dB under the voice so joins don't pop.

## Render mechanics (learned the hard way)
- Cut each segment to its own file and join with the **concat demuxer**. A 15-input filtergraph that also
  crops/grades deadlocks ffmpeg: *"Error sending frames to consumers: Operation timed out"*.
- One render at a time — `build.py` takes an flock. Two runs writing the same output = corrupt mp4.
  (`pkill -f "project/build.py"` does NOT match `python build.py` run from that directory.)
- With an explicit `-map 0:a:0` you must also `-map 0:v:0`, or you ship an audio-only file.
- Overlay inputs are numbered in command order: the logo added after the video is `[1:v]`.

## Gate before shipping (`verify.py`) — all must pass
full decode with 0 errors · duration within `0.3 + 0.05×cuts` · dead air < 0.35 s · 0 clicks ·
transcript matches the script word for word · audio stereo 48k · both cuts the same length.

## Deliver
`Master Content Folder/<batch>/{Reels Cut,Feed Cut}/` **and** Drive — ads → `Ads`, organic → `Organic Content`:

    rclone sync "<local>" "gdrive:<folder>" --drive-root-folder-id <id> --exclude ".DS_Store"
    rclone check "<local>" "gdrive:<folder>" --drive-root-folder-id <id> --size-only

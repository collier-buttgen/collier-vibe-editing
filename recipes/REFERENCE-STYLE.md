# Reference channels — measured, not guessed

Collier's four references (2026-10-03), measured off downloaded copies. Numbers are the target; re-measure
any new edit the same way before shipping.

| | cuts/min (hard) | cuts/min (all) | captions | caption height | speaker on screen | skin luma | skin sat |
|---|---|---|---|---|---|---|---|
| **Alex Hormozi** (talking head) | 5.9 | **15.5** | 98% | **76%** | **80%** | 127 | **40%** |
| Nick Bare (vlog) | 3.6 | 9.4 | 38% | 66% | 75% | 100 | 38% |
| Dom Iacovone (vlog) | 4.6 | 8.3 | 0% | — | 92% | 119 | 40% |
| Greg Lav (long takes) | 0.7 | 1.3 | 0% | — | 100% | 140 | 43% |
| **FC C9881 (ours, 10-03)** | 11.3 | 17.2 | 100% | 68% | **100%** | 107 | 47% |

Caption height = % down the frame (76% sits above the lower edge; 92% is hard against the bottom).
Speaker on screen = fraction of sampled frames with a face; the remainder is b-roll, graphics or full-frame text.

## What this says for a TALKING-HEAD cut
- **Density comes from frequency, not size.** Hormozi's total change rate is 15.5/min but only 5.9 are hard
  cuts — most are small re-frames or jump cuts on the same framing. Big crop jumps every few seconds read
  as hard cuts and overshoot (our first attempt hit 22/min). Re-frame every ~7s with gentle steps.
- **Captions ride at ~76% height**, not jammed to the bottom. Always on.
- **~20% of his runtime is NOT the speaker** — full-frame graphics, b-roll, text. Ours is 100% speaker with
  cards overlaid in the corner. Closing that gap needs either b-roll or full-frame graphic beats.
- Skin sits around luma 127 / saturation 40% across all four. Ours ran 107 / 47% — darker and more saturated.

## For VLOGS (Collier is shooting more)
Nick Bare and Dom Iacovone: 8–9 changes/min, 75–92% speaker on camera, captions used sparingly or not at
all. Pacing comes from location changes and b-roll, not from cutting the speech. A vlog needs a different
pipeline from the talking-head recipe: multi-clip assembly, b-roll selection, music.

## How to measure (both traps are real)
    ffmpeg -hide_banner -nostats -i X.mp4 -vf "select='gt(scene,0.08)',showinfo" -f null - 2>&1 | grep -c pts_time
`-v error` SUPPRESSES showinfo and silencedetect output — the check then silently reports zero. It reported
"0 cuts" on all four references the first time.

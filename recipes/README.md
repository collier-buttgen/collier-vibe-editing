# Recipes

Proven, end-to-end pipelines from real jobs. Each one reads a project folder given as `PROJECT=`
and uses the kit's fonts, keys and ffmpeg. Everything follows `../HOUSE-RULES.md`.

| Recipe | Use it for | Made |
|---|---|---|
| `zoom-workshop-reels/` | A long Zoom recording (workshop, call) → vertical reels. Two formats: **Collier-only camera** and **split screen with the slides** (navy "A" or light "B"). | 2026-09-21, PFOS workshop → 23 reels |
| `webinar-ad/` | Paid ad: several hooks × one body/CTA → one 9x16 file per hook, −14 LUFS, captions in three looks (`box`, `shadow`, `brand`). | 2026-09-14, COLD_WEBINAR_v05 |

Run any script with the kit's Python:

    plugins/vibe-editing/.venv/bin/python recipes/<recipe>/<script>.py

# Webinar ad — hooks × body

Builds one 9x16 ad per hook: hook select + shared body/CTA select → concat → −14 LUFS → captions.
Spec: FC Content Playbook Week 1, p.12 (1080x1920, 30 fps, first frame talking, hard-cut end, no end card).

## Project folder (`PROJECT=...`)
    03_selects/<HOOK>.mov  BODY_*.mov      # cut + cropped selects (1080x1920, PCM audio)
    04_project-files/work/                 # assemble.py output: *_norm.mov, *_tx.json

## Steps
1. Cut selects from the camera files at waveform dips (not whisper stamps). Full-height crop for hooks,
   ~1.2× punch-in for the body when there's only one camera angle.
2. `VARIANTS='{"NAME":"hook_select"}' BODY_SELECT=BODY.mov assemble.py` — concat (normalises SAR/fps/audio),
   two-pass loudnorm, transcribes each assembled ad.
3. `CAP_STYLE=box|shadow|brand BODY_OPEN="you don't" build_captions.py <hook_tx> <hook_dur> <body_tx> <body_hook_dur> <out.ass>`
   — splits hook/body by TEXT (the body's opening words within 1 s of the cut), never by timestamp.
4. Burn: `ffmpeg -i NAME_norm.mov -vf "subtitles=NAME.ass:fontsdir=<kit fonts/_all>" -c:v libx264 -crf 18 ...`
5. Guard before export and make it actually stop the run (`|| exit 1`).

Compliance: cold creative can't carry earnings/income/profit claims. Flag them to Collier.

#!/usr/bin/env python3
"""Transcribe every delivered clip and diff it against the intended words. Flags extra/missing words anywhere."""
import json, os, re, subprocess, time, difflib, sys
import pathlib as _pl, shutil as _sh
KIT = _pl.Path(__file__).resolve().parents[2]                       # repo root (recipes/<name>/<script>.py)
FF = _sh.which('ffmpeg') or str(_pl.Path.home() / '.local/bin/ffmpeg')
FD = str(KIT / 'plugins/vibe-editing/skills/caption-clips/fonts/_all') + '/'
KEYS = KIT / 'plugins/vibe-editing/config/keys.env'
P = os.environ.get('PROJECT') or sys.exit('Set PROJECT=/path/to/project (with source.mp4, tx/, work/) — see README.md'); 
KEY = [l.split('=', 1)[1].strip() for l in open(KEYS) if l.startswith('GROQ_API_KEY=')][0]
W = json.load(open(P + '/tx/ws.json'))['words']; R = json.load(open(P + '/work/resolved.json'))
norm = lambda t: [re.sub(r"[^a-z0-9']", '', x.lower()) for x in t.split() if re.sub(r"[^a-z0-9']", '', x.lower())]
os.makedirs(P + '/work/verify', exist_ok=True); bad = 0
for name, c in [(n, R[n]) for n in (sys.argv[1:] or R)]:
    exp = norm(' '.join(' '.join(W[i]['word'] for i in range(a, b + 1)) for s, e, a, b in c['parts']))
    mp3 = P + f'/work/verify/{name}.mp3'
    subprocess.run([FF, '-y', '-v', 'error', '-i', P + f'/deliver/{name}.mp4', '-vn', '-ac', '1', '-ar', '16000', '-b:a', '48k', mp3])
    for k in range(6):
        r = subprocess.run(['curl', '-s', 'https://api.groq.com/openai/v1/audio/transcriptions', '-H', f'Authorization: Bearer {KEY}',
                            '-F', f'file=@{mp3}', '-F', 'model=whisper-large-v3', '-F', 'language=en', '-F', 'response_format=text'],
                           capture_output=True, text=True).stdout
        if '"error"' not in r: break
        time.sleep(15)
    got = norm(r.replace('-', ' ')); exp2 = norm(' '.join(exp).replace('-', ' '))
    sm = difflib.SequenceMatcher(a=exp2, b=got, autojunk=False)
    extra_tail = got[len(got) - (len(got) - max(j + n for i, j, n in sm.get_matching_blocks() if n) if sm.get_matching_blocks() else 0):]
    ops = [(t, ' '.join(exp2[i1:i2]), ' '.join(got[j1:j2])) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != 'equal']
    last_match_end = max((j + n for i, j, n in sm.get_matching_blocks() if n), default=0)
    first_match = min((j for i, j, n in sm.get_matching_blocks() if n), default=0)
    tail, head = got[last_match_end:], got[:first_match]
    ok = not tail and not head and sm.ratio() > .9
    bad += not ok
    print(f"{'OK ' if ok else 'CHK'} {name:<24} match {sm.ratio():.2f}  ends: …{' '.join(got[-6:])}"
          + (f"\n      EXTRA AT END: {' '.join(tail)}" if tail else '') + (f"\n      EXTRA AT START: {' '.join(head)}" if head else '')
          + ''.join(f"\n      {t}: '{a}' → '{b}'" for t, a, b in ops if (t != 'replace' or len(a.split()) > 1 or len(b.split()) > 1)))
    time.sleep(3.5)
sys.exit(1 if bad else 0)

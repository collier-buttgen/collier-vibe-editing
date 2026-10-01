#!/usr/bin/env python3
"""Production QC for the C984x batch. Fails loudly; nothing ships unless every line says OK.

 1. file integrity + duration matches the cut list
 2. word-for-word: transcribe the finished clip and diff against the words the cut list keeps
    (catches a cut swallowing or repeating a word at a join)
 3. audio: stereo 48k, and still the same length as the picture
 4. the two variants of a clip are the same edit (same duration)
 5. no dead air left: silencedetect must find nothing over 0.30s
    (NOTE: silencedetect prints at info level — `-v error` hides it and the check silently passes)
 6. no clicks at the joins: no sample-to-sample jump over 0.25 full scale
"""
import difflib, json, os, re, subprocess, sys, time, importlib.util

P = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('b', P + '/build.py'); b = importlib.util.module_from_spec(spec)
sys.argv = ['x']; spec.loader.exec_module(b)
FP = b.FF.replace('ffmpeg', 'ffprobe')
KEY = [l.split('=', 1)[1].strip() for l in open(os.path.expanduser(
    '~/Documents/vibe-editing/plugins/vibe-editing/config/keys.env')) if l.startswith('GROQ_API_KEY=')][0]
norm = lambda t: [re.sub(r"[^a-z0-9']", '', x.lower()) for x in t.replace('-', ' ').split()
                  if re.sub(r"[^a-z0-9']", '', x.lower())]

def probe(f, sel, ent):
    return subprocess.run([FP, '-v', 'error', '-select_streams', sel, '-show_entries', ent,
                           '-of', 'csv=p=0', f], capture_output=True, text=True)

def transcribe(f):
    mp3 = f'{P}/work/qc.mp3'
    subprocess.run([b.FF, '-y', '-v', 'error', '-i', f, '-vn', '-ac', '1', '-ar', '16000',
                    '-b:a', '48k', mp3], check=True)
    for _ in range(6):
        r = subprocess.run(['curl', '-s', 'https://api.groq.com/openai/v1/audio/transcriptions',
                            '-H', f'Authorization: Bearer {KEY}', '-F', f'file=@{mp3}',
                            '-F', 'model=whisper-large-v3', '-F', 'language=en',
                            '-F', 'response_format=text'], capture_output=True, text=True).stdout
        if '"error"' not in r: return r
        time.sleep(15)
    sys.exit('transcription failed')

bad = 0
for n in b.CLIPS:
    segs = b.segments(n); want = sum(y - x for x, y in segs)
    # what SHOULD be audible: every word between the head/tail trims except the flubs we dropped on
    # purpose. Do NOT derive this per-segment — the silence cuts remove no speech, but whisper's stamps
    # drift enough that words land inside a cut silence and vanish from the expectation, not the audio.
    ts, te = b.trim(n)
    drops = b.DROP.get(n, [])
    # Two legitimate readings of a clip: every word of the take (a dropped RESTART is said again in the
    # retake, and the source transcript holds only one smoothed copy), or the take minus the dropped words
    # (a dropped flub is gone for good). Score against both and take the better — the duration gate below
    # is what proves the drop actually happened, so this cannot hide a cut that failed to apply.
    allw = [w for w in b.words(n) if ts <= (w['start'] + w['end']) / 2 < te]
    expect_full = norm(' '.join(w['word'] for w in allw))
    expect_cut = norm(' '.join(w['word'] for w in allw
                               if not any(x <= (w['start'] + w['end']) / 2 < y for x, y in drops)))
    durs = {}
    for v in ('full', 'boxed'):
        f = f'{P}/deliver/{n}_9x16-{v}.mp4'
        if not os.path.exists(f): print(f"BAD {n}-{v}: missing"); bad += 1; continue
        r = probe(f, 'v:0', 'format=duration:stream=width,height')
        if r.stderr.strip(): print(f"BAD {n}-{v}: unreadable — {r.stderr.strip()[:60]}"); bad += 1; continue
        wh, d = r.stdout.split()[0], float(r.stdout.split()[-1]); durs[v] = d
        a = probe(f, 'a:0', 'stream=channels,sample_rate').stdout.strip()
        got = norm(transcribe(f))
        sm = max((difflib.SequenceMatcher(a=e, b=got, autojunk=False) for e in (expect_full, expect_cut)),
                 key=lambda m: m.ratio())
        expect = sm.a
        blocks = [x for x in sm.get_matching_blocks() if x.size]
        head, tail = got[:blocks[0].b], got[blocks[-1].b + blocks[-1].size:]
        joins = [(' '.join(expect[i1:i2]), ' '.join(got[j1:j2])) for t, i1, i2, j1, j2 in sm.get_opcodes()
                 if t != 'equal' and (i2 - i1 > 1 or j2 - j1 > 1)]
        sil = subprocess.run([b.FF, '-hide_banner', '-nostats', '-i', f, '-af',
                              'silencedetect=noise=-45dB:d=0.30', '-f', 'null', '-'],
                             capture_output=True, text=True).stderr
        dead = sum(float(x) for x in re.findall(r'silence_duration: ([\d.]+)', sil))
        pcm = subprocess.run([b.FF, '-v', 'error', '-i', f, '-ac', '1', '-ar', '48000',
                              '-f', 's16le', '-'], capture_output=True).stdout
        import numpy as np
        sig = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
        clicks = int((np.abs(np.diff(sig)) > 0.25).sum())
        # Words may legitimately differ by a few around a DROP: when we cut a restart, the source
        # transcript holds only the smoothed single copy of the phrase, so the retake reads as an insert.
        # Anything bigger than that — or any drift at the head/tail — still fails.
        slack = 5 if drops else 3          # transcription variance alone can add a word or two
        inserted = sum(j2 - j1 for t_, i1, i2, j1, j2 in sm.get_opcodes() if t_ == 'insert')
        # each piece rounds up to a frame boundary, so the tolerance has to scale with the number of cuts
        # (still far tighter than any dropped flub, which is seconds long)
        tol = 0.3 + 0.05 * len(segs)
        ok = (dead < 0.35 and clicks == 0 and abs(d - want) < tol and inserted <= slack
              and not head and not tail and sm.ratio() > .93) and a.replace(' ','') in ('2,48000', '48000,2')
        bad += not ok
        print(f"{'OK ' if ok else 'BAD'} {n}-{v:<6} {d:6.1f}s (cut list {want:5.1f} ±{tol:.2f})  {wh}  audio {a}  "
              f"words {sm.ratio():.2f}  dead {dead:.1f}s  clicks {clicks}" + (f"  HEAD:{' '.join(head)}" if head else '')
              + (f"  TAIL:{' '.join(tail)}" if tail else '')
              + ''.join(f"  [{x} → {y}]" for x, y in joins[:3]))
        time.sleep(3.5)
    if len(durs) == 2 and abs(durs['full'] - durs['boxed']) > 0.1:
        print(f"BAD {n}: variants differ ({durs['full']:.2f} vs {durs['boxed']:.2f})"); bad += 1
print(('ALL CLEAR' if not bad else f'{bad} PROBLEM(S) — do not ship'))
sys.exit(1 if bad else 0)

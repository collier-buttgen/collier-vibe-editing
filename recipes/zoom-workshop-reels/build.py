#!/usr/bin/env python3
"""Workshop 2026-09-16 → reels.  Usage: build.py [clip-name ...]   (default: all in work/resolved.json)

face  : Collier's full camera, static 9:16 crop centred on his face (no tracking, no shake).
splitA: navy — slide on top, yellow rule, Collier's Zoom tile below, captions on navy (the approved 09-09 look).
splitB: paper — Collier's tile on top, ice rule, slide below, navy captions on white.
Cuts: part in/out snapped to the waveform; pauses > ~0.45s of real silence tightened to 0.24s.
Captions: source word stamps mapped through the cut list (no re-transcription), static, 1 line, max 4 words.
Audio: two-pass loudnorm to -14 LUFS / -1 dBTP.
"""
import json, os, re, subprocess, sys, math
import pathlib as _pl, shutil as _sh
KIT = _pl.Path(__file__).resolve().parents[2]                       # repo root (recipes/<name>/<script>.py)
FF = _sh.which('ffmpeg') or str(_pl.Path.home() / '.local/bin/ffmpeg')
FD = str(KIT / 'plugins/vibe-editing/skills/caption-clips/fonts/_all') + '/'
KEYS = KIT / 'plugins/vibe-editing/config/keys.env'
import numpy as np
from PIL import ImageFont
from fontTools.ttLib import TTFont

P = os.environ.get('PROJECT') or sys.exit('Set PROJECT=/path/to/project (with source.mp4, tx/, work/) — see README.md')
# per-project hand settings (face crops, hand-checked cut points) live in $PROJECT/overrides.json
_OV = json.load(open(P + '/overrides.json')) if os.path.exists(P + '/overrides.json') else {}
SRC = P + '/source.mp4'


W = json.load(open(P + '/tx/ws.json'))['words']
RES = json.load(open(P + '/work/resolved.json'))

SLIDE = (221, 170, 1419, 767)          # slide page, right edge stops short of the Zoom tile
THUMB = (1650, 76, 254, 140)           # Collier's Zoom tile during screen share

def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: sys.exit(f"FAILED: {' '.join(cmd)[:300]}\n{r.stderr[-1500:]}")
    return r

# ---------- audio envelope (10 ms RMS, whole source, cached) ----------
ENV = P + '/work/env10ms.npy'
if not os.path.exists(ENV):
    raw = subprocess.run([FF, '-v', 'error', '-i', SRC, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                         capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    a = a[:len(a) // 160 * 160].reshape(-1, 160)
    np.save(ENV, 20 * np.log10(np.sqrt((a ** 2).mean(1)) + 1e-6))
env = np.load(ENV)
def db(t0, t1): return env[max(0, int(t0 * 100)):max(int(t0 * 100) + 1, int(t1 * 100))]

def quiet_thr(s, e):
    seg = db(s, e); return max(np.percentile(seg, 12) + 6, -50)

def snap_in(t, thr):   # walk back from word start to speech onset (max 0.30s)
    for k in range(0, 30):
        if db(t - (k + 1) * .01, t - k * .01).max() < thr: return t - k * .01 - .05
    return t - .30
def snap_out(t, thr):  # walk forward from word end until silence (max 0.45s)
    for k in range(0, 45):
        if db(t + k * .01, t + (k + 1) * .01).max() < thr: return t + k * .01 + .08
    return t + .45

def dip(t0, t1):   # time of the quietest point (30 ms smoothed) in [t0, t1]
    seg = db(t0, t1)
    if len(seg) < 3: return (t0 + t1) / 2
    sm = np.convolve(seg, np.ones(3) / 3, mode='same')
    return t0 + int(np.argmin(sm[1:-1]) + 1) * .01

# Hand-checked cut points (each verified by transcribing the audio up to / from the cut) where whisper's word
# edges drift in continuous speech. Key: (clip, part index, 'start'|'end') → source seconds.
BOUND = {(c, int(i), k): t for c, i, k, t in _OV.get('bound', [])}
NAME = ''

def segments(parts):
    segs = []
    for pi, (s, e, a, b) in enumerate(parts):
        thr = quiet_thr(s - 1, e + 1)
        cur = snap_in(W[a]['start'], thr)
        if a > 0: cur = max(cur, min(W[a]['start'] - .02, W[a - 1]['end'] + .04))   # don't pick up the previous word's tail
        cur = BOUND.get((NAME, pi, 'start'), cur)
        for i in range(a, b):
            g0, g1 = W[i]['end'], W[i + 1]['start']
            if g1 - g0 < 0.30: continue
            # find the real silent run inside the (possibly stretched) gap
            win = db(g0 - .25, g1 + .25); q = win < thr
            best, run, st = (0, 0), 0, 0
            for j, v in enumerate(q):
                if v: run += 1; st = j if run == 1 else st
                else: run = 0
                if run > best[0]: best = (run, st)
            if best[0] * .01 < 0.45: continue
            qs = g0 - .25 + best[1] * .01; qe = qs + best[0] * .01
            segs.append([round(cur, 3), round(qs + .12, 3)]); cur = qe - .12
        # continuous speech into the next (unwanted) word: whisper's word edges drift ±0.2s there, so cut at the
        # quietest 10 ms between the last kept word's second half and the next word's onset
        end = snap_out(W[b]['end'], thr)
        if b + 1 < len(W): end = min(end, max(W[b]['end'] + .02, W[b + 1]['start'] - .04))
        end = BOUND.get((NAME, pi, 'end'), end)
        segs.append([round(cur, 3), round(end, 3)])
    return segs

# ---------- face position (set by eye from gridded frames; camera is locked off) ----------
# Zoom paints the camera inside black bars: picture spans y 48..1032, so the 9:16 crop is 553x984.
FACE_X = _OV.get('face_x', {})                  # clip → face centre x in the 1920 frame (set by eye from a gridded frame)
SEG_X = {k: {int(i): x for i, x in v.items()} for k, v in _OV.get('seg_x', {}).items()}   # clip → {segment index: x}
TILE_Y = 80                                                         # tile crop top (face centred ~y130)

# ---------- layouts ----------
def layout(kind, segs, name):
    if kind == 'face':
        return "[v]null[out]", None
    tx, ty, tw, th = THUMB; ph = 108; y0 = TILE_Y                   # tile crop 254x108 ≈ 1080x460
    sx, sy, sw, sl = SLIDE
    face = f"crop={tw}:{ph}:{tx}:{y0},scale=1080:460:flags=lanczos,unsharp=5:5:0.6,setsar=1"
    slide = f"crop={sw}:{sl}:{sx}:{sy},scale=1080:584:flags=lanczos,setsar=1"
    if kind == 'splitA':
        return (f"[v]split[p][q];[p]{slide}[sl];[q]{face}[fc];"
                f"color=c=0x101726:s=1080x1920:r=30[bg];[bg][sl]overlay=0:300:shortest=1[t1];"
                f"[t1]drawbox=x=0:y=884:w=1080:h=8:color=0xFFD400:t=fill[t2];[t2][fc]overlay=0:892:shortest=1,setsar=1[out]"), 'A'
    return (f"[v]split[p][q];[p]{slide}[sl];[q]{face}[fc];"
            f"color=c=0xF3F5F8:s=1080x1920:r=30[bg];[bg][fc]overlay=0:290:shortest=1[t1];"
            f"[t1]drawbox=x=0:y=750:w=1080:h=8:color=0x4CC8F0:t=fill[t2];[t2][sl]overlay=0:758:shortest=1,"
            f"drawbox=x=0:y=1342:w=1080:h=2:color=0xD5DBE3:t=fill,setsar=1[out]"), 'B'

# ---------- captions ----------
MAXW, GAP_BREAK, HOLD = 4, 0.32, 0.55
EMPH = set("""not don't never no zero one broke broken profit offer freedom selfish bottleneck standard connection community
significant bridge transformation impact burnt hate fired owner employee marketing website miserable cost forever paralysis
faster donut math leads ads content integrity implementation lease asset retire vacation college kids wife coaches
five-minute minutes permission leader grace fear families wrong asinine bugatti supercar proteus cool 13 four""".split())
STY = {  # name: font, size, primary, outline/back, border, outline, shadow, marginV, accent
 'face': ('Poppins SemiBold', 'Poppins ExtraBold', 90, '&H00FFFFFF', '&H00000000', '&H99000000', 1, 3, 2, 330, '&H00D4FF&'),
 'A':    ('Poppins SemiBold', 'Poppins ExtraBold', 82, '&H00FFFFFF', '&H00261710', '&H00261710', 1, 0, 0, 300, '&H00D4FF&'),
 'B':    ('Poppins SemiBold', 'Poppins ExtraBold', 82, '&H00261710', '&H00F8F5F3', '&H00F8F5F3', 1, 0, 0, 250, '&HA07C0E&'),
}
def ts(t): t = max(0, t); return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"

def captions(segs, parts, style, out):
    fam, efam, size, prim, outl, back, bord, ow, shd, mv, acc = STY[style]
    font = ImageFont.truetype(FD + 'Poppins-ExtraBold.ttf', size)
    f = TTFont(FD + 'Poppins-ExtraBold.ttf', lazy=True); k = f['head'].unitsPerEm / (f['OS/2'].usWinAscent + f['OS/2'].usWinDescent)
    font = ImageFont.truetype(FD + 'Poppins-ExtraBold.ttf', max(1, round(size * k)))
    # words kept by the cut list, re-timed
    # every kept word, in SPOKEN order (whisper can stamp a word before its predecessor — never sort by time),
    # placed in the segment it overlaps most (or the nearest one), then times forced monotonic
    offs, o = [], 0.0
    for s, e in segs: offs.append(o); o += e - s
    off = o
    ws = []
    for i in sorted({i for s, e, a, b in parts for i in range(a, b + 1)}):
        w = W[i]
        ov = [min(w['end'], e) - max(w['start'], s) for s, e in segs]
        k = max(range(len(segs)), key=lambda j: (ov[j], -min(abs(w['start'] - segs[j][1]), abs(w['end'] - segs[j][0]))))
        s, e = segs[k]
        ws0 = offs[k] + min(max(w['start'], s), e) - s; we0 = offs[k] + min(max(w['end'], s), e) - s
        for p in w['word'].split(): ws.append(dict(w=p, s=ws0, e=max(we0, ws0 + .05)))
    for j in range(1, len(ws)):
        ws[j]['s'] = max(ws[j]['s'], ws[j - 1]['s'] + .01); ws[j]['e'] = max(ws[j]['e'], ws[j]['s'] + .05)
    # sentence case + phrase chunking
    cap = True
    for w in ws:
        t = w['w']
        if cap and t[:1].isalpha(): t = t[0].upper() + t[1:]
        w['w'] = t; cap = bool(re.search(r'[.?!]$', t))
    phrases, cur = [], []
    for i, w in enumerate(ws):
        cur.append(w); last = i == len(ws) - 1
        gap = 0 if last else ws[i + 1]['s'] - w['e']
        if last or re.search(r'[.?!,]$', w['w']) or gap >= GAP_BREAK: phrases.append(cur); cur = []
    chunks = []
    for ph in phrases:
        n = math.ceil(len(ph) / MAXW); i = 0
        for j in range(n):
            sz = math.ceil((len(ph) - i) / (n - j)); c = ph[i:i + sz]; i += sz
            while len(c) > 1 and font.getlength(' '.join(x['w'] for x in c)) > 960:
                h = len(c) // 2; chunks.append(c[:h]); c = c[h:]
            chunks.append(c)
    ev = []
    for i, c in enumerate(chunks):
        st = c[0]['s']; nx = chunks[i + 1][0]['s'] if i + 1 < len(chunks) else None
        en = nx if (nx is not None and nx - c[-1]['e'] < HOLD) else c[-1]['e'] + .2
        en = max(en, st + .4); en = min(en, nx) if nx is not None else en
        toks = re.sub(r'[,.;:]+$', '', ' '.join(x['w'] for x in c)).split(' ')
        txt = ' '.join(f"{{\\fn{efam}\\1c{acc}}}{t}{{\\fn{fam}\\1c{prim}}}"
                       if (re.search(r'\d', t) or re.sub(r"[^\w'-]", '', t.lower()) in EMPH) else t for t in toks)
        ev.append(f"Dialogue: 1,{ts(st)},{ts(en)},Cap,,0,0,0,,{txt}")
    hdr = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\nWrapStyle: 2\n\n"
           "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
           "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
           f"Style: Cap,{fam},{size},{prim},&H00FFFFFF,{outl},{back},0,0,0,0,100,100,0.5,0,{bord},{ow},{shd},2,50,50,{mv},1\n")
    if style in 'AB':
        lab = '&H00F0C84C' if style == 'A' else '&H00261710'
        hdr += f"Style: Label,Poppins Bold,34,{lab},&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,4,0,1,0,0,7,60,60,190,1\n"
    hdr += "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    if style in 'AB': hdr += f"Dialogue: 0,0:00:00.00,{ts(off + 1)},Label,,0,0,0,,FACILITY COACH\n"
    open(out, 'w').write(hdr + '\n'.join(ev) + '\n')
    return len(ev), off

# ---------- render ----------
def build(name, kind_i):
    global NAME; NAME = name
    c = RES[name]; parts = c['parts']; segs = segments(parts)
    kind = 'face' if c['kind'] == 'face' else ('splitA' if kind_i % 2 == 0 else 'splitB')
    d = P + f'/work/{name}'; os.makedirs(d, exist_ok=True)
    print(f'\n== {name}  [{kind}]  {len(segs)} segments, {sum(e - s for s, e in segs):.1f}s')
    lay, st = layout(kind, segs, name)
    ins, fc = [], []
    for i, (s, e) in enumerate(segs):
        ins += ['-ss', f'{s:.3f}', '-t', f'{e - s:.3f}', '-i', SRC]
        crop = ''
        if kind == 'face':
            x = int(min(max(SEG_X.get(name, {}).get(i, FACE_X[name]) - 276, 80), 1832 - 553))
            crop = f"crop=553:984:{x}:48,scale=1080:1920:flags=lanczos,"
        fc.append(f"[{i}:v]{crop}setsar=1,fps=30,format=yuv420p[v{i}];[{i}:a]aresample=48000,aformat=channel_layouts=stereo,"
                  f"afade=t=in:d=0.012,afade=t=out:st={e - s - .015:.3f}:d=0.015[a{i}]")
    cat = ''.join(f'[v{i}][a{i}]' for i in range(len(segs))) + f'concat=n={len(segs)}:v=1:a=1[v][a]'
    fcx = ';'.join(fc) + ';' + cat + ';' + lay
    raw = d + '/raw.mov'
    sh([FF, '-y', '-hide_banner', '-loglevel', 'error', *ins, '-filter_complex', fcx, '-map', '[out]', '-map', '[a]',
        '-c:v', 'libx264', '-crf', '14', '-preset', 'fast', '-c:a', 'pcm_s16le', raw])
    m = sh([FF, '-hide_banner', '-i', raw, '-af', 'loudnorm=I=-14:TP=-1:LRA=11:print_format=json', '-f', 'null', '-']).stderr
    j = json.loads(m[m.rindex('{'):m.rindex('}') + 1])
    ln = (f"loudnorm=I=-14:TP=-1:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
          f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    ncue, dur = captions(segs, parts, 'face' if kind == 'face' else st, d + '/cap.ass')
    out = P + f'/deliver/{name}.mp4'
    sh([FF, '-y', '-hide_banner', '-loglevel', 'error', '-i', raw, '-vf', f"subtitles={d}/cap.ass:fontsdir={FD}",
        '-af', ln + ',aresample=48000', '-r', '30', '-c:v', 'libx264', '-crf', '18', '-preset', 'slow', '-profile:v', 'high',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '192k', out])
    json.dump(dict(kind=kind, segs=segs), open(d + '/cutlist.json', 'w'))
    print(f'   {ncue} cues · {dur:.1f}s → deliver/{name}.mp4')

if __name__ == '__main__':
    names = sys.argv[1:] or list(RES)
    splits = [n for n in RES if RES[n]['kind'] == 'split']
    for n in names: build(n, splits.index(n) if n in splits else 0)
    print('BUILD DONE')

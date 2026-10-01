#!/usr/bin/env python3
"""C984x organic batch → two 9:16 variations per clip, at native 4K-derived resolution.

v2: internal cuts. Pauses over ~0.35s are tightened to ~0.14s and flubs/restarts are dropped, so the
pacing is tight. The music bed sits ~36 dB under the voice (pauses measure -53 to -83 dB), so the joins
do not pop. Cutting means the audio can no longer be stream-copied — it is re-encoded ONCE at 256k AAC
with 12 ms fades at each join. No processing, no levels touched.

full  : vertical crop of the 4K frame — 1216x2160 native pixels, nothing scaled down.
boxed : the whole landscape frame floated on its own blurred, darkened background (feed style).

Per house rules: AUDIO IS COPIED THROUGH UNTOUCHED (Collier already ran these through Adobe Podcast —
music bed and levels are his). Light denoise + a subtle grade on the picture only. One trim per clip,
so there is no internal cut to break the music bed.
"""
import json, math, os, re, subprocess, sys
import numpy as np
from PIL import ImageFont
from fontTools.ttLib import TTFont

P = os.path.dirname(os.path.abspath(__file__))
FF = os.path.expanduser('~/.local/bin/ffmpeg')
FD = os.path.expanduser('~/Documents/vibe-editing/plugins/vibe-editing/skills/caption-clips/fonts/_all/')
W, H = 2160, 3840                                  # 4K delivery (native 9:16 slice is 1216 wide, upscaled)
LOGO = os.path.expanduser('~/Documents/vibe-editing/brand/logos/FC-logos-transparent-png/FC-logo-white.png')
# Denoise/degrain: temporal (atadenoise) does the work on a locked-off camera, hqdn3d cleans spatially,
# unsharp puts the micro-detail back. Measured on frame-to-frame noise in static areas:
# raw 3.19 → 1.65 with face detail held at 10.73 (raw 10.82). Stronger settings start smoothing the beard.
DENOISE = ('atadenoise=0a=0.025:0b=0.05:1a=0.025:1b=0.05:2a=0.025:2b=0.05,'
           'hqdn3d=2.5:1.8:8:8,unsharp=5:5:0.45:5:5:0.0')
# Matched to the reference ads in Drive (measured on skin: tonal spread ~103, saturation ~29%).
# The old grade left skin at spread 75 / sat 20% — that is what read as "flat".
# Graded to look good on its own (not matched to anyone else's footage): skin ~149, rich blacks,
# highlight headroom (top 5% ~196, nothing clipped), natural saturation on a ruddy complexion.
GRADE = "curves=master='0/0 0.22/0.15 0.5/0.47 0.78/0.81 1/0.98',eq=saturation=1.04:gamma=0.96"
PUNCH_W = 1120                                     # tighter framing than a full-height 1216 crop
# Pacing: every cut also changes the framing, so a jump cut reads as a deliberate punch instead of a
# splice. Widths cycle per segment (all scaled back to 1216 wide, so the size change is what you see).
PUNCH_CYCLE = [1180, 1010, 1120, 960, 1180, 1060]

# clip → (first words, last words). Face centre x is MEASURED into face_x.json (skin centroid, head band).
CLIPS = {
 'C9841': ("Most coaches I talk to, they sell a menu.", "one door that people can walk through."),
 'C9842': ("At 22 years old, I made more money",        "10 hours of yourself in the cage."),
 'C9843': ("When your model is broken",                 "None of those things matter."),
 'C9844': ("This week I asked my coaches",              "exactly how we've done that."),
 'C9845': ("Really simply, if I had to boil down",      "that you follow along."),
}
# hand-checked end point where speech runs straight on with no pause (verified by transcribing to the cut)
END_AT = {'C9842': 87.70}                          # after "…in the cage.", before "What scales is"
FACE = json.load(open(f'{P}/face_x.json'))         # clip → head centre x in the 3840 frame
BOX_W, BOX_H = 3000, 2160                          # 'boxed' = partial landscape crop, centred on him
BOX_SCALE_H = BOX_H * W // BOX_W // 2 * 2          # partial-crop box scaled to full width
EMPH = set("""not don't never no one menu door offer transformation confusion money lease job business
scale profit impact leadership predictable model cost customer lifetime value free freedom follow
150 zero 22 30,000 40,000 10 three first""".split())

def sh(c, **k):
    r = subprocess.run(c, capture_output=True, text=True, **k)
    if r.returncode: sys.exit(f"FAILED: {' '.join(map(str, c))[:250]}\n{r.stderr[-1200:]}")
    return r

def words(n): return json.load(open(f'{P}/tx/{n}.json'))['words']

def env_db(n):
    f = f'{P}/work/{n}_env.npy'
    if not os.path.exists(f):
        raw = subprocess.run([FF, '-v', 'error', '-i', f'{P}/src/{n}.MP4', '-ac', '1', '-ar', '16000',
                              '-f', 's16le', '-'], capture_output=True).stdout
        a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        a = a[:len(a) // 160 * 160].reshape(-1, 160)
        np.save(f, 20 * np.log10(np.sqrt((a ** 2).mean(1)) + 1e-6))
    return np.load(f)

def anchor(ws, phrase, first):
    key = [re.sub(r"[^a-z0-9']", '', x.lower()) for x in phrase.split()]
    for i in range(len(ws) - len(key) + 1):
        if [re.sub(r"[^a-z0-9']", '', ws[i + j]['word'].lower()) for j in range(len(key))] == key:
            return i if first else i + len(key) - 1
    sys.exit(f"phrase not found: {phrase}")


DROP = {'C9841': [(24.0, 32.6)],          # flub: "…beats all of them." + the 6.9s reset after it
        'C9842': [(14.93, 17.30)]}        # restart: "And I realized that there was a," before the clean take
SIL_DB, SIL_MIN, SIL_KEEP = -45, 0.20, 0.10   # cut any silence over 0.20s down to 0.10s

def silences(n):
    """Silent ranges straight from the waveform. Whisper's word gaps MISS silence it never transcribed —
    C9841 had 5 s of digital silence with no gap in the word list at all."""
    r = subprocess.run([FF, '-hide_banner', '-nostats', '-i', f'{P}/src/{n}.MP4',
                        '-af', f'silencedetect=noise={SIL_DB}dB:d={SIL_MIN}', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    out, st = [], None
    for m in re.finditer(r'silence_(start|end): (-?[\d.]+)', r):
        if m.group(1) == 'start': st = float(m.group(2))
        elif st is not None: out.append((st, float(m.group(2)))); st = None
    return out

def segments(n):
    """[in,out] pieces: trim the ends, drop flubs, and squeeze every silence to SIL_KEEP."""
    s, t = trim(n)
    cuts = [(a + SIL_KEEP / 2, b - SIL_KEEP / 2) for a, b in silences(n)
            if b - a > SIL_MIN and b > s and a < t]
    cuts += list(DROP.get(n, []))
    cuts = [(max(a, s), min(b, t)) for a, b in cuts if min(b, t) - max(a, s) > 0.05]
    cuts.sort()
    segs, cur = [], s
    for a, b in cuts:
        if a <= cur: cur = max(cur, b); continue
        segs.append([round(cur, 3), round(a, 3)]); cur = b
    if cur < t: segs.append([round(cur, 3), round(t, 3)])
    return [x for x in segs if x[1] - x[0] > 0.10]

def trim(n):
    """in/out points: snapped into the silence around the first/last kept word."""
    ws, e = words(n), env_db(n)
    a, b = anchor(ws, CLIPS[n][0], True), anchor(ws, CLIPS[n][1], False)
    thr = max(np.percentile(e, 12) + 6, -50)
    s = ws[a]['start']
    for k in range(30):
        if e[max(0, int((s - (k + 1) * .01) * 100)):int((s - k * .01) * 100) + 1].max() < thr:
            s = s - k * .01 - .12; break
    else: s -= .25
    t = ws[b]['end']
    for k in range(60):
        if e[int((t + k * .01) * 100):int((t + (k + 1) * .01) * 100) + 1].max() < thr:
            t = t + k * .01 + .25; break
    else: t += .5
    # never run into the next spoken word — continuous speech has no silence to stop at
    if b + 1 < len(ws): t = min(t, max(ws[b]['end'] + .10, ws[b + 1]['start'] - .04))
    return max(0, s), END_AT.get(n, t)

def captions(n, segs, out, marginv):
    fam, efam, size = 'Poppins SemiBold', 'Poppins ExtraBold', 88
    f = TTFont(FD + 'Poppins-ExtraBold.ttf', lazy=True)
    k = f['head'].unitsPerEm / (f['OS/2'].usWinAscent + f['OS/2'].usWinDescent)
    font = ImageFont.truetype(FD + 'Poppins-ExtraBold.ttf', max(1, round(size * k)))
    ws, off = [], 0.0
    for a, b in segs:
        for w in words(n):
            m = (w['start'] + w['end']) / 2
            if a <= m < b:
                for p in w['word'].split():
                    ws.append(dict(w=p, s=off + max(w['start'], a) - a, e=off + min(w['end'], b) - a))
        off += b - a
    for i in range(1, len(ws)):
        ws[i]['s'] = max(ws[i]['s'], ws[i - 1]['s'] + .01); ws[i]['e'] = max(ws[i]['e'], ws[i]['s'] + .05)
    cap = True
    for w in ws:
        if cap and w['w'][:1].isalpha(): w['w'] = w['w'][0].upper() + w['w'][1:]
        cap = bool(re.search(r'[.?!]$', w['w']))
    phrases, cur = [], []
    for i, w in enumerate(ws):
        cur.append(w); last = i == len(ws) - 1
        if last or re.search(r'[.?!,]$', w['w']) or (ws[i + 1]['s'] - w['e']) >= .32:
            phrases.append(cur); cur = []
    chunks = []
    for ph in phrases:
        nch = math.ceil(len(ph) / 4); i = 0
        for j in range(nch):
            sz = math.ceil((len(ph) - i) / (nch - j)); c = ph[i:i + sz]; i += sz
            while len(c) > 1 and font.getlength(' '.join(x['w'] for x in c)) > 840:
                h = len(c) // 2; chunks.append(c[:h]); c = c[h:]
            chunks.append(c)
    ev = []
    def ts(x): x = max(0, x); return f"{int(x//3600)}:{int(x%3600//60):02d}:{x%60:05.2f}"
    for i, c in enumerate(chunks):
        st = c[0]['s']; nx = chunks[i + 1][0]['s'] if i + 1 < len(chunks) else None
        en = nx if (nx is not None and nx - c[-1]['e'] < .55) else c[-1]['e'] + .2
        en = max(en, st + .4)
        if nx is not None: en = min(en, nx)
        toks = re.sub(r'[,.;:]+$', '', ' '.join(x['w'] for x in c)).split(' ')
        txt = ' '.join(f"{{\\fn{efam}\\1c&H00D4FF&}}{x}{{\\fn{fam}\\1c&H00FFFFFF&}}"
                       if (re.search(r'\d', x) or re.sub(r"[^\w'-]", '', x.lower()) in EMPH) else x for x in toks)
        ev.append(f"Dialogue: 0,{ts(st)},{ts(en)},Cap,,0,0,0,,{txt}")
    open(out, 'w').write(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\nWrapStyle: 2\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold,"
        " Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL,"
        " MarginR, MarginV, Encoding\n"
        f"Style: Cap,{fam},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H99000000,0,0,0,0,100,100,0.5,0,1,3,2,2,120,120,{marginv},1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" + '\n'.join(ev) + '\n')
    return len(ev)

def main():
    os.makedirs(f'{P}/deliver', exist_ok=True); os.makedirs(f'{P}/work', exist_ok=True)
    # one render at a time: two runs writing the same output file produce a corrupt mp4 (learned the hard way)
    import fcntl
    lock = open(f'{P}/work/.render.lock', 'w')
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: sys.exit('ANOTHER RENDER IS ALREADY RUNNING — refusing to start a second one')
    for n in CLIPS:
        fx = FACE[n]
        if len(sys.argv) > 1 and n not in sys.argv[1:]: continue
        segs = segments(n); src = f'{P}/src/{n}.MP4'
        x = int(min(max(fx - W // 2, 0), 3840 - W))
        kept = sum(b - a for a, b in segs)
        for variant, marginv in (('full', 540), ('boxed', 540)):   # 28% up from the bottom, clear of IG's UI
            ass = f'{P}/work/{n}_{variant}.ass'; ncue = captions(n, segs, ass, marginv)
            out = f'{P}/deliver/{n}_9x16-{variant}.mp4'
            if variant == 'boxed':     # 4K cut for the boxed layout (needs the whole frame)
                cut = f'{P}/work/{n}_cut.mov'   # doing cuts + grade + captions in one graph deadlocks ffmpeg
                if not os.path.exists(cut):     # ("Error sending frames to consumers: Operation timed out")
                    ins, pre = [], []
                    for i, (a_, b_) in enumerate(segs):
                        ins += ['-ss', f'{a_:.3f}', '-t', f'{b_ - a_:.3f}', '-i', src]
                        pre.append(f"[{i}:v]setsar=1,fps=30000/1001,format=yuv420p[v{i}];"
                                   f"[{i}:a]aresample=48000,afade=t=in:d=0.012,"
                                   f"afade=t=out:st={b_ - a_ - .015:.3f}:d=0.015[a{i}]")
                    cat = ''.join(f'[v{i}][a{i}]' for i in range(len(segs))) + f'concat=n={len(segs)}:v=1:a=1[cv][ca]'
                    sh([FF, '-y', '-hide_banner', '-loglevel', 'error', *ins,
                        '-filter_complex', ';'.join(pre) + ';' + cat, '-map', '[cv]', '-map', '[ca]',
                        '-c:v', 'libx264', '-crf', '12', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac', '-b:a', '256k', cut])
            if variant == 'full':
                cut = f'{P}/work/{n}_punch.mov'
                if not os.path.exists(cut):
                    parts = []
                    for i, (a_, b_) in enumerate(segs):
                        cw = PUNCH_CYCLE[i % len(PUNCH_CYCLE)]
                        ch = cw * 16 // 9 // 2 * 2
                        cx = int(min(max(fx - cw // 2, 0), 3840 - cw))
                        cy = (2160 - ch) // 2
                        seg = f'{P}/work/{n}_p{i:02d}.mp4'
                        sh([FF, '-y', '-hide_banner', '-loglevel', 'error', '-ss', f'{a_:.3f}',
                            '-t', f'{b_ - a_:.3f}', '-i', src,
                            '-vf', f"crop={cw}:{ch}:{cx}:{cy},scale={W}:{H}:flags=lanczos,setsar=1,fps=30000/1001",
                            '-af', f"aresample=48000,afade=t=in:d=0.012,afade=t=out:st={b_ - a_ - .015:.3f}:d=0.015",
                            '-c:v', 'libx264', '-crf', '12', '-preset', 'veryfast', '-pix_fmt', 'yuv420p',
                            '-c:a', 'aac', '-b:a', '256k', seg])
                        parts.append(seg)
                    lst = f'{P}/work/{n}_punch.txt'
                    open(lst, 'w').write(''.join(f"file '{x}'\n" for x in parts))
                    sh([FF, '-y', '-hide_banner', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
                        '-i', lst, '-c', 'copy', cut])
                    for x in parts: os.remove(x)
                vf = f"{DENOISE},{GRADE},subtitles={ass}:fontsdir={FD},setsar=1"
                vmap = ['-vf', vf, '-map', '0:v:0']
            else:
                bx = int(min(max(fx - BOX_W // 2, 0), 3840 - BOX_W))
                vf = (f"[0:v]{DENOISE},{GRADE},crop={BOX_W}:{BOX_H}:{bx}:0,split[bg][fg];"
                      f"[bg]scale=-2:{H},crop={W}:{H},boxblur=40:2,eq=brightness=-0.14:saturation=0.65[b];"
                      f"[fg]scale={W}:{BOX_SCALE_H}[f];[b][f]overlay=0:{int(380 * W / 1216)}:shortest=1[v1];"
                      f"[1:v]scale={int(W * 0.22)}:-1[lg];[v1][lg]overlay=(W-w)/2:{int(150 * W / 1216)},"
                      f"subtitles={ass}:fontsdir={FD},setsar=1[out]")
                vmap = ['-i', LOGO, '-filter_complex', vf, '-map', '[out]']
            sh([FF, '-y', '-hide_banner', '-loglevel', 'error', '-i', cut, *vmap, '-map', '0:a:0',
                '-c:v', 'libx264', '-crf', '15', '-preset', 'slow', '-profile:v', 'high',
                '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-c:a', 'copy', out])
            d = sh([FF.replace('ffmpeg', 'ffprobe'), '-v', 'error', '-show_entries', 'format=duration',
                    '-of', 'csv=p=0', out]).stdout.strip()
            print(f"{os.path.basename(out):<28} {float(d):5.1f}s  {len(segs)} pieces  {ncue} cues  "
                  f"{os.path.getsize(out)/1e6:5.0f} MB")

if __name__ == '__main__':
    main()

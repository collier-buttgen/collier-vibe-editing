#!/usr/bin/env python3
"""QC every deliverable: (1) Collier-only gate at 5 fps over the kept source ranges,
(2) loudness, (3) a 5-frame strip per clip into frames/qc/.  Exit 1 if any gate fails."""
import json, os, subprocess, sys, glob
import pathlib as _pl, shutil as _sh
KIT = _pl.Path(__file__).resolve().parents[2]                       # repo root (recipes/<name>/<script>.py)
FF = _sh.which('ffmpeg') or str(_pl.Path.home() / '.local/bin/ffmpeg')
FD = str(KIT / 'plugins/vibe-editing/skills/caption-clips/fonts/_all') + '/'
KEYS = KIT / 'plugins/vibe-editing/config/keys.env'
import numpy as np
P = os.environ.get('PROJECT') or sys.exit('Set PROJECT=/path/to/project (with source.mp4, tx/, work/) — see README.md'); 
SRC = P + '/source.mp4'; os.makedirs(P + '/frames/qc', exist_ok=True)

def frames(s, e, fps=5):
    raw = subprocess.run([FF, '-v', 'error', '-ss', f'{s:.3f}', '-t', f'{e - s:.3f}', '-i', SRC, '-vf',
                          f'fps={fps},scale=192:108:flags=area', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 108, 192, 3).astype(np.float32)

lab = json.load(open(P + '/work/layout.json'))
low = np.fromfile(P + '/work/lowres.rgb', np.uint8).reshape(-1, 108, 192, 3).astype(np.float32)
tile_ref = np.median(low[[1500, 1600, 1700, 2000, 2500], 8:21, 166:190], axis=0)
bad = 0
for d in sorted(glob.glob(P + '/work/*/cutlist.json')):
    name = d.split('/')[-2]; c = json.load(open(d)); out = P + f'/deliver/{name}.mp4'
    fr = np.concatenate([frames(s, e) for s, e in c['segs']])
    if c['kind'] == 'face':
        ref = np.median(fr, axis=0); dist = np.abs(fr - ref).mean(axis=(1, 2, 3))
        share = (fr[:, 10:100, 2:17].mean(axis=(1, 2, 3)) < 22)
        flag = (dist > 38) | share
    else:
        dist = np.abs(fr[:, 8:21, 166:190] - tile_ref).mean(axis=(1, 2, 3))
        flag = dist > 30
    m = subprocess.run([FF, '-hide_banner', '-nostats', '-i', out, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    I = [l for l in m.splitlines() if l.strip().startswith('I:')][-1].split()[1]
    dur = float(subprocess.run([FF.replace('ffmpeg', 'ffprobe'), '-v', 'error', '-show_entries', 'format=duration', '-of',
                                'csv=p=0', out], capture_output=True, text=True).stdout)
    ok = flag.sum() == 0 and abs(float(I) + 14) < 0.6
    bad += not ok
    print(f"{'OK ' if ok else 'BAD'} {name:<24} {c['kind']:<6} {dur:5.1f}s  {I} LUFS  flagged frames {int(flag.sum())}/{len(flag)}"
          + (f"  max dist {dist.max():.0f}" if flag.sum() else ''))
    ins = []
    for k, t in enumerate(np.linspace(0.3, dur - 0.3, 5)):
        f = P + f'/frames/qc/{name}_{k}.png'
        subprocess.run([FF, '-y', '-v', 'error', '-ss', f'{t:.2f}', '-i', out, '-frames:v', '1', '-vf', 'scale=216:384', f])
        ins += ['-i', f]
    subprocess.run([FF, '-y', '-v', 'error', *ins, '-filter_complex', 'hstack=5', P + f'/frames/qc/{name}.png'])
sys.exit(1 if bad else 0)

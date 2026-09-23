#!/usr/bin/env python3
"""Measure and remove grain/noise from video. Never changes resolution, frame rate or audio.

    denoise.py --detect  IN [IN ...]              # score each file: how grainy is it?
    denoise.py IN OUT [--strength auto|light|medium|strong] [--crf 16]

Detection samples frames, takes the residual against a 3x3 median (that's the grain), and measures it
only in FLAT areas, so edges and detail don't count. Score ≈ noise in 0-255 levels:

    < 0.8   clean        — leave it alone
    0.8-1.5 light grain  — hqdn3d light
    1.5-2.5 grainy       — hqdn3d medium
    > 2.5   heavy        — nlmeans (slow, much stronger)

House rules: audio is copied through untouched, and the picture keeps its native size (4K stays 4K).
"""
import argparse, os, subprocess, sys
import numpy as np
from scipy.ndimage import median_filter, uniform_filter

FF = __import__('shutil').which('ffmpeg') or os.path.expanduser('~/.local/bin/ffmpeg')
FP = FF.replace('ffmpeg', 'ffprobe')
PRESETS = {'light':  'hqdn3d=1.5:1.5:6:6',
           'medium': 'hqdn3d=3:2:8:8',
           'strong': 'nlmeans=s=3.0:p=7:r=15'}

def probe(path):
    r = subprocess.run([FP, '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                        'stream=width,height:format=duration', '-of', 'csv=p=0', path],
                       capture_output=True, text=True)
    out = r.stdout.split()
    if not out: sys.exit(f"cannot read {path}: {r.stderr.strip()[:200]}")
    w, h = out[0].split(',')[:2]; dur = float(out[-1])
    return int(w), int(h), dur

def score(path, n=9):
    """Median noise level (0-255) over n frames, measured in flat areas only."""
    w, h, dur = probe(path)
    vals = []
    for k in range(n):
        t = dur * (k + .5) / n
        raw = subprocess.run([FF, '-v', 'error', '-ss', f'{t:.2f}', '-i', path, '-frames:v', '1',
                              '-vf', 'format=gray,scale=960:-2', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                             capture_output=True).stdout
        if not raw: continue
        g = np.frombuffer(raw, np.uint8).astype(np.float32).reshape(-1, 960)
        resid = g - median_filter(g, size=3)
        # flat = low local variance in the MEDIAN-filtered image (so the grain itself doesn't mark it busy)
        m = median_filter(g, size=3)
        var = uniform_filter(m ** 2, 9) - uniform_filter(m, 9) ** 2
        flat = var < np.percentile(var, 40)
        if flat.sum() < 500: continue
        vals.append(1.4826 * np.median(np.abs(resid[flat])))       # MAD → sigma
    return float(np.median(vals)) if vals else 0.0

def verdict(s):
    return ('clean', None) if s < 0.8 else ('light grain', 'light') if s < 1.5 else \
           ('grainy', 'medium') if s < 2.5 else ('heavy grain', 'strong')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--detect', action='store_true')
    ap.add_argument('--strength', default='auto', choices=['auto', 'light', 'medium', 'strong'])
    ap.add_argument('--crf', default='16')
    a = ap.parse_args()

    if a.detect:
        for p in a.paths:
            s = score(p); label, rec = verdict(s)
            print(f"{os.path.basename(p):<40} noise {s:4.2f}  {label}" + (f"  → --strength {rec}" if rec else ""))
        return

    if len(a.paths) != 2: sys.exit("usage: denoise.py IN OUT [--strength ...]   (or --detect IN ...)")
    src, out = a.paths
    s = score(src); label, rec = verdict(s)
    strength = rec if a.strength == 'auto' else a.strength
    if strength is None:
        print(f"noise {s:.2f} ({label}) — nothing to clean. Copying through untouched.")
        subprocess.run([FF, '-y', '-v', 'error', '-i', src, '-c', 'copy', out], check=True); return
    w, h, _ = probe(src)
    print(f"noise {s:.2f} ({label}) → {strength}: {PRESETS[strength]}   keeping {w}x{h}, audio untouched")
    subprocess.run([FF, '-y', '-hide_banner', '-loglevel', 'error', '-i', src, '-vf', PRESETS[strength],
                    '-c:v', 'libx264', '-crf', a.crf, '-preset', 'slow', '-profile:v', 'high',
                    '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-c:a', 'copy', out], check=True)
    print(f"after: noise {score(out):.2f}  →  {out}")

if __name__ == '__main__':
    main()

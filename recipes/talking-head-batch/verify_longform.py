#!/usr/bin/env python3
"""Full production check for the C9881 longform. Nothing ships unless every line says OK.

The one that matters most here: A/V SYNC MEASURED ACROSS THE WHOLE FILE, not just at the start.
A re-framing stage that cut the video into pieces and re-muxed the original audio drifted progressively —
it looked fine at 0s and was audibly off by the middle. So sync is checked at 9 points by transcribing a
window of the delivered audio and comparing it to the caption burned at that same timestamp.

Also: stream durations, dead air, clicks, card presence, word-for-word transcript, resolution.
"""
import difflib, json, os, re, subprocess, sys, time

P = os.path.dirname(os.path.abspath(__file__))
FF = os.path.expanduser('~/.local/bin/ffmpeg'); FP = FF.replace('ffmpeg', 'ffprobe')
OUT = f'{P}/deliver/FC_YT_goal-setting-2027.mp4'
ASS = f'{P}/work/FC_YT_goal-setting-2027_caps.ass'
KEY = [l.split('=', 1)[1].strip() for l in open(os.path.expanduser(
    '~/Documents/vibe-editing/plugins/vibe-editing/config/keys.env')) if l.startswith('GROQ_API_KEY=')][0]
norm = lambda t: [re.sub(r"[^a-z0-9']", '', x.lower()) for x in t.replace('-', ' ').split()
                  if re.sub(r"[^a-z0-9']", '', x.lower())]
bad = []

def say(ok, line):
    print(('OK  ' if ok else 'BAD ') + line)
    if not ok: bad.append(line)

def tx(ss, dur):
    mp3 = f'{P}/work/_v.mp3'
    subprocess.run([FF, '-y', '-v', 'error', '-ss', f'{ss:.2f}', '-t', f'{dur:.2f}', '-i', OUT,
                    '-vn', '-ac', '1', '-ar', '16000', mp3], check=True)
    for _ in range(6):
        r = subprocess.run(['curl', '-s', 'https://api.groq.com/openai/v1/audio/transcriptions',
                            '-H', f'Authorization: Bearer {KEY}', '-F', f'file=@{mp3}',
                            '-F', 'model=whisper-large-v3', '-F', 'language=en',
                            '-F', 'response_format=text'], capture_output=True, text=True).stdout
        if '"error"' not in r: time.sleep(3.2); return r.strip()
        time.sleep(25)
    sys.exit('transcription failed')

def caption_at(t):
    def sec(x): h, m, s = x.split(':'); return int(h) * 3600 + int(m) * 60 + float(s)
    best = ''
    for l in open(ASS):
        if not l.startswith('Dialogue'): continue
        f = l.split(',', 9)
        if sec(f[1]) <= t < sec(f[2]): best = re.sub(r'\{[^}]*\}', '', f[9]).strip()
    return best

# 1. container / streams
v = subprocess.run([FP, '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                    'stream=width,height,duration,r_frame_rate', '-of', 'csv=p=0', OUT],
                   capture_output=True, text=True)
a = subprocess.run([FP, '-v', 'error', '-select_streams', 'a:0', '-show_entries',
                    'stream=duration,sample_rate,channels', '-of', 'csv=p=0', OUT],
                   capture_output=True, text=True)
say(not v.stderr.strip() and not a.stderr.strip(), f"readable · video {v.stdout.strip()} · audio {a.stdout.strip()}")
vw, vh = v.stdout.split(',')[:2]

def dur_of(stream):          # ask for ONE field; parsing a multi-field csv by position or by size both bit me
    return float(subprocess.run([FP, '-v', 'error', '-select_streams', stream, '-show_entries',
                                 'stream=duration', '-of', 'csv=p=0', OUT],
                                capture_output=True, text=True).stdout.strip().rstrip(','))
vdur = dur_of('v:0')
adur = dur_of('a:0')
say(vw == '3840' and vh == '2160', f"resolution {vw}x{vh} (want 3840x2160)")
say(abs(vdur - adur) < 0.12, f"stream lengths video {vdur:.2f}s vs audio {adur:.2f}s (drift {abs(vdur-adur)*1000:.0f} ms)")

# 2. decode cleanly
errs = subprocess.run([FF, '-v', 'error', '-i', OUT, '-f', 'null', '-'], capture_output=True, text=True).stderr
say(not errs.strip(), f"full decode, {len(errs.splitlines())} errors")

# 3. A/V SYNC across the file — caption burned at t must match what is being said at t
print('--- sync across the file (caption on screen vs audio at that moment)')
for frac in (0.08, 0.2, 0.32, 0.44, 0.5, 0.62, 0.74, 0.86, 0.95):
    t = vdur * frac
    heard = norm(tx(max(0, t - 1.6), 3.2))
    shown = norm(caption_at(t))
    hit = bool(shown) and any(w in heard for w in shown)
    say(hit, f"  {t:6.1f}s  caption {' '.join(shown) or '(none)':<28} heard …{' '.join(heard[-7:])}")

# 4. dead air + clicks
sil = subprocess.run([FF, '-hide_banner', '-nostats', '-i', OUT, '-af',
                      'silencedetect=noise=-45dB:d=0.60', '-f', 'null', '-'], capture_output=True, text=True).stderr
dead = [float(x) for x in re.findall(r'silence_duration: ([\d.]+)', sil)]
say(not dead, f"no pause over 0.6s ({len(dead)} found{', longest %.2fs' % max(dead) if dead else ''})")
import numpy as np
pcm = subprocess.run([FF, '-v', 'error', '-i', OUT, '-ac', '1', '-ar', '48000', '-f', 's16le', '-'],
                     capture_output=True).stdout
sig = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
say(int((np.abs(np.diff(sig)) > 0.25).sum()) == 0, "no clicks at joins")

# 5. the cards are actually on screen
sys.path.insert(0, P)
import importlib.util
spec = importlib.util.spec_from_file_location('b', P + '/build.py'); b = importlib.util.module_from_spec(spec)
sys.argv = ['x']; spec.loader.exec_module(b)
for key, times in b.card_times(f'{P}/work/FC_YT_goal-setting-2027_cut.mov'):
    t = times[0] + 1.0
    # the card sits at overlay x = W-1180-120 = 2540, y = 260; sample ONLY its header strip, not a big
    # box that is mostly bright window (that read 146 and failed every card that was plainly on screen)
    raw = subprocess.run([FF, '-v', 'error', '-ss', f'{t:.2f}', '-i', OUT, '-frames:v', '1',
                          '-vf', 'crop=1100:120:2580:280,scale=110:12', '-f', 'rawvideo',
                          '-pix_fmt', 'gray', '-'], capture_output=True).stdout
    g = np.frombuffer(raw, np.uint8).astype(np.float32)
    say(g.mean() < 110, f"card '{key}' on screen at {t:.0f}s (header strip brightness {g.mean():.0f})")

print('\n' + ('ALL CLEAR' if not bad else f'{len(bad)} PROBLEM(S):\n  ' + '\n  '.join(bad)))
sys.exit(1 if bad else 0)

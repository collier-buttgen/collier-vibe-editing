#!/usr/bin/env python3
"""Captions for the webinar ad (Week 1 playbook p.12) — v4 / r2.

Static, word-timed, 1 line, max 5 words, sentence case, centred, baseline at 78% of frame height.
Nothing moves: no drop-in, no size change, no karaoke.

CAP_STYLE picks the look (r2: Collier asked for a different caption look per video):
  box    — Poppins SemiBold 84, white on a 70% black box (the playbook spec, enlarged)
  shadow — Poppins ExtraBold 84, white, thin dark outline + shadow, no box; emphasis in yellow #FFD400
  brand  — Poppins Bold 82, white on a 90% navy #101726 box; emphasis in ice #4CC8F0

Sizes are libass Fontsize. libass sizes Poppins so usWinAscent+usWinDescent == Fontsize (~0.57x of PIL
at the same number) — the width guard measures the libass-true size.

HOOK/BODY SPLIT IS TEXT-ANCHORED (v4). Whisper stamps words near a hard cut unreliably in BOTH
directions: the first body word starts up to ~0.5s early, the last hook word ends late. Any
timestamp rule drops or steals a word (r2 shipped "Don't need 17 cages" and a body opening on the
previous hook's "dollars"). So the split finds the body's opening words (BODY_OPEN, default
"you don't") within 1s of the cut and splits there; times are then clamped to the cut.

Usage: [CAP_STYLE=..] [BODY_OPEN="you don't"] build_captions.py <hook_tx> <hook_dur> <body_tx> <body_tx_hook_dur> <out.ass>
"""
import json, math, os, re, sys
from PIL import ImageFont
from fontTools.ttLib import TTFont

MAX_WORDS, BREAK_GAP, HOLD_GAP, MIN_DUR = 5, 0.35, 0.60, 0.45
FD = str(__import__("pathlib").Path(__file__).resolve().parents[2] / "plugins/vibe-editing/skills/caption-clips/fonts/_all") + "/"
STYLES = {
    "box":    dict(family="Poppins SemiBold",  file="Poppins-SemiBold.ttf",  size=84, primary="&H00FFFFFF",
                   outline="&H4D000000", back="&H4D000000", border=3, out=26, shadow=0, spacing=0,   accent=None),
    "shadow": dict(family="Poppins ExtraBold", file="Poppins-ExtraBold.ttf", size=84, primary="&H00FFFFFF",
                   outline="&H00000000", back="&H80000000", border=1, out=3,  shadow=3, spacing=1.5, accent="&H00D4FF&"),
    "brand":  dict(family="Poppins Bold",      file="Poppins-Bold.ttf",      size=82, primary="&H00FFFFFF",
                   outline="&H1A261710", back="&H1A261710", border=3, out=26, shadow=0, spacing=0,   accent="&HF0C84C&"),
}
S = STYLES[os.environ.get("CAP_STYLE", "box")]
BODY_OPEN = os.environ.get("BODY_OPEN", "you don't").lower().split()
EMPH = {"not", "don't", "zero", "one", "two", "three", "profit", "offer", "lease", "job", "wednesday"}
NUM = re.compile(r"^\$?[\d][\d,.]*[,]?$")

def _k(path):
    f = TTFont(path, lazy=True); k = f["head"].unitsPerEm / (f["OS/2"].usWinAscent + f["OS/2"].usWinDescent); f.close(); return k
FONT = ImageFont.truetype(FD + S["file"], max(1, round(S["size"] * _k(FD + S["file"]))))
MAX_W = 960 - 2 * S["out"]
HEADER = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\nWrapStyle: 2\n\n"
          "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
          "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
          "MarginR, MarginV, Encoding\n"
          f"Style: Cap,{S['family']},{S['size']},{S['primary']},&H00FFFFFF,{S['outline']},{S['back']},0,0,0,0,100,100,"
          f"{S['spacing']},0,{S['border']},{S['out']},{S['shadow']},2,60,60,422,1\n\n"
          "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

def ts(t):
    t = max(0.0, t); return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"

def load(path):
    out = []
    for w in json.load(open(path))["words"]:
        txt = w["word"].strip()
        if not txt: continue
        s, e = float(w["start"]), float(w["end"]); parts = txt.split(); total = sum(len(p) for p in parts) or 1; cur = s
        for p in parts:                                   # split glued tokens by character share
            d = (e - s) * len(p) / total; out.append(dict(w=p, s=cur, e=cur + d)); cur += d
    return out

def norm(x): return re.sub(r"[^a-z']", "", x.lower())

def body_index(ws, cut):
    n = len(BODY_OPEN)
    c = [i for i in range(len(ws) - n + 1)
         if [norm(ws[i+j]["w"]) for j in range(n)] == BODY_OPEN and abs(ws[i]["s"] - cut) <= 1.0]
    if not c: sys.exit(f"ABORT: body opener '{' '.join(BODY_OPEN)}' not found within 1s of cut {cut}")
    return min(c, key=lambda i: abs(ws[i]["s"] - cut))

def phrases(ws):
    ph, cur = [], []
    for i, w in enumerate(ws):
        cur.append(w); last = i == len(ws) - 1
        gap = 0 if last else ws[i+1]["s"] - w["e"]
        ends = bool(re.search(r"[.?!]$", w["w"]))
        comma = w["w"].endswith(",") and not (NUM.match(w["w"]) and not last and NUM.match(ws[i+1]["w"].rstrip(",")))
        if last or ends or comma or gap >= BREAK_GAP: ph.append(cur); cur = []
    return ph

def balanced(ph):
    n = len(ph); k = math.ceil(n / MAX_WORDS); out, i = [], 0
    for j in range(k):
        size = math.ceil((n - i) / (k - j)); out.append(ph[i:i+size]); i += size
    fixed = []
    for c in out:
        while len(c) > 1 and FONT.getlength(" ".join(x["w"] for x in c)) > MAX_W:
            h = len(c) // 2; fixed.append(c[:h]); c = c[h:]
        fixed.append(c)
    return fixed

def render(words):
    plain = re.sub(r"[,.;:]+$", "", " ".join(words))
    if not S["accent"]: return plain, plain
    out = []
    for t in plain.split(" "):
        hot = bool(re.search(r"\d", t)) or re.sub(r"[^\w$',]", "", t.lower()).strip(",") in EMPH
        out.append(f"{{\\1c{S['accent']}}}{t}{{\\1c&HFFFFFF&}}" if hot else t)
    return plain, " ".join(out)

def main(hook_tx, hook_dur, body_tx, body_hook_dur, out):
    hook_dur, body_hook_dur = float(hook_dur), float(body_hook_dur)
    hw = load(hook_tx);  hb = body_index(hw, hook_dur)
    bw = load(body_tx);  bb = body_index(bw, body_hook_dur); shift = hook_dur - body_hook_dur
    hook = [dict(w=x["w"], s=min(x["s"], hook_dur - 0.05), e=min(x["e"], hook_dur)) for x in hw[:hb]]
    body = [dict(w=x["w"], s=max(x["s"] + shift, hook_dur), e=max(x["e"] + shift, hook_dur + 0.05)) for x in bw[bb:]]
    ws = hook + body
    cap = True
    for w in ws:                                          # sentence case
        if cap and w["w"][:1].isalpha(): w["w"] = w["w"][0].upper() + w["w"][1:]
        cap = bool(re.search(r"[.?!]$", w["w"]))
    ws[len(hook)]["w"] = ws[len(hook)]["w"][0].upper() + ws[len(hook)]["w"][1:]   # body opens a sentence
    chunks = [c for p in phrases(hook) for c in balanced(p)] + [c for p in phrases(body) for c in balanced(p)]
    lines = []
    for i, c in enumerate(chunks):
        start = c[0]["s"]; nxt = chunks[i+1][0]["s"] if i + 1 < len(chunks) else None
        end = nxt if (nxt is not None and nxt - c[-1]["e"] < HOLD_GAP) else c[-1]["e"] + 0.15
        end = max(end, start + MIN_DUR)
        if nxt is not None: end = min(end, nxt)
        plain, styled = render([x["w"] for x in c]); lines.append((start, end, plain, styled))
    open(out, "w").write(HEADER + "\n".join(f"Dialogue: 0,{ts(a)},{ts(b)},Cap,,0,0,0,,{s}" for a, b, _, s in lines) + "\n")
    worst = max(len(p.split()) for *_, p, _ in lines); widest = max(FONT.getlength(p) for *_, p, _ in lines)
    print(f"[{os.environ.get('CAP_STYLE','box')}] {len(lines)} cues · max {worst} words · widest {widest:.0f}/{MAX_W}px -> {os.path.basename(out)}")

if __name__ == "__main__":
    main(*sys.argv[1:6])

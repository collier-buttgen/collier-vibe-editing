#!/usr/bin/env python3
"""Drag caption position before the burn.

Built for Collier 2026-08-26. The kit had no way to nudge caption Y by hand — only the
automatic layout track from layout_analyze.py. This opens a local page where you drag each
caption up/down over the real video, then writes a layout track that generate_spice.py
consumes with --layout.

    python3 tools/caption_place.py <video.mp4> <subs.ass> --out layout.json

Then re-burn with the placement applied:

    python3 skills/caption-clips/scripts/generate_spice.py <transcript.json> \
        --preset <preset.json> --layout layout.json --out subs.ass \
        --burn <video.mp4> --burn-out <final.mp4>

Nothing leaves the machine — the server binds to 127.0.0.1 and stops when you hit Save.
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys, os, threading, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ASS_TIME = re.compile(r"(\d+):(\d\d):(\d\d)\.(\d\d)")
OVERRIDE = re.compile(r"\{[^}]*\}")
POSY     = re.compile(r"\\(?:move|pos)\((?:[-\d.]+),\s*([-\d.]+)")


def t2s(t: str) -> float:
    m = ASS_TIME.fullmatch(t.strip())
    if not m:
        return 0.0
    h, mi, s, cs = (int(x) for x in m.groups())
    return h * 3600 + mi * 60 + s + cs / 100.0


def probe(video: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,r_frame_rate,duration", "-of", "json", str(video)],
        capture_output=True, text=True).stdout
    st = json.loads(out)["streams"][0]
    num, den = (st.get("r_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den or 1)
    dur = float(st.get("duration") or 0) or None
    if dur is None:
        d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", str(video)],
                           capture_output=True, text=True).stdout.strip()
        dur = float(d or 0)
    return {"w": int(st["width"]), "h": int(st["height"]), "fps": fps, "dur": dur}


def parse_ass(ass: Path, frame_h: int) -> tuple[list[dict], int]:
    """Return the TEXT cues only (layer 1), with their current Y as a 0..1 fraction."""
    play_y = frame_h
    cues, seen = [], set()
    for line in ass.read_text(errors="replace").splitlines():
        if line.startswith("PlayResY:"):
            try: play_y = int(line.split(":", 1)[1].strip())
            except ValueError: pass
        if not line.startswith("Dialogue:"):
            continue
        body = line.split(":", 1)[1]
        parts = body.split(",", 9)
        if len(parts) < 10:
            continue
        layer, start, end, style, raw = parts[0].strip(), parts[1], parts[2], parts[3].strip(), parts[9]
        # layer 0 = the blurred shadow copy; the bubble layer draws \p1 vector shapes.
        if layer != "1" or style == "SpiceShadow" or "\\p1" in raw:
            continue
        text = OVERRIDE.sub("", raw).replace("\\N", " ").strip()
        if not text:
            continue
        my = POSY.search(raw)
        y_pct = (float(my.group(1)) / play_y) if my else 0.5
        key = (start.strip(), end.strip())
        if key in seen:
            continue
        seen.add(key)
        cues.append({"i": len(cues), "start": t2s(start), "end": t2s(end),
                     "text": text, "y": round(y_pct, 4), "orig": round(y_pct, 4)})
    return cues, play_y


PAGE = r"""<!doctype html><meta charset=utf-8><title>Caption placement</title>
<style>
 :root{--bg:#101726;--sur:#19222F;--bd:#26313F;--ice:#4CC8F0;--yel:#FFD400;--tx:#fff;--mut:#8A90A8}
 *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--tx);
   font:14px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;display:flex;height:100vh;overflow:hidden}
 #left{flex:0 0 auto;padding:16px;display:flex;flex-direction:column;gap:10px}
 #stage{position:relative;background:#000;border:1px solid var(--bd);border-radius:4px;overflow:hidden}
 video{display:block;height:72vh;width:auto}
 #cap{position:absolute;left:0;right:0;text-align:center;cursor:grab;user-select:none;
   transform:translateY(-50%);padding:6px 0}
 #cap.drag{cursor:grabbing}
 #cap span{display:inline-block;background:rgba(16,23,38,.55);border:1px dashed var(--ice);
   color:#fff;font-weight:800;padding:4px 12px;border-radius:3px;max-width:88%}
 #guide{position:absolute;left:0;right:0;border-top:1px dashed rgba(255,212,0,.55);display:none}
 #right{flex:1;min-width:340px;border-left:1px solid var(--bd);background:var(--sur);
   display:flex;flex-direction:column;height:100vh}
 header{padding:14px 16px;border-bottom:1px solid var(--bd)}
 h1{margin:0 0 4px;font-size:15px;letter-spacing:.02em}
 .mut{color:var(--mut);font-size:12px}
 #list{flex:1;overflow:auto;padding:8px 10px}
 .row{display:flex;gap:8px;align-items:center;padding:7px 8px;border-radius:4px;cursor:pointer;
   border:1px solid transparent}
 .row:hover{background:#212B3A}
 .row.on{background:#212B3A;border-color:var(--ice)}
 .row b{flex:1;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
 .row i{font-style:normal;color:var(--mut);font-variant-numeric:tabular-nums;font-size:12px}
 .row em{font-style:normal;color:var(--yel);font-size:11px}
 footer{padding:12px 16px;border-top:1px solid var(--bd);display:flex;gap:8px;flex-wrap:wrap}
 button{font:inherit;font-weight:600;padding:9px 14px;border-radius:4px;border:1px solid var(--bd);
   background:#212B3A;color:#fff;cursor:pointer}
 button.p{background:var(--ice);color:#06212c;border-color:var(--ice)}
 button:disabled{opacity:.5;cursor:default}
 kbd{background:#0b1220;border:1px solid var(--bd);border-radius:3px;padding:1px 5px;font-size:11px}
</style>
<div id=left>
  <div id=stage>
    <video id=v src="/video" preload=auto></video>
    <div id=guide></div>
    <div id=cap><span>—</span></div>
  </div>
  <div class=mut>Drag the caption up or down · <kbd>space</kbd> play/pause ·
     <kbd>←</kbd><kbd>→</kbd> prev/next cue · <kbd>↑</kbd><kbd>↓</kbd> nudge 0.5%</div>
</div>
<div id=right>
  <header><h1>Caption placement</h1>
    <div class=mut id=meta></div></header>
  <div id=list></div>
  <footer>
    <button class=p id=save>Save &amp; close</button>
    <button id=allfrom>Apply to all after</button>
    <button id=all>Apply to all</button>
    <button id=reset>Reset</button>
  </footer>
</div>
<script>
const D = __DATA__;
const v=document.getElementById('v'), cap=document.getElementById('cap'),
      stage=document.getElementById('stage'), list=document.getElementById('list'),
      guide=document.getElementById('guide');
document.getElementById('meta').textContent =
  D.cues.length+' captions · '+D.w+'×'+D.h+' · '+D.fps.toFixed(2)+' fps';
let cur=0, dirty=false;

function rows(){
  list.innerHTML='';
  D.cues.forEach((c,i)=>{
    const r=document.createElement('div'); r.className='row'+(i===cur?' on':''); r.dataset.i=i;
    const moved = Math.abs(c.y-c.orig)>0.001;
    r.innerHTML='<i>'+c.start.toFixed(2)+'s</i><b></b>'+
                '<em>'+(c.y*100).toFixed(1)+'%'+(moved?' •':'')+'</em>';
    r.querySelector('b').textContent=c.text;
    r.onclick=()=>{cur=i; v.currentTime=c.start+0.01; draw();};
    list.appendChild(r);
  });
}
function activeAt(t){
  for(let i=0;i<D.cues.length;i++){const c=D.cues[i]; if(t>=c.start&&t<c.end) return i;}
  return -1;
}
function draw(){
  const c=D.cues[cur]; if(!c) return;
  cap.style.top=(c.y*100)+'%';
  cap.querySelector('span').textContent=c.text;
  guide.style.top=(c.y*100)+'%';
  [...list.children].forEach(r=>r.classList.toggle('on',+r.dataset.i===cur));
  const on=list.children[cur]; if(on) on.scrollIntoView({block:'nearest'});
  const em=on&&on.querySelector('em');
  if(em) em.textContent=(c.y*100).toFixed(1)+'%'+(Math.abs(c.y-c.orig)>0.001?' •':'');
}
v.addEventListener('timeupdate',()=>{const i=activeAt(v.currentTime); if(i>=0&&i!==cur){cur=i;draw();}});
v.addEventListener('loadeddata',()=>{rows();draw();});

let dragging=false;
cap.addEventListener('mousedown',e=>{dragging=true;cap.classList.add('drag');
  guide.style.display='block';e.preventDefault();});
window.addEventListener('mouseup',()=>{dragging=false;cap.classList.remove('drag');
  guide.style.display='none';});
window.addEventListener('mousemove',e=>{
  if(!dragging) return;
  const b=v.getBoundingClientRect();
  let y=(e.clientY-b.top)/b.height;
  y=Math.max(0.06,Math.min(0.94,y));
  D.cues[cur].y=Math.round(y*1e4)/1e4; dirty=true; draw();
});
addEventListener('keydown',e=>{
  if(e.key===' '){e.preventDefault(); v.paused?v.play():v.pause();}
  else if(e.key==='ArrowRight'){e.preventDefault();cur=Math.min(cur+1,D.cues.length-1);
    v.currentTime=D.cues[cur].start+0.01;draw();}
  else if(e.key==='ArrowLeft'){e.preventDefault();cur=Math.max(cur-1,0);
    v.currentTime=D.cues[cur].start+0.01;draw();}
  else if(e.key==='ArrowUp'||e.key==='ArrowDown'){e.preventDefault();
    const d=(e.key==='ArrowUp'?-0.005:0.005);
    D.cues[cur].y=Math.max(0.06,Math.min(0.94,+(D.cues[cur].y+d).toFixed(4)));dirty=true;draw();}
});
document.getElementById('all').onclick=()=>{const y=D.cues[cur].y;
  D.cues.forEach(c=>c.y=y);dirty=true;rows();draw();};
document.getElementById('allfrom').onclick=()=>{const y=D.cues[cur].y;
  D.cues.slice(cur).forEach(c=>c.y=y);dirty=true;rows();draw();};
document.getElementById('reset').onclick=()=>{D.cues.forEach(c=>c.y=c.orig);dirty=true;rows();draw();};
document.getElementById('save').onclick=async()=>{
  const b=document.getElementById('save'); b.disabled=true; b.textContent='Saving…';
  await fetch('/save',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({cues:D.cues.map(c=>({start:c.start,end:c.end,y:c.y}))})});
  b.textContent='Saved — you can close this tab';
  document.body.style.opacity=.6;
};
</script>"""


def build_layout(cues, fps, dur):
    segs = []
    for c in cues:
        s = max(0, int(round(c["start"] * fps)))
        e = max(s, int(round(c["end"] * fps)) - 1)
        segs.append({"start_i": s, "end_i": e, "safe_y_pct": round(float(c["y"]), 4)})
    return {"meta": {"fps": fps, "duration": dur,
                     "_source": "tools/caption_place.py — hand-placed by the user"},
            "segments": segs}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("ass", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    for f in (a.video, a.ass):
        if not f.exists():
            print(f"missing: {f}", file=sys.stderr); return 2

    info = probe(a.video)
    cues, _ = parse_ass(a.ass, info["h"])
    if not cues:
        print("No text cues found in the .ass — nothing to place.", file=sys.stderr); return 1
    print(f"  {len(cues)} captions · {info['w']}x{info['h']} · {info['fps']:.2f} fps")

    data = {"w": info["w"], "h": info["h"], "fps": info["fps"], "cues": cues}
    page = PAGE.replace("__DATA__", json.dumps(data))
    done = threading.Event()
    vsize = a.video.stat().st_size

    class H(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            if self.path.startswith("/video"):
                rng = self.headers.get("Range")
                start, end = 0, vsize - 1
                if rng and rng.startswith("bytes="):
                    p = rng[6:].split("-")
                    if p[0]:
                        start = int(p[0])
                    if len(p) > 1 and p[1]:
                        end = min(int(p[1]), vsize - 1)
                    self.send_response(206)
                    self.send_header("Content-Range", f"bytes {start}-{end}/{vsize}")
                else:
                    self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Length", str(end - start + 1))
                self.end_headers()
                with open(a.video, "rb") as fh:
                    fh.seek(start)
                    left = end - start + 1
                    while left > 0:
                        chunk = fh.read(min(262144, left))
                        if not chunk:
                            break
                        try:
                            self.wfile.write(chunk)
                        except (BrokenPipeError, ConnectionResetError):
                            return
                        left -= len(chunk)
                return
            body = page.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n) or b"{}")
            lay = build_layout(payload.get("cues", []), info["fps"], info["dur"])
            a.out.write_text(json.dumps(lay, indent=1))
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")
            moved = sum(1 for c, o in zip(payload.get("cues", []), cues)
                        if abs(float(c["y"]) - float(o["orig"])) > 0.001)
            print(f"  saved {a.out}  ({len(lay['segments'])} segments, {moved} moved)")
            done.set()

    srv = HTTPServer(("127.0.0.1", a.port), H)
    url = f"http://127.0.0.1:{a.port}/"
    print(f"  open {url}   (Save & close writes {a.out})")
    if not a.no_open:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        done.wait()
    except KeyboardInterrupt:
        print("\n  cancelled — nothing written")
        return 130
    srv.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Assemble hook + body per variant, two-pass loudnorm to -14 LUFS, re-transcribe for captions."""
import shutil, sys, json, pathlib, subprocess, re, os
P = pathlib.Path(os.environ.get("PROJECT") or sys.exit("Set PROJECT=/path/to/ad-project (with 03_selects/, 04_project-files/)"))
SEL = P/"03_selects"
WK = P/"04_project-files"/os.environ.get("WORK_DIR", "work"); WK.mkdir(exist_ok=True)
BODY = os.environ.get("BODY_SELECT", "BODY_take2.mov")
FF = shutil.which("ffmpeg") or os.path.expanduser("~/.local/bin/ffmpeg")
KEY = [l.split("=",1)[1].strip() for l in open(pathlib.Path(__file__).resolve().parents[2] / "plugins/vibe-editing/config/keys.env") if l.startswith("GROQ_API_KEY=")][0]
VARIANTS = json.loads(os.environ.get("VARIANTS", '{"PAIDMYSELF":"V05A_hook", "JOBWITHALEASE":"V05B_hook", "40KZERO":"V05C_hook"}'))  # export name → hook select

def run(cmd): return subprocess.run(cmd, capture_output=True, text=True)
def dur(f): return float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(f)]).stdout)

for name, hook in VARIANTS.items():
    asm, norm = WK/f"{name}_asm.mov", WK/f"{name}_norm.mov"
    r = run([FF,"-y","-hide_banner","-loglevel","error","-i",str(SEL/f"{hook}.mov"),"-i",str(SEL/BODY),
             "-filter_complex","[0:v]setsar=1,fps=30,format=yuv420p[v0];[1:v]setsar=1,fps=30,format=yuv420p[v1];[0:a]aresample=48000,aformat=channel_layouts=stereo[a0];[1:a]aresample=48000,aformat=channel_layouts=stereo[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]","-map","[v]","-map","[a]",
             "-c:v","libx264","-crf","14","-preset","fast","-pix_fmt","yuv420p","-r","30",
             "-c:a","pcm_s16le","-ar","48000",str(asm)])
    if r.returncode: sys.exit(f"concat failed {name}: {r.stderr[-400:]}")
    m = run([FF,"-hide_banner","-i",str(asm),"-af","loudnorm=I=-14:TP=-1:LRA=11:print_format=json","-f","null","-"]).stderr
    j = json.loads(m[m.rfind("{"):m.rfind("}")+1])
    af = (f"loudnorm=I=-14:TP=-1:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    r = run([FF,"-y","-hide_banner","-loglevel","error","-i",str(asm),"-c:v","copy","-af",af,
             "-c:a","pcm_s16le","-ar","48000",str(norm)])
    if r.returncode: sys.exit(f"loudnorm failed {name}: {r.stderr[-400:]}")
    mp3 = WK/f"{name}.mp3"
    run([FF,"-y","-hide_banner","-loglevel","error","-i",str(norm),"-vn","-ac","1","-ar","16000","-c:a","libmp3lame","-b:a","64k",str(mp3)])
    tx = WK/f"{name}_tx.json"
    code = run(["curl","-s","https://api.groq.com/openai/v1/audio/transcriptions","-H",f"Authorization: Bearer {KEY}",
                "-F",f"file=@{mp3}","-F","model=whisper-large-v3","-F","response_format=verbose_json",
                "-F","timestamp_granularities[]=word","-o",str(tx),"-w","%{http_code}"]).stdout
    print(f"{name:<14} {dur(norm):5.2f}s  input {float(j['input_i']):6.2f} LUFS -> -14  groq {code}", flush=True)
print("ASSEMBLED")

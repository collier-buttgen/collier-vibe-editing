import json,os,re,sys
import pathlib as _pl, shutil as _sh
KIT = _pl.Path(__file__).resolve().parents[2]                       # repo root (recipes/<name>/<script>.py)
FF = _sh.which('ffmpeg') or str(_pl.Path.home() / '.local/bin/ffmpeg')
FD = str(KIT / 'plugins/vibe-editing/skills/caption-clips/fonts/_all') + '/'
KEYS = KIT / 'plugins/vibe-editing/config/keys.env'
P = os.environ.get('PROJECT') or sys.exit('Set PROJECT=/path/to/project (with source.mp4, tx/, work/) — see README.md')
W=[w for w in json.load(open(P+'/tx/ws.json'))['words']]
lab=json.load(open(P+'/work/layout.json'))['lab']
n=lambda s:re.sub(r"[^a-z0-9']","",s.lower())
def find(t,phrase,first=True):
    ph=[n(x) for x in phrase.split()]; best=None
    for i in range(len(W)-len(ph)):
        if abs(W[i]['start']-t)>12: continue
        if [n(W[i+j]['word']) for j in range(len(ph))]==ph:
            if best is None or abs(W[i]['start']-t)<abs(W[best]['start']-t): best=i
    if best is None: sys.exit(f"NOT FOUND: '{phrase}' near {t}")
    return best if first else best+len(ph)-1
spec=json.load(open(P+'/scripts/clips.json')); out={}
for name,c in spec.items():
    parts=[];txt=[];tot=0
    for (ts,sp,te,ep) in c['parts']:
        a=find(ts,sp); b=find(te,ep,False)
        s,e=W[a]['start'],W[b]['end']; parts.append([round(s,3),round(e,3),a,b]); tot+=e-s
        txt.append(' '.join(w['word'] for w in W[a:b+1]))
        L=lab[int(s):int(e)+1]
        bad=sum(ch not in ('C' if c['kind']=='face' else 'S') for ch in L)
        if bad: txt[-1]+=f"   <<LAYOUT {L}>>"
    out[name]=dict(kind=c['kind'],parts=parts)
    print(f"\n## {name} [{c['kind']}] {tot:.1f}s"); [print('  ·',t) for t in txt]
json.dump(out,open(P+'/work/resolved.json','w'),indent=1)

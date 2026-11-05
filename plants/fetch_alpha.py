import json, os, subprocess, glob
UA = 'jv-texture-fetch/1.0'
for d in sorted(glob.glob('/home/claude/jv5/plants/src/*/')):
    pid = os.path.basename(d.rstrip('/'))
    files = json.loads(subprocess.run(['curl', '-s', '-f', '-A', UA, f'https://api.polyhaven.com/files/{pid}'], capture_output=True).stdout)
    got = []
    for k, v in files.items():
        if not any(w in k.lower() for w in ('alpha', 'opacity', 'mask')): continue
        res = v.get('1k') or v.get('2k')
        fmt = res.get('png') or res.get('jpg')
        out = f'{d}/textures/{os.path.basename(fmt["url"])}'
        if not os.path.exists(out):
            subprocess.run(['curl', '-s', '-f', '-L', '-A', UA, '-o', out, fmt['url']], check=True)
        got.append(os.path.basename(out))
    print(pid, got, flush=True)

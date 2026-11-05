import sys; sys.path.insert(0,'.')
import bpy, kit, math
import numpy as np
kit.reset()
s,so=kit.sky(sun_elev=8, sun_az=90)
sc=bpy.context.scene; sc.cycles.samples=8; sc.cycles.use_denoising=False
res={}
for nm,az in [('N',0),('E',90),('S',180),('W',270)]:
    a=math.radians(az)
    c=kit.camera('c'+nm,(0,0,1.6),(math.sin(a)*10,math.cos(a)*10,2.6),lens=20)
    p=f'/tmp/sky_{nm}.png'; kit.render(p,c,(48,32),8)
    img=bpy.data.images.load(p); px=np.array(img.pixels[:]).reshape(-1,4)[:,:3].mean()
    res[nm]=round(float(px),3)
print('SKY rotation 90 brightness by view dir:',res)

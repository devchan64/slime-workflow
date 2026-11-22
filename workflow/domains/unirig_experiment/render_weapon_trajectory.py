"""Overlay the sampled sword tip path on a diagnostic body pose."""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from workflow.domains.unirig_experiment.render_combat import raster,zup


def main(directory):
    d=np.load(directory/'frames.npz',allow_pickle=False)
    qa=json.loads((directory/'combat-welded-check.json').read_text())
    body=zup(d['positions']);weapon=zup(d['weapon_vertices']);tip=zup(d['tip']);bf=d['faces']
    wf=[]
    for q in d['weapon_faces']:wf.extend([[q[0],q[1],q[2]],[q[0],q[2],q[3]]])
    wf=np.asarray(wf,dtype=np.int32)+body.shape[1];faces=np.concatenate((bf,wf))
    ptsall=np.concatenate((body.reshape(-1,3),weapon.reshape(-1,3)));center=(ptsall.min(0)+ptsall.max(0))/2
    scale=430/max(np.ptp(ptsall,axis=0));frame=97
    verts=np.concatenate((body[frame],weapon[frame]))-center
    colors=np.concatenate((np.full((len(bf),3),[190,190,190],np.uint8),np.full((len(wf),3),[75,78,85],np.uint8)))
    sheet=Image.new('RGB',(1024,512))
    for col,(label,angle) in enumerate((('front',0),('side',np.pi/2))):
        right=np.array([np.cos(angle),np.sin(angle),0]);depth=np.array([-np.sin(angle),np.cos(angle),0])
        def project(x):
            a=np.stack((x@right,x[:,2]),axis=1)*scale+[256,256];a[:,1]=512-a[:,1];return a
        image=Image.fromarray(raster(project(verts),verts@depth,faces,colors));draw=ImageDraw.Draw(image)
        points=project(tip-center)
        for i in range(len(points)-1):
            u=i/max(1,len(points)-1);color=(int(30+205*u),80,int(225-195*u))
            draw.line((tuple(points[i]),tuple(points[i+1])),fill=color,width=2)
        for f in qa['blade_selected_frames']:
            x,y=points[f-1];draw.ellipse((x-4,y-4,x+4,y+4),fill=(255,0,0))
        draw.text((8,8),f'{label}: blue=start, orange=end; red=blade candidate',fill=(0,0,0))
        draw.text((8,26),'body pose shown: frame 98 / 132',fill=(0,0,0))
        sheet.paste(image,(col*512,0))
    sheet.save(directory/'weapon-trajectory.png')


if __name__=='__main__':main(Path(sys.argv[1]))

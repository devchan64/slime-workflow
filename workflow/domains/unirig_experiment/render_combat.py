"""Render sampled diagnostic combat poses with a depth buffer."""
import sys
from pathlib import Path
import imageio.v2 as imageio
from numba import njit
import numpy as np
from PIL import Image, ImageDraw
import trimesh


@njit
def raster(points,depths,faces,colors):
    size=512
    image=np.full((size,size,3),240,np.uint8)
    z=np.full((size,size),-1e20,np.float64)
    for i in range(len(faces)):
        a,b,c=faces[i]
        x0,y0=points[a]; x1,y1=points[b]; x2,y2=points[c]
        area=(x1-x0)*(y2-y0)-(y1-y0)*(x2-x0)
        if abs(area)<0.001: continue
        xl=max(0,int(np.floor(min(x0,x1,x2)))); xh=min(size-1,int(np.ceil(max(x0,x1,x2))))
        yl=max(0,int(np.floor(min(y0,y1,y2)))); yh=min(size-1,int(np.ceil(max(y0,y1,y2))))
        for y in range(yl,yh+1):
            for x in range(xl,xh+1):
                u=((x1-x)*(y2-y)-(y1-y)*(x2-x))/area
                v=((x2-x)*(y0-y)-(y2-y)*(x0-x))/area
                w=1-u-v
                if u>=0 and v>=0 and w>=0:
                    d=u*depths[a]+v*depths[b]+w*depths[c]
                    if d>z[y,x]: z[y,x]=d; image[y,x]=colors[i]
    return image


def zup(points):
    return points[..., [0,2,1]]*np.array([1,1,-1],dtype=np.float32)


def main(directory):
    d=np.load(directory/'frames.npz',allow_pickle=False)
    fps=20 if (directory/'retarget.json').exists() else 24
    body=zup(d['positions']); weapon=zup(d['weapon_vertices']); tip=zup(d['tip'])
    bf=d['faces']; wf=[]
    for q in d['weapon_faces']:
        wf.extend([[q[0],q[1],q[2]],[q[0],q[2],q[3]]])
    wf=np.asarray(wf,dtype=np.int32)+body.shape[1]
    faces=np.concatenate((bf,wf)); colors=np.concatenate((d['colors'][:,:3],np.tile(np.array([[145,151,163]],dtype=np.uint8),(weapon.shape[1],1))))
    allpoints=np.concatenate((body.reshape(-1,3),weapon.reshape(-1,3)),axis=0)
    center=(allpoints.min(0)+allpoints.max(0))/2
    scale=430/max(np.ptp(allpoints,axis=0))
    frames=[]
    for i in range(len(body)):
        verts=np.concatenate((body[i],weapon[i]))-center
        mesh=trimesh.Trimesh(vertices=verts,faces=faces,process=False)
        shade=np.clip(.55+.45*np.abs(mesh.face_normals@np.array([.4,-.6,.69])),0,1)
        fc=(colors[faces].mean(axis=1)*shade[:,None]).clip(0,255).astype(np.uint8)
        panels=[]
        for angle in (0,np.pi/2):
            right=np.array([np.cos(angle),np.sin(angle),0]); depth=np.array([-np.sin(angle),np.cos(angle),0])
            pts=np.stack((verts@right,verts[:,2]),axis=1)*scale+[256,256]; pts[:,1]=512-pts[:,1]
            panels.append(raster(pts,verts@depth,faces,fc))
        img=Image.fromarray(np.concatenate(panels,axis=1)); draw=ImageDraw.Draw(img)
        draw.text((10,10),f'frame {i+1:03d}/{len(body)} - front',fill=(20,20,20));draw.text((522,10),'side',fill=(20,20,20))
        frames.append(np.asarray(img))
    with imageio.get_writer(str(directory/'combat-preview.mp4'),fps=fps,codec='libx264',quality=8,macro_block_size=None) as writer:
        for frame in frames: writer.append_data(frame)
    indices=np.linspace(0,len(frames)-1,5,dtype=int)
    images=[Image.fromarray(frames[i]) for i in indices]
    montage=Image.new('RGB',(1024,512*len(images)))
    for i,img in enumerate(images): montage.paste(img,(0,i*512))
    montage.save(directory/'combat-contact-sheet.png')


if __name__=='__main__': main(Path(sys.argv[1]))

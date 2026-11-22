"""Depth-buffer rasterization for TRELLIS experiment views."""
import numpy as np
from numba import njit


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

"""Render rig placement over the imported mesh and inspect dominant weights."""
import json
import os
import sys
from pathlib import Path
import bpy
import numpy as np
from PIL import Image,ImageDraw


def main(path,out):
    out.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
    arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    obj=next(o for o in bpy.context.scene.objects if o.type=='MESH' and len(o.vertex_groups))
    dg=bpy.context.evaluated_depsgraph_get(); evaluated=obj.evaluated_get(dg); m=evaluated.to_mesh()
    try:
        coords=np.empty((len(m.vertices),3),np.float32);m.vertices.foreach_get('co',coords.ravel())
        obj_world=np.array(obj.matrix_world,dtype=np.float64);v=coords@obj_world[:3,:3].T+obj_world[:3,3]
        m.calc_loop_triangles();faces=np.array([t.vertices[:] for t in m.loop_triangles],dtype=np.int32)
    finally:evaluated.to_mesh_clear()
    center=(v.min(0)+v.max(0))/2;span=np.ptp(v,axis=0);scale=440/max(span)
    w=np.array(arm.matrix_world,dtype=np.float64)
    bones={}
    for b in arm.data.bones:
        h=w[:3,:3]@np.asarray(b.head_local)+w[:3,3];t=w[:3,:3]@np.asarray(b.tail_local)+w[:3,3]
        bones[b.name]={'head':h.tolist(),'tail':t.tolist(),'parent':b.parent.name if b.parent else None}
    tracked=[f'bone_{i}' for i in (0,1,2,3,4,5,6,7,8,9,25,26,27,28,44,45,46,47,48,49,50,51)]
    indexes={g.index:g.name for g in obj.vertex_groups}; dominant=[]; influence={}
    for vertex in obj.data.vertices:
        vals=[(g.weight,indexes[g.group]) for g in vertex.groups if g.group in indexes]
        dominant.append(max(vals)[1] if vals else None)
    dominant=np.array(dominant,dtype=object)
    for name in tracked:
        if name not in bones:continue
        inds=np.flatnonzero(dominant==name)
        if not len(inds):
            influence[name]={'dominant_vertices':0};continue
        p=v[inds];h=np.asarray(bones[name]['head']);t=np.asarray(bones[name]['tail']);d=t-h
        u=np.clip(((p-h)@d)/max(d@d,1e-20),0,1);dist=np.linalg.norm(p-(h+u[:,None]*d),axis=1)
        influence[name]={'dominant_vertices':len(inds),'distance_to_bone_p95':float(np.percentile(dist,95)),
                         'distance_to_bone_max':float(dist.max()),'dominant_centroid':p.mean(axis=0).tolist()}
    panels=[]
    for label,angle in [('front',0),('side',np.pi/2)]:
        right=np.array([np.cos(angle),np.sin(angle),0]);toward=np.array([-np.sin(angle),np.cos(angle),0])
        pts=np.stack(((v-center)@right,(v-center)[:,2]),axis=1)*scale+[256,256];pts[:,1]=512-pts[:,1]
        image=Image.new('RGB',(512,512),(240,240,240));draw=ImageDraw.Draw(image)
        face_depth=(v@toward)[faces].mean(axis=1)
        for face in faces[np.argsort(face_depth)]:
            draw.polygon([tuple(map(float,pts[i])) for i in face],fill=(185,185,185),outline=(150,150,150))
        draw.text((8,8),label,fill=(0,0,0))
        def project(x):
            p=(np.asarray(x)-center);return (float(p@right*scale+256),float(512-(p[2]*scale+256)))
        for name in tracked:
            if name not in bones:continue
            a=project(bones[name]['head']);b=project(bones[name]['tail'])
            draw.line((a,b),fill=(215,25,25),width=3);draw.ellipse((a[0]-3,a[1]-3,a[0]+3,a[1]+3),fill=(20,60,240))
            draw.text((a[0]+3,a[1]+3),name.removeprefix('bone_'),fill=(0,0,0))
        panels.append(image)
    sheet=Image.new('RGB',(1024,512));sheet.paste(panels[0],(0,0));sheet.paste(panels[1],(512,0));sheet.save(out/'bone-overlay.png')
    report={'world_bounds':[v.min(0).tolist(),v.max(0).tolist()],'height_z':float(span[2]),'bones':bones,'dominant_weights':influence,
            'limitations':'Bone-distance metrics are diagnostic, not proof of leakage: bone influence can include neighbouring joints and descendant geometry. Overlays are projected in two views.'}
    (out/'bone-overlay.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'height_z':report['height_z'],'bones':len(bones),'dominant_weights':influence}),flush=True)


if __name__=='__main__':
    main(*(Path(x) for x in sys.argv[1:]));sys.stdout.flush();sys.stderr.flush();os._exit(0)

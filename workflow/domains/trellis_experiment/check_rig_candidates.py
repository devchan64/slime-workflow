"""Measure structure, silhouettes and approximate hand clearance of candidates."""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pymeshlab
from scipy.spatial import cKDTree
import trimesh
from workflow.domains.trellis_experiment.raster import raster


def silhouettes(mesh, center, scale):
    v=np.asarray(mesh.vertices,dtype=np.float64)-center
    f=np.asarray(mesh.faces,dtype=np.int32)
    colors=np.zeros((len(f),3),dtype=np.uint8)
    result=[]
    for i in range(8):
        angle=i*np.pi/4
        right=np.array([np.cos(angle),np.sin(angle),0.0])
        toward=np.array([-np.sin(angle),np.cos(angle),0.0])
        p=np.stack((v@right,v[:,2]),axis=1)*scale+[256,256]
        p[:,1]=512-p[:,1]
        result.append(raster(p,v@toward,f,colors)[:,:,0] < 128)
    return result


def examine(mesh):
    e=np.asarray(mesh.edges_sorted);_,count=np.unique(e,axis=0,return_counts=True)
    ms=pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(vertex_matrix=np.asarray(mesh.vertices,dtype=np.float64),
                               face_matrix=np.asarray(mesh.faces,dtype=np.int32)))
    ms.compute_selection_by_self_intersections_per_face()
    v=np.asarray(mesh.vertices)
    torso=v[(np.abs(v[:,0])<.13)&(v[:,2]>-.18)&(v[:,2]<.04)]
    if len(torso)<50: raise ValueError('torso region missing')
    gaps={}
    for side,sign in [('left',1),('right',-1)]:
        hand=v[(sign*v[:,0]>.235)&(v[:,2]>-.18)&(v[:,2]<.04)]
        if len(hand)<20: raise ValueError('hand region missing')
        gaps[side]={'hand_vertices':len(hand),'minimum_vertex_distance':float(cKDTree(torso).query(hand)[0].min())}
    return {'vertices':len(v),'triangles':len(mesh.faces),'components':len(mesh.split(only_watertight=False)),
            'watertight':bool(mesh.is_watertight),'winding_consistent':bool(mesh.is_winding_consistent),
            'boundary_edges':int((count==1).sum()),'nonmanifold_edges':int((count>2).sum()),
            'self_intersection_selected_faces':int(ms.current_mesh().face_selection_array().sum()),
            'hand_to_torso_vertex_clearance':gaps}


def main(source, color_source, directory):
    ref=trimesh.load(source,force='mesh',process=False)
    color_ref=trimesh.load(color_source,force='mesh',process=False)
    if len(color_ref.vertices)!=len(ref.vertices): raise ValueError('color reference mismatch')
    tree=cKDTree(np.asarray(color_ref.vertices))
    center=np.asarray(ref.bounds).mean(axis=0);scale=440/max(ref.extents)
    ref_sil=silhouettes(ref,center,scale)
    report={'source':str(source.resolve()),'candidates':[],
            'limitations':'Clearance uses hand and torso vertex subsets, not exact surface distances or all possible bridges. Silhouettes and self-intersection are sampled/tool-limited. These checks do not test skeleton placement, skin weights, grasp or joint deformation.'}
    for target in (20000,50000,100000):
        m=trimesh.load(directory/f'candidate-{target}.ply',force='mesh',process=False)
        if not np.isfinite(m.vertices).all() or not len(m.faces): raise ValueError('invalid candidate')
        d,idx=tree.query(np.asarray(m.vertices),workers=1)
        m.visual.vertex_colors=np.asarray(color_ref.visual.vertex_colors)[idx]
        m.export(directory/f'candidate-{target}.glb')
        sil=silhouettes(m,center,scale)
        iou=[float(np.count_nonzero(a&b)/max(1,np.count_nonzero(a|b))) for a,b in zip(ref_sil,sil)]
        row={'target_triangles':target,**examine(m),'silhouette_iou':iou,
             'color_nearest_distance_median':float(np.median(d)),
             'color_nearest_distance_p99':float(np.percentile(d,99)),
             'rigging_ready':False,'rigging_reason':'Actual skeleton, skinning and pose deformation not yet validated.'}
        report['candidates'].append(row)
        print(json.dumps(row),flush=True)
    (directory/'qa-report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__': main(*(Path(x) for x in sys.argv[1:]))

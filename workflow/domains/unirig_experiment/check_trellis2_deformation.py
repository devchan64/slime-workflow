"""Check rest and diagnostic pose geometry of one generated UniRig FBX."""
import json
import sys
from pathlib import Path
import numpy as np
import pymeshlab
import trimesh
from PIL import Image, ImageDraw
from workflow.domains.unirig_experiment.render_combat import raster


def main(directory):
    report=json.loads((directory/'deformation-report.json').read_text())
    probes=[];sheet=Image.new('RGB',(1024,2048),(240,240,240))
    for index,name in enumerate(('rest','arms','legs','fingers')):
        mesh=trimesh.load(directory/(name+'.ply'),force='mesh',process=False)
        edges=np.asarray(mesh.edges_sorted);_,counts=np.unique(edges,axis=0,return_counts=True)
        ms=pymeshlab.MeshSet(); ms.add_mesh(pymeshlab.Mesh(vertex_matrix=np.asarray(mesh.vertices,dtype=np.float64),
                                                           face_matrix=np.asarray(mesh.faces,dtype=np.int32)))
        ms.compute_selection_by_self_intersections_per_face()
        selected=int(ms.current_mesh().face_selection_array().sum())
        probes.append({'pose':name,'self_intersection_selected_faces':selected,'watertight':bool(mesh.is_watertight),
                       'boundary_edges':int((counts==1).sum()),'nonmanifold_edges':int((counts>2).sum()),
                       'winding_consistent':bool(mesh.is_winding_consistent)})
        v=np.asarray(mesh.vertices,dtype=np.float64);v=v-np.asarray(mesh.bounds).mean(axis=0)
        faces=np.asarray(mesh.faces,dtype=np.int32)
        shade=np.clip(.55+.45*np.abs(mesh.face_normals@np.array([.4,-.6,.69])),0,1)
        colors=(np.asarray(mesh.visual.vertex_colors)[:,:3][faces].mean(axis=1)*shade[:,None]).clip(0,255).astype(np.uint8)
        scale=440/max(mesh.extents)
        for col,angle in enumerate((0,np.pi/2)):
            right=np.array([np.cos(angle),np.sin(angle),0]);depth=np.array([-np.sin(angle),np.cos(angle),0])
            pts=np.stack((v@right,v[:,2]),axis=1)*scale+[256,256];pts[:,1]=512-pts[:,1]
            im=Image.fromarray(raster(pts,v@depth,faces,colors));ImageDraw.Draw(im).text((10,10),f'{name} {"front" if col==0 else "side"}',fill=(20,20,20))
            sheet.paste(im,(col*512,index*512))
    sheet.save(directory/'pose-comparison.png')
    fail_bones=[x['bone'] for x in report['bone_probes'] if not x.get('weighted_vertices_moved')]
    result={'bones':report['bones'],'unweighted_vertices':report['unweighted_vertices'],'failed_bone_probes':fail_bones,
            'pose_checks':probes,'rigging_approved':False,
            'limitations':'Named bone tests use heuristic mapping and fixed local rotations. Intersection selection is approximate and does not prove actual intersections or absence thereof; no BVH/combat/grasp validation.'}
    (directory/'pose-geometry-report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__': main(Path(sys.argv[1]))

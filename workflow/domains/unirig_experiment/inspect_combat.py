"""Geometry and blade collision probes for a sampled combat trial."""
import json
import sys
from pathlib import Path
import numpy as np
import pymeshlab
import trimesh


def selected(vertices, faces):
    ms=pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(vertex_matrix=np.asarray(vertices,dtype=np.float64),
                               face_matrix=np.asarray(faces,dtype=np.int32)))
    ms.compute_selection_by_self_intersections_per_face()
    return ms.current_mesh().face_selection_array().copy()


def main(directory, stride=1):
    data=np.load(directory/'frames.npz',allow_pickle=False)
    positions=data['positions']; faces=data['faces']; weapon=data['weapon_vertices']; quads=data['weapon_faces']
    if not len(positions) or stride<1 or not np.isfinite(positions).all() or not np.isfinite(weapon).all():
        raise ValueError('invalid animation samples')
    # The final six quads belong to the blade; handle/guard contact is excluded.
    blade_faces=[]
    for q in quads[12:]: blade_faces.extend([[q[0],q[1],q[2]],[q[0],q[2],q[3]]])
    blade_faces=np.asarray(blade_faces,dtype=np.int32)
    rows=[]
    sample_indices=sorted(set(range(0,len(positions),stride))|{len(positions)-1})
    for i in sample_indices:
        body=positions[i]
        if i==0:
            m=trimesh.Trimesh(vertices=body,faces=faces,process=False)
            topology={'watertight':bool(m.is_watertight),'winding_consistent':bool(m.is_winding_consistent)}
        sel=selected(body,faces)
        all_vertices=np.concatenate((body,weapon[i]),axis=0)
        all_faces=np.concatenate((faces,blade_faces+len(body)),axis=0)
        combined=selected(all_vertices,all_faces)
        rows.append({'frame':i+1,'self_intersection_faces_selected':int(sel.sum()),
                     'blade_faces_selected_in_combined_test':int(combined[len(faces):].sum())})
    grip=np.asarray(data['grip']); hand=np.asarray(data['hand']); tip=np.asarray(data['tip'])
    arm_movement=np.linalg.norm(positions-positions[0],axis=2)
    r={'frames':rows,'total_frames':len(positions),'sample_stride':stride,'sampled_frames':len(rows),
       'rest_topology_at_first_animated_frame':topology,
       'frames_with_body_intersection_candidates':sum(x['self_intersection_faces_selected']>0 for x in rows),
       'frames_with_blade_intersection_candidates':sum(x['blade_faces_selected_in_combined_test']>0 for x in rows),
       'max_vertex_displacement':float(arm_movement.max()),
       'grip_to_hand_tail_min':float(np.linalg.norm(grip-hand,axis=1).min()),
       'grip_to_hand_tail_max':float(np.linalg.norm(grip-hand,axis=1).max()),
       'weapon_tip_path_length':float(np.linalg.norm(np.diff(tip,axis=0),axis=1).sum()),
       'limitations':'MeshLab selection reports suspect faces, not intersection pairs; misses are possible. Blade test excludes hilt and guard; sampled frames do not prove absence of collisions between frames or a plausible grasp.'}
    (directory/'combat-geometry-check.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='frames'},ensure_ascii=False),flush=True)


if __name__=='__main__': main(Path(sys.argv[1]),int(sys.argv[2]) if len(sys.argv)>2 else 1)

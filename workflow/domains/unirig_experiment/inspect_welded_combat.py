"""Check all BVH frames after welding identical exported vertex trajectories."""
import json
import sys
from pathlib import Path
import numpy as np
import pymeshlab
import trimesh


def selected(vertices,faces):
    ms=pymeshlab.MeshSet();ms.add_mesh(pymeshlab.Mesh(vertex_matrix=np.asarray(vertices,dtype=np.float64),
                                                      face_matrix=np.asarray(faces,dtype=np.int32)))
    ms.compute_selection_by_self_intersections_per_face()
    return ms.current_mesh().face_selection_array().copy()


def main(directory):
    d=np.load(directory/'frames.npz',allow_pickle=False);p=d['positions'];f=d['faces'];w=d['weapon_vertices'];quads=d['weapon_faces']
    if len(p)!=132 or not np.isfinite(p).all() or not np.isfinite(w).all():raise ValueError('invalid animation')
    sig=np.round(p[[0,33,66,99,131]].transpose(1,0,2).reshape(p.shape[1],-1),6)
    _,idx,inverse=np.unique(sig,axis=0,return_index=True,return_inverse=True)
    faces=inverse[f];body=p[:,idx];max_weld_error=0.
    # Confirm the split vertices match for every sampled frame before welding.
    for frame in range(len(p)):
        max_weld_error=max(max_weld_error,float(np.linalg.norm(p[frame]-body[frame][inverse],axis=1).max()))
    if max_weld_error>2e-5:raise ValueError('split vertices diverge; cannot weld for validation')
    blade=[]
    for q in quads[12:]:blade.extend([[q[0],q[1],q[2]],[q[0],q[2],q[3]]])
    blade=np.asarray(blade,dtype=np.int32);rows=[]
    for i in range(len(p)):
        sel=selected(body[i],faces)
        allv=np.concatenate((body[i],w[i]));allf=np.concatenate((faces,blade+len(body[i])))
        cross=selected(allv,allf)
        rows.append({'frame':i+1,'body_selected_faces':int(sel.sum()),'blade_selected_faces':int(cross[len(faces):].sum())})
    first=trimesh.Trimesh(vertices=body[0],faces=faces,process=False)
    tip=np.asarray(d['tip']);grip=np.asarray(d['grip']);hand=np.asarray(d['hand'])
    step=np.linalg.norm(np.diff(tip,axis=0),axis=1)
    r={'total_frames':len(p),'source_vertices':p.shape[1],'welded_vertices':len(idx),'max_weld_error':max_weld_error,
       'first_frame_topology':{'watertight':bool(first.is_watertight),'winding_consistent':bool(first.is_winding_consistent)},
       'frames_with_body_selected':sum(x['body_selected_faces']>0 for x in rows),
       'frames_with_blade_selected':sum(x['blade_selected_faces']>0 for x in rows),
       'max_body_selected_faces':max(x['body_selected_faces'] for x in rows),
       'blade_selected_frames':[x['frame'] for x in rows if x['blade_selected_faces']>0],
       'weapon_tip_path_length':float(step.sum()),'weapon_tip_max_speed_per_sec':float(step.max()*20),
       'grip_to_hand_tail_min':float(np.linalg.norm(grip-hand,axis=1).min()),
       'grip_to_hand_tail_max':float(np.linalg.norm(grip-hand,axis=1).max()),'frames':rows,
       'limitations':'MeshLab selection identifies suspect faces, not exact intersection pairs and can miss collisions. Blade test excludes hilt and guard; no continuous collision test or grip validation. Coordinates are normalized Y-down rig space.'}
    (directory/'combat-welded-check.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='frames'}),flush=True)


if __name__=='__main__':main(Path(sys.argv[1]))

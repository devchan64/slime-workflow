"""Compare the retargeted skeleton with the input BVH without modifying either."""
import json
import os
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

from retarget_bvh_trial import MAPPING


def main(blend, bvh, output):
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    scene = bpy.context.scene
    target = scene.objects['Armature']
    bpy.ops.import_anim.bvh(filepath=str(bvh.resolve()), use_fps_scale=False, update_scene_fps=False)
    source = next(o for o in scene.objects if o.type == 'ARMATURE' and o != target)
    align = Matrix(((1,0,0),(0,0,-1),(0,1,0)))
    source_height = abs(source.data.bones['Hips'].head_local.z-source.data.bones['LeftFoot'].head_local.z)
    target_height = abs(target.data.bones['bone_0'].head_local.y-target.data.bones['bone_50'].head_local.y)
    scale = target_height/source_height
    records = []
    for frame in (1,34,67,100,132):
        scene.frame_set(frame); bpy.context.view_layer.update()
        sroot = source.pose.bones['Hips'].head
        troot = target.pose.bones['bone_0'].head
        for src,dst in MAPPING.items():
            s = align @ (source.pose.bones[src].head-sroot) * scale
            t = target.pose.bones[dst].head-troot
            records.append({'frame':frame, 'source_joint':src, 'target_bone':dst,
                            'source_relative':list(s), 'target_relative':list(t),
                            'distance':float((s-t).length)})
    lengths=[]
    for src,dst in MAPPING.items():
        a=source.data.bones[src]; b=target.data.bones[dst]
        sl=(a.tail_local-a.head_local).length*scale; tl=(b.tail_local-b.head_local).length
        lengths.append({'source_joint':src,'target_bone':dst,'source_length_scaled':sl,
                        'target_length':tl,'target_over_source':tl/sl if sl>1e-5 else None})
    output.write_text(json.dumps({'scale':scale,'joint_positions':records,'bone_lengths':lengths,
                                  'limitations':'Pelvis aligned only; proportions and joint conventions differ; distances are diagnostic, not ground-truth anatomical errors.'},indent=2)+'\n')
    print(json.dumps({'max_distance':max(x['distance'] for x in records),
                      'median_distance':float(np.median([x['distance'] for x in records])),
                      'max_cases':sorted(records,key=lambda x:x['distance'],reverse=True)[:5]}),flush=True)


if __name__ == '__main__':
    main(*(Path(x) for x in sys.argv[1:]))
    sys.stdout.flush(); sys.stderr.flush(); os._exit(0)

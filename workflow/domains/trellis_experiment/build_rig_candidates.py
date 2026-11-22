"""Create shape-only remeshed candidates; retain the source and keep failures visible."""
import json
import os
import sys
from pathlib import Path

import bpy


def main(source, output):
    if output.exists(): raise FileExistsError(output)
    output.mkdir(parents=True)
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    bpy.ops.wm.ply_import(filepath=str(source.resolve()))
    obj=bpy.context.active_object
    if obj is None or obj.type!='MESH' or len(obj.data.polygons)==0:
        raise ValueError('missing mesh')
    obj.name='character_shape'
    original_faces=len(obj.data.polygons)
    obj.data.remesh_voxel_size=0.004
    bpy.ops.object.voxel_remesh()
    remesh_faces=len(obj.data.polygons)
    # Approximate hands on this normalized A-pose source. Only the outer hand
    # regions are smoothed; the independent checks determine if they survived.
    group=obj.vertex_groups.new(name='hand_simplification')
    selected=[v.index for v in obj.data.vertices if abs(v.co.x)>=.235 and -.18<=v.co.z<=.04]
    if len(selected)<100: raise ValueError('hand region could not be located')
    group.add(selected,1.0,'REPLACE')
    bpy.context.view_layer.objects.active=obj
    smooth=obj.modifiers.new('simplify_hand_detail','SMOOTH')
    smooth.vertex_group=group.name; smooth.factor=.5; smooth.iterations=3
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    mesh_base=obj.data.copy()
    mesh_base.calc_loop_triangles()
    base_triangles=len(mesh_base.loop_triangles)
    results=[]
    for target in (20000,50000,100000):
        obj.data=mesh_base.copy()
        modifier=obj.modifiers.new('reduce_triangles','DECIMATE')
        modifier.decimate_type='COLLAPSE'; modifier.ratio=min(1.0,target/max(1,base_triangles))
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        bpy.ops.wm.ply_export(filepath=str((output/f'candidate-{target}.ply').resolve()), export_selected_objects=True,
                              export_triangulated_mesh=True, export_attributes=False)
        obj.data.calc_loop_triangles()
        results.append({'target_triangles':target,'triangles':len(obj.data.loop_triangles),'vertices':len(obj.data.vertices)})
    report={'original_faces':original_faces,'voxel_size':.004,'voxel_remesh_faces':remesh_faces,'base_triangles':base_triangles,
            'hand_vertex_count':len(selected),'hand_region':'abs(x)>=0.235 and -0.18<=z<=0.04',
            'hand_smoothing_iterations':3,'hand_smoothing_factor':.5,'candidates':results,
            'limitations':'Hand region is calibrated only for this normalized A-pose; voxel remesh and smoothing can merge or remove fingers, limbs and thin parts. Remesh does not ensure riggability.'}
    (output/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    main(*(Path(x) for x in sys.argv[1:]))
    sys.stdout.flush();sys.stderr.flush();os._exit(0)

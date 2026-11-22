"""Make a triangle-limited mesh from an already repaired Z-up PLY."""
import json
import os
import sys
from pathlib import Path
import bpy


def main(source, output, target):
    if output.exists(): raise FileExistsError(output)
    output.mkdir(parents=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.wm.ply_import(filepath=str(source.resolve()))
    obj=bpy.context.active_object
    if not obj or obj.type!='MESH': raise ValueError('missing input mesh')
    obj.data.calc_loop_triangles(); before=len(obj.data.loop_triangles)
    modifier=obj.modifiers.new('reduce_triangles','DECIMATE')
    modifier.decimate_type='COLLAPSE';modifier.ratio=min(1.0,target/before)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.data.calc_loop_triangles();actual=len(obj.data.loop_triangles)
    if actual>target: raise ValueError('triangle target exceeded')
    bpy.ops.wm.ply_export(filepath=str((output/'candidate.ply').resolve()),export_selected_objects=True,
                          export_triangulated_mesh=True,export_attributes=False)
    (output/'build-report.json').write_text(json.dumps({'source':str(source.resolve()),'source_triangles':before,
        'target_triangles':target,'actual_triangles':actual,'vertices':len(obj.data.vertices)},indent=2)+'\n')
    print(json.dumps({'source_triangles':before,'triangles':actual,'vertices':len(obj.data.vertices)}),flush=True)


if __name__=='__main__':
    main(Path(sys.argv[1]),Path(sys.argv[2]),int(sys.argv[3]))
    sys.stdout.flush();sys.stderr.flush();os._exit(0)

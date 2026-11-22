"""Inspect an experimental UniRig FBX and generate isolated deformation probes."""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
import trimesh
from scipy.spatial import cKDTree


def positions(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        result = np.empty((len(mesh.vertices),3),dtype=np.float32)
        mesh.vertices.foreach_get('co',result.ravel())
        return result
    finally:
        evaluated.to_mesh_clear()


def main(fbx, source, output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(fbx.resolve()))
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and len(o.vertex_groups)]
    arms = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
    if len(meshes)!=1 or len(arms)!=1:
        raise ValueError('unexpected skinned asset structure')
    obj, arm = meshes[0], arms[0]
    if not any(m.type=='ARMATURE' and m.object==arm for m in obj.modifiers):
        raise ValueError('missing armature modifier')
    # The exporter uses normalized Y-down character coordinates.  Map the
    # source's Z-up coordinates by the experimentally observed axis transform.
    original = trimesh.load(source,force='mesh',process=False)
    center = np.asarray(original.bounds).mean(axis=0)
    transformed = (np.asarray(original.vertices)-center)*(2/max(original.extents))
    transformed = transformed[:,[0,2,1]]*np.array([1,-1,1])
    raw = np.array([v.co[:] for v in obj.data.vertices],dtype=np.float32)
    distances, near = cKDTree(transformed).query(raw,workers=1)
    colors = np.asarray(original.visual.vertex_colors)[near,:3].astype(np.float32)/255
    linear = np.where(colors<=0.04045,colors/12.92,((colors+0.055)/1.055)**2.4)
    attr = obj.data.color_attributes.new(name='ReferenceColor',type='FLOAT_COLOR',domain='POINT')
    rgba=np.column_stack((linear,np.ones(len(linear),dtype=np.float32))).astype(np.float32)
    attr.data.foreach_set('color',rgba.ravel())
    material=bpy.data.materials.new('Reference vertex colors'); material.use_nodes=True
    nodes=material.node_tree.nodes
    vertex=nodes.new('ShaderNodeVertexColor'); vertex.layer_name='ReferenceColor'
    material.node_tree.links.new(vertex.outputs['Color'],nodes.get('Principled BSDF').inputs['Base Color'])
    obj.data.materials.clear(); obj.data.materials.append(material)
    deps=bpy.context.evaluated_depsgraph_get()
    baseline=positions(obj,deps)
    if not np.isfinite(baseline).all():
        raise ValueError('nonfinite baseline')
    groups={g.name:g.index for g in obj.vertex_groups}
    sum_weights=np.array([sum(g.weight for g in v.groups) for v in obj.data.vertices])
    selected = [f'bone_{i}' for i in list(range(10,25))+list(range(29,44))]
    joints=['bone_7','bone_8','bone_26','bone_27','bone_44','bone_45','bone_48','bone_49']
    tests=[]
    for name in joints+selected:
        if name not in arm.pose.bones or name not in groups:
            tests.append({'bone':name,'status':'missing'}); continue
        bone=arm.pose.bones[name]; bone.rotation_mode='XYZ'; bone.rotation_euler.x=math.radians(25)
        bpy.context.view_layer.update(); posed=positions(obj,deps)
        delta=np.linalg.norm(posed-baseline,axis=1)
        index=groups[name]
        weights=np.array([next((g.weight for g in v.groups if g.group==index),0.0) for v in obj.data.vertices])
        strong=weights>=0.05
        tests.append({'bone':name,'weighted_vertices_ge_005':int(strong.sum()),
                      'weighted_vertices_moved':int(((delta>1e-4)&strong).sum()),
                      'moved_vertices':int((delta>1e-4).sum()),'max_displacement':float(delta.max()),
                      'finite':bool(np.isfinite(posed).all())})
        bone.rotation_euler.x=0; bpy.context.view_layer.update()
    # Export selected mesh and armature only; discard Blender's default scene cube.
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); arm.select_set(True)
    bpy.context.view_layer.objects.active=arm
    bpy.ops.export_scene.gltf(filepath=str((output/'rigged.glb').resolve()),export_format='GLB',
                              use_selection=True,export_skins=True,export_animations=False)
    # Fixed joint probes are diagnostic only, not anatomically authored poses.
    for label, rotations in [
        ('rest',{}),
        ('arms',{'bone_7':35,'bone_8':40,'bone_26':-35,'bone_27':-40}),
        ('fingers',{name:20 for name in selected}),
        ('legs',{'bone_44':25,'bone_45':35,'bone_48':-25,'bone_49':-35}),
    ]:
        for name,angle in rotations.items():
            bone=arm.pose.bones[name]; bone.rotation_mode='XYZ'; bone.rotation_euler.x=math.radians(angle)
        bpy.context.view_layer.update(); pos=positions(obj,deps)
        # Return to Z-up for the existing renderer.
        pos=pos[:,[0,2,1]]*np.array([1,1,-1],dtype=np.float32)
        obj.data.calc_loop_triangles()
        faces=np.array([t.vertices[:] for t in obj.data.loop_triangles],dtype=np.int32)
        mesh=trimesh.Trimesh(vertices=pos,faces=faces,process=False)
        mesh.visual.vertex_colors=np.column_stack(((colors*255).clip(0,255).astype(np.uint8),np.full(len(colors),255,np.uint8)))
        mesh.export(output/(label+'.ply'))
        for name in rotations: arm.pose.bones[name].rotation_euler.x=0
        bpy.context.view_layer.update()
    report={'vertices':len(baseline),'faces':len(obj.data.polygons),'bones':len(arm.data.bones),
            'weight_sum_min':float(sum_weights.min()),'weight_sum_max':float(sum_weights.max()),
            'unweighted_vertices':int((sum_weights<1e-6).sum()),
            'color_mapping_median_distance_normalized':float(np.median(distances)),
            'color_mapping_p95_distance_normalized':float(np.percentile(distances,95)),
            'bone_probes':tests,'limitations':'Numbered bones and test rotations are heuristic; nonzero motion does not prove anatomical correctness, full collision absence or combat suitability. Color transfer is approximate.'}
    (output/'deformation-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'vertices':report['vertices'],'faces':report['faces'],'bones':report['bones'],
                      'unweighted_vertices':report['unweighted_vertices'],'failed_bone_probes':sum(t.get('weighted_vertices_moved',0)==0 for t in tests)}),flush=True)


if __name__=='__main__':
    main(*(Path(x) for x in sys.argv[1:]))

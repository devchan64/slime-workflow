"""고정 ANNY 리타게팅·렌더 단계만 별도 Blender 프로세스에서 실행한다."""
import json
from pathlib import Path
import runpy
import sys

CURRENT_WORKSPACE_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(CURRENT_WORKSPACE_ROOT))
current_stage_record=json.loads(Path(sys.argv[2]).read_text())
current_stage_name=sys.argv[3]
current_retarget_root=Path(current_stage_record['output_directory'])
if current_stage_name=='retarget':
    sys.path.insert(0,str(CURRENT_WORKSPACE_ROOT/'generators/momask'))
    current_stage_namespace=runpy.run_path(str(CURRENT_WORKSPACE_ROOT/'generators/momask/templates/retarget_loop.py'),init_globals={'retarget_output_directory':current_retarget_root},run_name='__main__')
    from generators.kimodo.anny_rotation import apply_neck_rotation_channels
    apply_neck_rotation_channels(current_retarget_root,current_stage_namespace)
elif current_stage_name=='render':
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(current_retarget_root/'mannequin.blend'))
    runpy.run_path(str(CURRENT_WORKSPACE_ROOT/'generators/hy_motion/templates/vnccs_render.py'),init_globals={'export_stage_request':current_stage_record,'prepared_body_object':bpy.data.objects['AnnyAttributesBody']},run_name='__main__')
else:
    raise ValueError('지원하지 않는 Kimodo ANNY 단계')

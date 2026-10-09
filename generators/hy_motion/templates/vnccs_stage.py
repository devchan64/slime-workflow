"""별도 Blender 프로세스의 고정 단계 진입점. 임의 스크립트를 실행하지 않는다."""
from pathlib import Path
import json
import runpy
import sys
CURRENT_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(CURRENT_REPOSITORY_ROOT))
current_stage_request = json.loads(Path(sys.argv[2]).read_text())
current_stage_name = sys.argv[3]
current_output_directory = Path(current_stage_request['output_directory'])
current_source_directory = Path(current_stage_request['source_directory'])
if current_stage_name == 'position':
    sys.path.insert(0, str(CURRENT_REPOSITORY_ROOT / 'generators/momask'))
    runpy.run_path(str(CURRENT_REPOSITORY_ROOT / 'generators/momask/templates/retarget_loop.py'), init_globals={'retarget_output_directory': current_output_directory}, run_name='__main__')
elif current_stage_name in ('arms', 'rotation'):
    current_template_name = 'arm_transfer.py' if current_stage_name == 'arms' else 'local_rotation_transfer.py'
    current_stage_directory = current_output_directory / current_stage_name
    current_stage_directory.mkdir()
    runpy.run_path(str(Path(__file__).parent / current_template_name), init_globals={'stage_output_directory': current_stage_directory, 'source_job_directory': current_source_directory}, run_name='__main__')
elif current_stage_name == 'skin':
    from generators.hy_motion.anny_skin_stage import apply_anny_skin_barrier
    apply_anny_skin_barrier(current_output_directory / 'rotation/full_rotation/mannequin.blend', current_output_directory / 'final', source_motion_path=current_source_directory / 'motion.npz', skin_profile_path=Path(current_stage_request['skin_profile_path']))
elif current_stage_name == 'render':
    runpy.run_path(str(Path(__file__).parent / 'vnccs_render.py'), init_globals={'export_stage_request': current_stage_request}, run_name='__main__')
else:
    raise ValueError('지원하지 않는 ANNY 출력 단계')

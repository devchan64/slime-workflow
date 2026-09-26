"""저장된 리그·렌더 설정으로 중단된 MoMask ANNY 렌더를 재개한다."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys
import numpy as np
from PIL import Image

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.generation_records import write_record_atomically

def resume_render_frames(generation_job_path):
    request_record_value=json.loads((generation_job_path/'request.json').read_text())
    render_output_path=generation_job_path/'result/anny'
    frame_count_value=len(np.load(generation_job_path/'motion-run/motion/motion.npz')['joints'])
    valid_render_paths=[]
    for direction_name_value in request_record_value['directions']:
        for frame_number_value in range(1,frame_count_value+1):
            image_output_path=render_output_path/direction_name_value/f'preview-{frame_number_value:04d}.png'
            if not image_output_path.exists():continue
            try:
                with Image.open(image_output_path) as image_content_value:image_content_value.verify()
            except (OSError,SyntaxError):continue
            valid_render_paths.append(str(image_output_path))
    render_script_value=(render_output_path/'render_asset.py').read_text()
    render_call_value='  bpy.ops.render.render(write_still=True)'
    if render_script_value.count(render_call_value)!=1:raise ValueError('저장된 렌더 스크립트가 재개 계약과 다릅니다.')
    render_script_value=render_script_value.replace('.mkdir()', '.mkdir(exist_ok=True)')
    render_script_value=render_script_value.replace(render_call_value,'  if scene_render_value.render.filepath not in RESUME_VALID_IMAGE_PATHS:\n '+render_call_value)
    render_script_value='RESUME_VALID_IMAGE_PATHS=set('+repr(valid_render_paths)+')\n'+render_script_value
    resume_script_path=render_output_path/'resume_render_asset.py'
    resume_script_path.write_text(render_script_value)
    print(f'재개: 완료 PNG {len(valid_render_paths)}장 재사용 / 총 {frame_count_value*len(request_record_value["directions"])}장',flush=True)
    subprocess.run([str(WORKFLOW_ROOT_DIRECTORY/'.local/blender-runtime/bin/python'),str(render_output_path/'run_stage.py'),str(resume_script_path)],cwd=render_output_path,check=True)
    for direction_name_value in request_record_value['directions']:
        frame_directory_path=render_output_path/direction_name_value/'frames';frame_directory_path.mkdir(exist_ok=True)
        for frame_number_value in range(1,frame_count_value+1):
            image_output_path=render_output_path/direction_name_value/f'preview-{frame_number_value:04d}.png'
            with Image.open(image_output_path) as image_content_value:image_content_value.verify()
            shutil.copy2(image_output_path,frame_directory_path/f'anny-{frame_number_value:04d}.png')
    baseline_record_value=json.loads((render_output_path/'baseline-model.json').read_text())
    result_record_value={'action':request_record_value['action'],'label':{'standing':'대기','deep_breath':'심호흡','stretch':'스트레칭','walking':'걷기'}[request_record_value['action']],'frames':frame_count_value,'anny_frames':frame_count_value,'fps':4,'directions':request_record_value['directions'],'prompt':(generation_job_path/'motion-run/prompt.txt').read_text().strip(),'sampling':'none','hand_pose':'fist-v3','arm_retarget':'parallel-transport-v3','skinning':'dual-quaternion-corrective-v1','baseline_model':baseline_record_value,'status':'completed','resumed':True}
    write_record_atomically(render_output_path/'result.json',{**result_record_value,'arm_corrections':json.loads((render_output_path/'arm-corrections.json').read_text())})
    write_record_atomically(generation_job_path/'result.json',result_record_value)
    from tools.review.domains.momask.openpose_maps import generate_openpose_maps
    generate_openpose_maps(generation_job_path,request_record_value.get('face',False))

if __name__=='__main__':
    argument_parser_value=argparse.ArgumentParser();argument_parser_value.add_argument('--job-dir',type=Path,required=True)
    resume_render_frames(argument_parser_value.parse_args().job_dir)

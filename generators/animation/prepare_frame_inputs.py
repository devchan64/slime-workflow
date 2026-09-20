"""검수한 외형·MoMask 포즈·프롬프트를 새 실험 폴더에 준비한다."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import hashlib
import json
import shutil
import traceback
from PIL import Image

WORKFLOW_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_SIZE = (512, 512)


def prepare_frame_inputs():
    argument_value_parser=argparse.ArgumentParser(description=__doc__)
    argument_value_parser.add_argument('--appearance',type=Path,required=True)
    argument_value_parser.add_argument('--pose',type=Path,required=True)
    argument_value_parser.add_argument('--prompt-file',type=Path,required=True)
    argument_value_parser.add_argument('--output-dir',type=Path,default=WORKFLOW_REPO_ROOT/'.tmp'/datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S'))
    parsed_argument_values=argument_value_parser.parse_args()
    output_trial_root=parsed_argument_values.output_dir.resolve()
    if not output_trial_root.is_relative_to(WORKFLOW_REPO_ROOT/'.tmp'):
        raise ValueError('후보 에셋은 저장소 .tmp 하위에서만 준비합니다.')
    output_trial_root.mkdir(parents=True,exist_ok=False)
    try:
        appearance_image_value=Image.open(parsed_argument_values.appearance).convert('RGBA')
        appearance_image_value.thumbnail(DEFAULT_OUTPUT_SIZE,Image.Resampling.LANCZOS)
        appearance_canvas_image=Image.new('RGB',DEFAULT_OUTPUT_SIZE,'white')
        appearance_canvas_image.paste(appearance_image_value,((512-appearance_image_value.width)//2,(512-appearance_image_value.height)//2),appearance_image_value)
        pose_image_value=Image.open(parsed_argument_values.pose).convert('RGB')
        if pose_image_value.size!=DEFAULT_OUTPUT_SIZE: raise ValueError('MoMask 투영 포즈 맵은 512×512여야 합니다.')
        if not parsed_argument_values.prompt_file.read_text().strip(): raise ValueError('프롬프트가 비었습니다.')
        appearance_canvas_image.save(output_trial_root/'standing-reference.png')
        pose_image_value.save(output_trial_root/'openpose-reference.png')
        shutil.copy2(parsed_argument_values.prompt_file,output_trial_root/'prompt.txt')
        input_source_records={source_role_name:{'path':str(source_file_path.resolve()),'sha256':hashlib.sha256(source_file_path.read_bytes()).hexdigest()} for source_role_name,source_file_path in [('appearance',parsed_argument_values.appearance),('pose',parsed_argument_values.pose),('prompt',parsed_argument_values.prompt_file)]}
        (output_trial_root/'inputs.json').write_text(json.dumps(input_source_records,ensure_ascii=False,indent=2)+'\n')
        trace_message_value=f'{datetime.now().isoformat()}/frame-inputs/complete {output_trial_root}\n'
    except Exception:
        trace_message_value=f'{datetime.now().isoformat()}/frame-inputs/failure {traceback.format_exc()}\n'
        (output_trial_root/'prepare.log').write_text(trace_message_value)
        print(trace_message_value,flush=True)
        raise
    (output_trial_root/'prepare.log').write_text(trace_message_value)
    print(trace_message_value,flush=True)

if __name__=='__main__': prepare_frame_inputs()

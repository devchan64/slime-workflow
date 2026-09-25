"""승인 모션의 OpenPose 프레임을 4fps 게임용 시트로 무손실 배치한다."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import hashlib
import json
import math
import yaml
from PIL import Image

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[2]
POSE_SHEET_COLUMNS=4
POSE_SHEET_MAX_FRAMES=32
POSE_FRAME_CELL_SIZE=512
POSE_DIRECTION_NAMES=('down_left','down_right','up_left','up_right')
POSE_SOURCE_RECORDS=(('standing-v3','momask-standing-v3',16,'openpose','manifest.yaml'),('walking-v8','mannequin-walk-v8',32,'','artifact.json'),('stretch-v1','momask-stretch-v1',120,'openpose','manifest.yaml'))


def calculate_asset_digest(asset_file_path):
    return hashlib.sha256(asset_file_path.read_bytes()).hexdigest()


def build_game_pose_sheets(output_asset_directory):
    output_asset_directory.mkdir(parents=True,exist_ok=False)
    output_manifest_record={'schema_version':1,'asset_id':'game-motion-pose-sheets','version':1,'fps':4,'frame_duration_ms':250,'format':'COCO18 body, face omitted','order':'row-major','columns':POSE_SHEET_COLUMNS,'cell_size':[512,512],'sampling':'none','motions':{},'files':{}}
    execution_record_directory=WORKFLOW_ROOT_DIRECTORY/'.tmp/test/game-pose-sheets'/datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
    execution_record_directory.mkdir(parents=True,exist_ok=False)
    execution_log_path=execution_record_directory/'build.log'
    def record_build_progress(progress_stage_name,progress_message_text):
        progress_log_line=f'{datetime.now().isoformat()}/game-pose-sheets/{progress_stage_name} {progress_message_text}\n'
        print(progress_log_line,end='',flush=True)
        with execution_log_path.open('a') as execution_log_handle:execution_log_handle.write(progress_log_line)
    try:
        for motion_asset_name,source_folder_name,motion_frame_count,pose_subdirectory_name,source_manifest_name in POSE_SOURCE_RECORDS:
            source_asset_directory=WORKFLOW_ROOT_DIRECTORY/'assets/motion-sheet'/source_folder_name
            source_manifest_path=source_asset_directory/source_manifest_name
            source_manifest_record=yaml.safe_load(source_manifest_path.read_text())
            if source_manifest_record['frames']!=motion_frame_count or source_manifest_record['fps']!=4:raise ValueError('등록 모션 프레임·fps 불일치')
            motion_manifest_record={'source_asset_path':str(source_asset_directory.relative_to(WORKFLOW_ROOT_DIRECTORY)),'source_manifest_sha256':calculate_asset_digest(source_manifest_path),'frames':motion_frame_count,'duration_seconds':motion_frame_count/4,'directions':{}}
            for direction_name_value in POSE_DIRECTION_NAMES:
                direction_sheet_records=[]
                for page_start_index in range(0,motion_frame_count,POSE_SHEET_MAX_FRAMES):
                    page_frame_numbers=list(range(page_start_index+1,min(page_start_index+POSE_SHEET_MAX_FRAMES,motion_frame_count)+1))
                    page_row_count=math.ceil(len(page_frame_numbers)/POSE_SHEET_COLUMNS)
                    output_sheet_image=Image.new('RGB',(POSE_SHEET_COLUMNS*POSE_FRAME_CELL_SIZE,page_row_count*POSE_FRAME_CELL_SIZE),'black')
                    source_frame_hashes={}
                    for cell_frame_index,source_frame_number in enumerate(page_frame_numbers):
                        source_frame_path=source_asset_directory/pose_subdirectory_name/direction_name_value/f'openpose-{source_frame_number:04d}.png'
                        relative_source_name=str(source_frame_path.relative_to(source_asset_directory))
                        source_frame_digest=calculate_asset_digest(source_frame_path)
                        if source_manifest_record['files'].get(relative_source_name)!=source_frame_digest:raise ValueError(f'원본 해시 불일치: {source_frame_path}')
                        with Image.open(source_frame_path) as source_frame_image:
                            if source_frame_image.mode!='RGB' or source_frame_image.size!=(512,512):raise ValueError('포즈 프레임 형식 불일치')
                            output_sheet_image.paste(source_frame_image,((cell_frame_index%4)*512,(cell_frame_index//4)*512))
                        source_frame_hashes[relative_source_name]=source_frame_digest
                    relative_sheet_path=Path(motion_asset_name)/direction_name_value/f'page-{page_start_index//POSE_SHEET_MAX_FRAMES+1:02d}.png'
                    output_sheet_path=output_asset_directory/relative_sheet_path;output_sheet_path.parent.mkdir(parents=True,exist_ok=True);output_sheet_image.save(output_sheet_path)
                    direction_sheet_records.append({'path':str(relative_sheet_path),'frames':page_frame_numbers,'rows':page_row_count,'size':list(output_sheet_image.size),'start_seconds':page_start_index/4,'duration_seconds':len(page_frame_numbers)/4,'source_files':source_frame_hashes})
                    output_manifest_record['files'][str(relative_sheet_path)]=calculate_asset_digest(output_sheet_path)
                    record_build_progress('sheet',str(relative_sheet_path))
                motion_manifest_record['directions'][direction_name_value]=direction_sheet_records
            output_manifest_record['motions'][motion_asset_name]=motion_manifest_record
        (output_asset_directory/'manifest.yaml').write_text(yaml.safe_dump(output_manifest_record,allow_unicode=True,sort_keys=False))
        record_build_progress('complete',str(output_asset_directory))
    except Exception as build_error_value:
        record_build_progress('failed',str(build_error_value));raise


if __name__=='__main__':
    command_argument_parser=argparse.ArgumentParser(description=__doc__)
    command_argument_parser.add_argument('--output-dir',type=Path,required=True)
    command_argument_values=command_argument_parser.parse_args()
    build_game_pose_sheets(command_argument_values.output_dir.resolve())

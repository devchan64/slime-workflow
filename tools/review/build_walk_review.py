"""걷기 생성 결과의 공통 검수 페이지를 만든다."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.review.ui_assets import resolve_review_ui_asset, read_review_shared_styles
import argparse
from datetime import datetime
import json
import traceback

WORKFLOW_REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIRECTION_NAMES = {'down_left','down_right','up_left','up_right'}

def build_walk_review(review_run_directory):
    review_run_directory = review_run_directory.resolve()
    if not review_run_directory.is_relative_to(WORKFLOW_REPO_ROOT/'.tmp'):
        raise ValueError('워크플로우 .tmp 실행 폴더를 지정하세요.')
    review_log_path = review_run_directory/'build-review.log'
    def emit_review_trace(trace_stage_name, trace_message_text):
        trace_output_text=f'{datetime.now().isoformat()}/walk-review/{trace_stage_name} {trace_message_text}'
        print(trace_output_text,flush=True)
        with review_log_path.open('a') as trace_file_stream: trace_file_stream.write(trace_output_text+'\n')
    try:
        emit_review_trace('start',str(review_run_directory))
        result_manifest_data=json.loads((review_run_directory/'result.json').read_text())
        review_asset_records=result_manifest_data['outputs']
        if len(review_asset_records)!=4 or {current_asset_record['direction'] for current_asset_record in review_asset_records}!=REVIEW_DIRECTION_NAMES:
            raise ValueError('고유한 4방향 결과가 필요합니다.')
        for current_asset_record in review_asset_records:
            current_asset_record['rigImage'] = f"rig-{current_asset_record['direction']}.png"
            for current_image_name in (current_asset_record['image'], current_asset_record['rigImage']):
                if Path(current_image_name).name!=current_image_name or not (review_run_directory/current_image_name).is_file():
                    raise ValueError(f'검수 이미지 누락 또는 잘못된 경로: {current_image_name}')
            if len(current_asset_record['size'])!=2 or any(type(current_dimension_value)is not int or current_dimension_value<=0 for current_dimension_value in current_asset_record['size']):
                raise ValueError('이미지 크기는 양의 정수 2개여야 합니다.')
        review_template_text=resolve_review_ui_asset('walk-sheet.html').read_text()
        review_template_text=review_template_text.replace('</style>', '</style><style>'+read_review_shared_styles()+'</style>',1)
        embedded_asset_json=json.dumps(review_asset_records,ensure_ascii=False).replace('<','\\u003c')
        (review_run_directory/'preview.html').write_text(review_template_text.replace('__ASSET_RECORDS__',embedded_asset_json))
        emit_review_trace('complete',str(review_run_directory/'preview.html'))
    except Exception:
        emit_review_trace('failure',traceback.format_exc())
        print('\n'.join(review_log_path.read_text().splitlines()[-20:]),flush=True)
        raise

if __name__=='__main__':
    review_argument_parser=argparse.ArgumentParser(description=__doc__)
    review_argument_parser.add_argument('--root',required=True,type=Path)
    build_walk_review(review_argument_parser.parse_args().root)

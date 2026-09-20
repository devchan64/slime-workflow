"""걷기 비교·걷기 및 스탠딩 앵커 검수를 단일 메뉴 화면으로 묶는다."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import json
import shutil
import traceback

WORKFLOW_REPO_ROOT=Path(__file__).resolve().parents[2]
MANAGER_PAGE_SPECS=(('walk-review','걷기 비교','walking','preview.html',False),('walk-anchors','걷기 앵커','walking','anchors.html',True),('standing-anchors','스탠딩 앵커','standing','preview.html',True))

def build_frame_manager(parsed_argument_values):
    selected_source_directories={'walking':parsed_argument_values.walking.resolve(),'standing':parsed_argument_values.standing.resolve()}
    for source_kind_name,source_directory_path in selected_source_directories.items():
        if not source_directory_path.is_relative_to(WORKFLOW_REPO_ROOT/'.tmp') or not source_directory_path.is_dir():raise ValueError(f'{source_kind_name}: 워크플로우 .tmp 실행 폴더가 필요합니다.')
    for page_identifier_text,page_label_text,source_kind_name,page_filename_text,anchor_editor_enabled in MANAGER_PAGE_SPECS:
        if not (selected_source_directories[source_kind_name]/page_filename_text).is_file():raise ValueError(f'검수 페이지 누락: {source_kind_name}/{page_filename_text}')
    output_manager_directory=WORKFLOW_REPO_ROOT/'.tmp'/datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
    output_manager_directory.mkdir(exist_ok=False)
    execution_log_path=output_manager_directory/'frame-manager.log'
    def emit_manager_trace(trace_stage_name,trace_message_text):
        trace_output_line=f'{datetime.now().isoformat()}/frame-manager/{trace_stage_name} {trace_message_text}'
        print(trace_output_line,flush=True)
        with execution_log_path.open('a') as execution_log_stream:execution_log_stream.write(trace_output_line+'\n')
    try:
        emit_manager_trace('start',str(output_manager_directory))
        manager_page_records=[]
        shared_review_styles=Path(__file__).with_name('review-ui.css').read_text()
        for source_kind_name,source_directory_path in selected_source_directories.items():
            destination_asset_directory=output_manager_directory/source_kind_name
            destination_asset_directory.mkdir()
            permitted_page_names={page_filename_text for _,_,current_source_kind,page_filename_text,_ in MANAGER_PAGE_SPECS if current_source_kind==source_kind_name}
            for source_file_path in source_directory_path.iterdir():
                if source_file_path.is_file() and (source_file_path.suffix.lower() in ('.png','.jpg','.webp','.gif') or source_file_path.name in permitted_page_names):
                    shutil.copy2(source_file_path,destination_asset_directory/source_file_path.name)
            emit_manager_trace('copy',source_kind_name)
        for page_identifier_text,page_label_text,source_kind_name,page_filename_text,anchor_editor_enabled in MANAGER_PAGE_SPECS:
            copied_review_path=output_manager_directory/source_kind_name/page_filename_text
            copied_review_html=copied_review_path.read_text()
            current_template_path=(WORKFLOW_REPO_ROOT/'generators/animation/review_standing_anchors.html') if anchor_editor_enabled else Path(__file__).with_name('walk-sheet.html')
            current_template_html=current_template_path.read_text()
            embedded_constant_names=(('reviewFrameRecords','__FRAME_RECORDS__'),('reviewSourceMetadata','__SOURCE_METADATA__')) if anchor_editor_enabled else (('reviewAssetRecords','__ASSET_RECORDS__'),)
            for embedded_constant_name,template_marker_text in embedded_constant_names:
                embedded_marker_text=f'const {embedded_constant_name}='
                if copied_review_html.count(embedded_marker_text)!=1:
                    raise ValueError(f'지원하지 않는 검수 페이지 데이터: {copied_review_path} / {embedded_constant_name}')
                embedded_json_value,_=json.JSONDecoder().raw_decode(copied_review_html.split(embedded_marker_text,1)[1].lstrip())
                current_template_html=current_template_html.replace(template_marker_text,json.dumps(embedded_json_value,ensure_ascii=False).replace('<','\\u003c'))
            copied_review_path.write_text(current_template_html.replace('</style>','</style><style>'+shared_review_styles+'</style>',1))
            manager_page_records.append({'id':page_identifier_text,'label':page_label_text,'path':f'{source_kind_name}/{page_filename_text}','category':'web-review','anchorEditor':anchor_editor_enabled,'description':f'{page_label_text} · 원본 실행 {selected_source_directories[source_kind_name].name}'})
        manager_template_text=Path(__file__).with_name('frame-manager.html').read_text()
        manager_template_text=manager_template_text.replace('</style>', '</style><style>'+(Path(__file__).with_name('review-ui.css')).read_text()+'</style>',1)
        (output_manager_directory/'preview.html').write_text(manager_template_text.replace('__MANAGER_PAGES__',json.dumps(manager_page_records,ensure_ascii=False).replace('<','\\u003c')))
        (output_manager_directory/'manager-source.json').write_text(json.dumps({'description':'워크프레임 통합 검수 실행 스냅샷','sources':{source_kind_name:str(source_directory_path) for source_kind_name,source_directory_path in selected_source_directories.items()},'pages':manager_page_records},ensure_ascii=False,indent=2))
        emit_manager_trace('complete',str(output_manager_directory/'preview.html'))
        return output_manager_directory
    except Exception:
        emit_manager_trace('failure',traceback.format_exc())
        print('\n'.join(execution_log_path.read_text().splitlines()[-20:]),flush=True)
        raise

if __name__=='__main__':
    manager_argument_parser=argparse.ArgumentParser(description=__doc__)
    manager_argument_parser.add_argument('--walking',type=Path,required=True)
    manager_argument_parser.add_argument('--standing',type=Path,required=True)
    build_frame_manager(manager_argument_parser.parse_args())

"""정적 검수 스냅샷을 Gradio 작업 영역의 사용자 정의 구성 요소로 제공한다."""
import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

import gradio as gr
WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.ui.gradio.anchor_native_preview import read_native_anchor_loader
from tools.review.common.gradio_frame_navigator import build_frame_navigator, build_browser_playback_speed
from tools.review.common.gradio_joypad import build_transform_joypad
from tools.review.common.gradio_browser_controls import build_browser_action_button
from tools.review.common.gradio_browser_history import build_browser_history_controls
from tools.review.common.gradio_browser_confirmation import build_browser_confirmation


from tools.review.common.static_review_registry import load_static_review_paths


def create_anchor_navigation_status_script(current_control_count,current_selection_enabled=False):
    """준비·실패 상태에서는 프레임 탐색을 차단하고 원인을 함께 표시한다."""
    current_status_script="""(currentActionIdentifier,currentDirectionName,currentPointName)=>{
 let currentReadyState=false,currentStatusText='애니메이션을 준비 중입니다.';
 try{
  if(typeof window.anchorReviewPlayback==='function'){
   currentStatusText=window.anchorReviewPlayback('status');
   currentReadyState=true;
  }
 }catch(currentLoadError){currentStatusText=currentLoadError.message+' 검수 화면을 새로고침하거나 원본과 초안을 확인하세요.';}
 return [currentStatusText,...Array(CONTROL_COUNT).fill(null).map(()=>({__type__:'update',interactive:currentReadyState}))];
}""".replace('CONTROL_COUNT',str(current_control_count))
    if current_selection_enabled:
        current_status_script=current_status_script.replace("interactive:currentReadyState}))];","interactive:currentReadyState})),{__type__:'update',interactive:currentReadyState&&Boolean(currentActionIdentifier)},{__type__:'update',interactive:currentReadyState&&Boolean(currentDirectionName&&currentPointName)}];")
    return current_status_script



def collect_anchor_review_paths(static_review_paths, current_anchor_paths=None):
    current_declared_paths={'/'+current_path_value.split('?')[0].lstrip('/'):current_path_value.split('?')[0] for current_path_value in static_review_paths.values()}
    current_selected_paths={'/'+current_path_value.split('?')[0].lstrip('/') for current_path_value in (current_anchor_paths or [])}
    if not current_selected_paths.issubset(current_declared_paths):
        raise ValueError('등록되지 않은 앵커 검수 경로입니다.')
    current_selected_paths.update(current_path_value for current_path_value in current_declared_paths if current_path_value.endswith('/anchors.html'))
    return sorted(current_declared_paths[current_path_value] for current_path_value in current_selected_paths)


def create_static_review_loader(review_server_port, static_review_paths, current_anchor_paths=None):
    serialized_paths=json.dumps(static_review_paths,ensure_ascii=False).replace('<','\\u003c')
    review_server_base=json.dumps(f'http://127.0.0.1:{review_server_port}')
    current_anchor_paths_json=json.dumps(collect_anchor_review_paths(static_review_paths,current_anchor_paths),ensure_ascii=False).replace('<','\\u003c')
    return f"""async()=>{{
{read_native_anchor_loader()}
{(Path(__file__).with_name("game_native_loader.js")).read_text()}
const staticReviewRoot=document.querySelector('#static-review-root');
if(!staticReviewRoot||staticReviewRoot.dataset.staticReviewLoaded)return;
staticReviewRoot.dataset.staticReviewLoaded='true';
const staticReviewPaths={serialized_paths};
const reviewServerBase={review_server_base};
const reviewIdentifier=new URLSearchParams(window.location.search).get('review');
const selectedReviewPath=Object.hasOwn(staticReviewPaths,reviewIdentifier)?staticReviewPaths[reviewIdentifier]:null;
if(!selectedReviewPath){{staticReviewRoot.innerHTML='<p class="static-review-error" role="alert">표시할 정적 검수 페이지를 찾을 수 없습니다.</p>';staticReviewRoot.setAttribute('aria-busy','false');return;}}
const staticReviewPageLocation=new URL(selectedReviewPath,reviewServerBase);
staticReviewPageLocation.searchParams.set('embedded','gradio-static');
const currentSelectedAction=new URLSearchParams(window.location.search).get('action');
if(currentSelectedAction)staticReviewPageLocation.searchParams.set('action',currentSelectedAction);
if({current_anchor_paths_json}.includes(selectedReviewPath.split('?')[0])){{await mountNativeAnchorReview(staticReviewRoot,staticReviewPageLocation);return;}}
if(['/design-system.html','/battlefield-preview.html'].some(currentPageSuffix=>selectedReviewPath.split('?')[0].endsWith(currentPageSuffix))){{
  const currentBrowserParameters=new URLSearchParams(window.location.search);
  for(const currentParameterName of ['field','locale','overview'])if(currentBrowserParameters.has(currentParameterName))staticReviewPageLocation.searchParams.set(currentParameterName,currentBrowserParameters.get(currentParameterName));
  await mountNativeGameReview(staticReviewRoot,staticReviewPageLocation);return;
}}
staticReviewRoot.textContent='지원하지 않는 정적 검수 화면입니다. 직접 마운트 모듈로 게시하세요.';
staticReviewRoot.setAttribute('aria-busy','false');

}}"""


def build_static_review_interface(static_review_paths, current_anchor_paths=None, current_animation_records=None):
    current_anchor_paths_json=json.dumps(collect_anchor_review_paths(static_review_paths,current_anchor_paths),ensure_ascii=False).replace('<','\\u003c')
    current_review_paths_json=json.dumps(static_review_paths,ensure_ascii=False).replace('<','\\u003c')
    with gr.Blocks(title='정적 검수') as interface_blocks_value:
        gr.Markdown('## 정적 검수\n게임 디자인과 등록 애니메이션을 검수합니다.')
        current_sprite_records=current_animation_records or []
        current_sprite_identifiers=[current_sprite_record['id'] for current_sprite_record in current_sprite_records]
        with gr.Group(visible=False) as current_sprite_group:
            gr.Markdown('### 등록 스프라이트 목록')
            current_sprite_search=gr.Textbox(label='스프라이트 검색',placeholder='이름, 등록 ID, 원본 경로')
            current_sprite_choice=gr.Dropdown(label='검수할 스프라이트',choices=[(current_sprite_record['label'],current_sprite_record['id']) for current_sprite_record in current_sprite_records],value=None,interactive=True,filterable=True)
            current_sprite_count=gr.Markdown(f'등록 스프라이트 {len(current_sprite_records)}개')
            current_sprite_open=gr.Button('선택 스프라이트 열기',interactive=False)
            gr.Markdown('목록 선택 후 열기를 누르면 해당 스프라이트의 동작·방향·프레임을 검수합니다. 편집한 좌표는 전환 전에 저장하세요.')
        def filter_sprite_catalog(current_search_value,current_selected_identifier):
            current_search_tokens=(current_search_value or '').casefold().split()
            current_filtered_records=[current_sprite_record for current_sprite_record in current_sprite_records if all(current_search_token in (' '.join(str(current_sprite_record.get(current_field_name,'')) for current_field_name in ('label','id','description','path'))).casefold() for current_search_token in current_search_tokens)]
            current_retained_identifier=current_selected_identifier if any(current_sprite_record['id']==current_selected_identifier for current_sprite_record in current_filtered_records) else None
            return gr.update(choices=[(current_sprite_record['label'],current_sprite_record['id']) for current_sprite_record in current_filtered_records],value=current_retained_identifier),f'{len(current_filtered_records)}개 / 전체 {len(current_sprite_records)}개',gr.update(interactive=current_retained_identifier is not None)
        current_sprite_search.input(filter_sprite_catalog,[current_sprite_search,current_sprite_choice],[current_sprite_choice,current_sprite_count,current_sprite_open],queue=False,preprocess=False)
        current_sprite_choice.change(lambda current_selected_identifier:gr.update(interactive=current_selected_identifier in current_sprite_identifiers),current_sprite_choice,current_sprite_open,queue=False,preprocess=False)
        current_sprite_open.click(fn=None,inputs=current_sprite_choice,queue=False,js="currentSelectedIdentifier=>{const currentAllowedIdentifiers="+json.dumps(current_sprite_identifiers)+";if(!currentAllowedIdentifiers.includes(currentSelectedIdentifier))throw Error('등록 스프라이트를 선택하세요.');const currentTargetUrl=new URL(location.href);currentTargetUrl.searchParams.set('review',currentSelectedIdentifier);currentTargetUrl.searchParams.set('tool',currentSelectedIdentifier);currentTargetUrl.searchParams.set('category','animation');currentTargetUrl.searchParams.delete('action');location.assign(currentTargetUrl.href);}")
        interface_blocks_value.load(fn=None,outputs=[current_sprite_group,current_sprite_choice,current_sprite_open],queue=False,js="()=>{const currentAllowedIdentifiers="+json.dumps(current_sprite_identifiers)+";const currentSelectedIdentifier=new URLSearchParams(location.search).get('review');const currentIsRegistered=currentAllowedIdentifiers.includes(currentSelectedIdentifier);return [{__type__:'update',visible:currentIsRegistered},{__type__:'update',value:currentIsRegistered?currentSelectedIdentifier:null},{__type__:'update',interactive:currentIsRegistered}];}")
        current_reload_button=gr.Button('검수 화면 새로고침')
        current_reload_button.click(fn=None,js="()=>{window.location.reload();}",queue=False)
        with gr.Column(visible=False) as current_battlefield_controls:
            gr.Markdown('### 전장 검수')
            current_battlefield_choice=gr.Dropdown(label='전장 선택',choices=[],interactive=True)
            current_battlefield_status=gr.Textbox(label='전장 렌더 상태',interactive=False)
            current_battlefield_choice.input(fn=None,inputs=current_battlefield_choice,outputs=[current_battlefield_choice,current_battlefield_status],queue=False,js="currentSelectedField=>{try{return window.battlefieldReviewControls(currentSelectedField);}catch(currentErrorValue){return [{__type__:'update'},currentErrorValue.message];}}")
        current_battlefield_timer=gr.Timer(1)
        current_battlefield_timer.tick(fn=None,outputs=[current_battlefield_choice,current_battlefield_status],queue=False,show_progress='hidden',js="()=>{if(typeof window.battlefieldReviewControls!=='function')return [{__type__:'update'},{__type__:'update'}];try{const currentResultValues=window.battlefieldReviewControls(null);const currentChoiceSignature=JSON.stringify(currentResultValues[0]);if(window.battlefieldChoiceSignature===currentChoiceSignature)currentResultValues[0]={__type__:'update'};else window.battlefieldChoiceSignature=currentChoiceSignature;return currentResultValues;}catch(currentErrorValue){return [{__type__:'update'},currentErrorValue.message];}}")
        interface_blocks_value.load(fn=None,outputs=current_battlefield_controls,queue=False,js="()=>{const currentReviewPaths="+json.dumps(static_review_paths,ensure_ascii=False)+";return {__type__:'update',visible:(Object.hasOwn(currentReviewPaths,new URLSearchParams(location.search).get('review'))?currentReviewPaths[new URLSearchParams(location.search).get('review')]:'').split('?')[0].endsWith('battlefield-preview.html')};}")
        with gr.Row():
            with gr.Column(visible=False,scale=1) as current_anchor_controls:
                gr.Markdown('프레임별 기준점을 원본 픽셀 단위로 조정합니다. 정지 상태에서 미리보기를 클릭하거나 조이패드를 사용하세요. 원점은 셀 왼쪽 위이며 오른쪽은 +X, 아래는 +Y입니다. 최종 앵커 이동 시 두 발 좌표도 함께 이동합니다.')
                current_anchor_status=gr.Textbox(label='프레임 탐색 상태',value='애니메이션을 준비 중입니다.',interactive=False)
                current_anchor_timer=gr.Timer(1)
                current_navigation_controls=[]
                current_anchor_feedback=gr.Textbox(label='조작 안내',value='프레임을 이동하거나 편집할 좌표를 선택하세요.',interactive=False)
                with gr.Row():
                    current_animation_action=gr.Dropdown(label='애니메이션 동작',choices=[],interactive=True)
                    current_animation_read=gr.Button('동작 목록 읽기',interactive=False)
                    current_animation_apply=gr.Button('선택 동작 불러오기',interactive=False)
                gr.Markdown('동작 목록을 읽고 사용할 동작을 선택하면 불러올 수 있습니다.')
                current_animation_action.change(fn=None,inputs=current_animation_action,outputs=current_animation_apply,queue=False,js="currentActionIdentifier=>{try{window.anchorReviewPlayback('status');return {__type__:'update',interactive:typeof currentActionIdentifier==='string'&&currentActionIdentifier.length>0};}catch(currentErrorValue){return {__type__:'update',interactive:false};}}")
                current_animation_read.click(fn=None,outputs=[current_animation_action,current_anchor_feedback],queue=False,js="()=>{try{return window.anchorReviewActions(null);}catch(currentErrorValue){return [{__type__:'update'},currentErrorValue.message];}}")
                current_animation_apply.click(fn=None,inputs=current_animation_action,outputs=[current_animation_action,current_anchor_feedback,current_anchor_status],queue=False,js="currentActionIdentifier=>{try{if(!currentActionIdentifier)throw Error('동작 목록을 읽고 동작을 선택하세요.');const currentActionResult=window.anchorReviewActions(currentActionIdentifier);return [...currentActionResult,typeof window.anchorReviewPlayback==='function'?window.anchorReviewPlayback('status'):'선택한 동작을 불러오는 중입니다.'];}catch(currentErrorValue){return [{__type__:'update'},currentErrorValue.message,{__type__:'update'}];}}")
                build_frame_navigator('anchorReviewPlayback','anchorReviewSeekFrame',current_anchor_status,current_navigation_controls)
                current_navigation_controls.append(build_browser_playback_speed('anchorReviewFrameRate',current_anchor_feedback,current_controls_enabled=False))
                with gr.Row():
                    current_anchor_direction=gr.Dropdown(label='방향',choices=[],interactive=True)
                    current_anchor_point=gr.Dropdown(label='편집할 좌표',choices=[],interactive=True)
                with gr.Row():
                    current_anchor_read=gr.Button('선택 목록 읽기',interactive=False)
                    current_anchor_apply=gr.Button('방향·좌표 선택 적용',interactive=False)
                gr.Markdown('선택 목록을 읽고 방향과 편집할 좌표를 모두 선택하세요.')
                gr.on(triggers=[current_anchor_direction.change,current_anchor_point.change],inputs=[current_anchor_direction,current_anchor_point],outputs=current_anchor_apply,queue=False,preprocess=False,fn=None,js="(currentDirectionName,currentPointName)=>{try{window.anchorReviewPlayback('status');return {__type__:'update',interactive:Boolean(currentDirectionName&&currentPointName)};}catch(currentErrorValue){return {__type__:'update',interactive:false};}}")
                current_anchor_outputs=[current_anchor_direction,current_anchor_point,current_anchor_feedback]
                current_anchor_read.click(fn=None,outputs=[*current_anchor_outputs,current_anchor_apply],queue=False,js="()=>{try{const currentSelectionValues=window.anchorReviewSelection(null,null);return [...currentSelectionValues,{__type__:'update',interactive:Boolean(currentSelectionValues[0].value && currentSelectionValues[1].value)}];}catch(currentErrorValue){return [{__type__:'update'},{__type__:'update'},currentErrorValue.message,{__type__:'update',interactive:false}];}}")
                current_anchor_apply.click(fn=None,inputs=[current_anchor_direction,current_anchor_point],outputs=current_anchor_outputs,queue=False,js="(currentDirectionName,currentPointName)=>{try{return window.anchorReviewSelection(currentDirectionName,currentPointName);}catch(currentErrorValue){return [{__type__:'update'},{__type__:'update'},currentErrorValue.message];}}")
                build_transform_joypad('anchorReviewCoordinates',current_anchor_feedback,current_scale_enabled=False,current_readiness_controls=current_navigation_controls)
                with gr.Row():
                    for current_command_name,current_command_label in [('undo','실행 취소'),('redo','다시 실행'),('previous','이전 프레임 앵커 가져오기'),('reset','현재 프레임 원본 복원'),('status','좌표 변경 상태 읽기')]:
                        current_navigation_controls.append(build_browser_action_button(current_command_label,'anchorReviewCoordinateCommands',current_command_name,current_anchor_feedback,current_button_enabled=False))

                with gr.Accordion('미리보기 표시',open=False):
                    gr.Markdown('앵커는 타일 중심에 고정됩니다. 표시 설정은 좌표를 변경하지 않습니다.')
                    with gr.Row():
                        current_display_fields=[gr.Checkbox(label=current_display_label,value=True) for current_display_label in ['가이드','리그 보기','가상 타일','그림자']]
                    with gr.Row():
                        current_display_read=gr.Button('표시 설정 읽기',interactive=False)
                        current_display_apply=gr.Button('표시 설정 적용',interactive=False)
                    current_display_outputs=[*current_display_fields,current_anchor_feedback]
                    current_display_read.click(fn=None,outputs=current_display_outputs,queue=False,js="()=>{try{return window.anchorReviewDisplay(null);}catch(currentErrorValue){return [...Array.from({length:4},()=>({__type__:'update'})),currentErrorValue.message];}}")
                    current_display_apply.click(fn=None,inputs=current_display_fields,outputs=current_display_outputs,queue=False,js="(...currentDisplayValues)=>{try{return window.anchorReviewDisplay(currentDisplayValues);}catch(currentErrorValue){return [...Array.from({length:4},()=>({__type__:'update'})),currentErrorValue.message];}}")


                with gr.Accordion('게임 출력 크기',open=False):
                    current_output_scale=gr.Checkbox(label='게임 출력 비율',value=True)
                    with gr.Row():
                        current_output_map=gr.Dropdown(label='맵 기준',choices=[('필드·전투','field'),('마을','town')],value='field')
                        current_output_size=gr.Dropdown(label='크기 등급',choices=[('소형 · 50%','small'),('중형 · 100%','medium'),('대형 · 150%','large'),('초대형 · 200%','huge')],value='medium')
                    with gr.Row():
                        current_output_height=gr.Number(label='출력 신체 높이 (px)',value=80,minimum=1,maximum=240,precision=0)
                        current_output_width=gr.Number(label='검수 타일 너비 (px)',value=240,minimum=32,maximum=600,precision=0)
                    gr.Markdown('타일 높이는 너비의 1/2로 계산합니다. 현재 설정을 읽은 뒤 적용하세요.')
                    current_output_feedback=gr.Textbox(label='출력 크기 상태',interactive=False)
                    current_output_fields=[current_output_scale,current_output_map,current_output_size,current_output_height,current_output_width]
                    with gr.Row():
                        current_output_read=gr.Button('출력 설정 읽기',interactive=False)
                        current_output_apply=gr.Button('출력 설정 적용',interactive=False)
                    current_output_read.click(fn=None,outputs=[*current_output_fields,current_output_feedback],queue=False,js="()=>{try{return window.anchorReviewOutputSettings(null);}catch(currentErrorValue){return [...Array.from({length:5},()=>({__type__:'update'})),currentErrorValue.message];}}")
                    current_output_apply.click(fn=None,inputs=current_output_fields,outputs=[*current_output_fields,current_output_feedback],queue=False,js="(...currentOutputValues)=>{try{return window.anchorReviewOutputSettings(currentOutputValues);}catch(currentErrorValue){return [...Array.from({length:5},()=>({__type__:'update'})),currentErrorValue.message];}}")
                    current_navigation_controls.append(build_browser_action_button('정규화 JSON 다운로드','anchorReviewDownloadSettings','download',current_output_feedback,current_button_enabled=False))

                current_navigation_controls.append(build_browser_action_button('좌표 저장','anchorReviewSaveCoordinates','save',current_anchor_feedback,current_button_enabled=False))
                current_navigation_controls.extend([current_animation_read,current_anchor_read,current_display_read,current_display_apply,current_output_read,current_output_apply])
                current_anchor_timer.tick(fn=None,inputs=[current_animation_action,current_anchor_direction,current_anchor_point],outputs=[current_anchor_status,*current_navigation_controls,current_animation_apply,current_anchor_apply],queue=False,show_progress='hidden',js=create_anchor_navigation_status_script(len(current_navigation_controls),True))

            with gr.Column(scale=2):
                with gr.Column(visible=False) as current_anchor_legend:
                    gr.Markdown('### 프레임 미리보기\n노랑: 기준선 · 청록: 발 중심 · 빨강: 최종 앵커 · 자주: 권장 신체 높이')
                gr.HTML('<section id="static-review-root" aria-label="정적 검수" aria-live="polite" aria-busy="true"><p>검수 화면을 준비하고 있습니다…</p></section>')
        build_browser_confirmation('anchorRestoreConfirmationState','resolveAnchorRestoreConfirmation')
        with gr.Accordion('손상된 앵커 초안 복구',open=False,visible=False) as current_draft_recovery_group:
            gr.Markdown('복원 실패한 초안을 현재 브라우저 세션에 별도 보관하고 원본 좌표로 다시 엽니다. 보관본도 탭 세션 종료 시 사라질 수 있습니다. 저장된 서버 이력은 변경하지 않습니다.')
            current_draft_confirmation=gr.Checkbox(label='초안을 세션에 보관하고 원본으로 다시 열겠습니다.',value=False)
            current_draft_recovery=gr.Button('초안 보관 후 원본 열기')
            current_draft_feedback=gr.Textbox(label='초안 복구 안내',interactive=False)
            current_draft_recovery.click(fn=None,inputs=current_draft_confirmation,outputs=[current_draft_feedback,current_draft_confirmation],queue=False,js="currentConfirmedValue=>{try{if(typeof window.anchorRecoverStoredDraft!=='function')throw Error('복원에 실패한 앵커 초안이 없습니다.');return [window.anchorRecoverStoredDraft(currentConfirmedValue),false];}catch(currentRecoveryError){return [currentRecoveryError.message,false];}}")

        with gr.Column(visible=False) as current_anchor_history:
            build_browser_history_controls('anchorReviewHistory','anchor-standard-history',current_supported_actions=('list','result','restore','reset'), current_reset_target_handler='anchorReviewResetTarget')

        interface_blocks_value.load(fn=None,outputs=[current_anchor_controls,current_anchor_history,current_anchor_legend,current_draft_recovery_group],queue=False,js="()=>{const currentReviewPaths="+current_review_paths_json+";const currentReviewId=new URLSearchParams(location.search).get('review');const currentAnchorVisible="+current_anchor_paths_json+".includes((Object.hasOwn(currentReviewPaths,currentReviewId)?currentReviewPaths[currentReviewId]:'').split('?')[0]);return Array.from({length:4},()=>({__type__:'update',visible:currentAnchorVisible}));}")
    return interface_blocks_value



if __name__=='__main__':
    parser_value=argparse.ArgumentParser()
    parser_value.add_argument('--port',type=int,required=True)
    parser_value.add_argument('--review-port',type=int,required=True)
    parser_value.add_argument('--owner-pid',type=int,required=True)
    parser_value.add_argument('--source-file',type=Path,required=True)
    parser_value.add_argument('--root-path',default='/management/frame/static-review/')
    arguments_value=parser_value.parse_args()
    static_review_paths=load_static_review_paths(arguments_value.source_file)
    def monitor_owner_process():
        while os.getppid()==arguments_value.owner_pid:time.sleep(1)
        os._exit(0)
    threading.Thread(target=monitor_owner_process,daemon=True).start()
    from tools.review.ui.gradio.management_menu_app import build_management_menu_interface, load_manager_page_records
    current_page_records=load_manager_page_records(arguments_value.source_file)
    current_catalog_records=load_manager_page_records(arguments_value.source_file,current_animation_catalog=True)
    current_anchor_paths=[current_page_record['path'].split('?')[0] for current_page_record in current_catalog_records if current_page_record.get('anchorEditor') and current_page_record.get('uiMode')=='gradio-static']
    current_inline_interface=build_static_review_interface(static_review_paths,current_anchor_paths,[current_page_record for current_page_record in current_catalog_records if current_page_record['category']=='animation'])
    current_management_interface,_=build_management_menu_interface(current_page_records,arguments_value.review_port,current_inline_interface)
    current_management_interface.queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,js=create_static_review_loader(arguments_value.review_port,static_review_paths,current_anchor_paths),allowed_paths=[])

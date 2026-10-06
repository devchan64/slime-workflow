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
from tools.review.common.gradio_frame_navigator import build_frame_navigator
from tools.review.common.gradio_joypad import build_transform_joypad
from tools.review.common.gradio_browser_controls import build_browser_action_button
from tools.review.common.gradio_browser_history import build_browser_history_controls


STATIC_REVIEW_FRAME_HEIGHT=1000
TERRAIN_REVIEW_MAP_CHOICES=[('이슬 초원','meadow'),('푸른 숲','grove'),('안개 호수','mist-lake'),('바람 구릉','wind-hills')]


def load_static_review_paths(source_file_path):
    source_record_values=json.loads(Path(source_file_path).read_text())
    static_review_paths={}
    for current_page_record in source_record_values.get('pages',[]):
        if current_page_record.get('uiMode')!='gradio-static':continue
        current_identifier_value=current_page_record.get('id')
        current_path_value=current_page_record.get('path')
        if not isinstance(current_identifier_value,str) or not current_identifier_value or not isinstance(current_path_value,str) or not current_path_value:
            raise ValueError('정적 검수 페이지 항목 형식 오류')
        static_review_paths[current_identifier_value]=current_path_value
    return static_review_paths


def create_static_review_loader(review_server_port, static_review_paths):
    serialized_paths=json.dumps(static_review_paths,ensure_ascii=False).replace('<','\\u003c')
    review_server_base=json.dumps(f'http://127.0.0.1:{review_server_port}')
    return f"""async()=>{{
const staticReviewRoot=document.querySelector('#static-review-root');
if(!staticReviewRoot||staticReviewRoot.dataset.staticReviewLoaded)return;
staticReviewRoot.dataset.staticReviewLoaded='true';
const staticReviewPaths={serialized_paths};
const reviewServerBase={review_server_base};
const reviewIdentifier=new URLSearchParams(window.location.search).get('review');
const selectedReviewPath=staticReviewPaths[reviewIdentifier];
if(!selectedReviewPath){{staticReviewRoot.innerHTML='<p class="static-review-error" role="alert">표시할 정적 검수 페이지를 찾을 수 없습니다.</p>';return;}}
const staticReviewPageLocation=new URL(selectedReviewPath,reviewServerBase);
staticReviewPageLocation.searchParams.set('embedded','gradio-static');
const staticReviewPageUrl=staticReviewPageLocation.href;
// 게임 디자인 및 지형 검수의 스타일·모듈·중첩 프리뷰 상대 경로를 원래 문서에 격리한다.
{{
  const currentReviewFrame=document.createElement('iframe');
  const currentAnchorReview=selectedReviewPath.split('?')[0].endsWith('/anchors.html');
  currentReviewFrame.title=currentAnchorReview?'등록 애니메이션 앵커 검수':'게임 디자인 검수';
  if(currentAnchorReview){{
    for(const currentHandlerName of ['anchorReviewSelection','anchorReviewCoordinates','anchorReviewDisplay','anchorReviewOutputSettings','anchorReviewDownloadSettings','anchorReviewActions','anchorReviewCoordinateCommands','anchorReviewHistory','anchorReviewSaveCoordinates'])window[currentHandlerName]=(...currentArgumentValues)=>{{const currentHandlerFunction=currentReviewFrame.contentWindow[currentHandlerName];if(typeof currentHandlerFunction!=='function')throw Error('애니메이션을 준비 중입니다.');return currentHandlerFunction(...currentArgumentValues);}};
    window.anchorReviewPlayback=currentActionName=>{{const currentPlaybackHandler=currentReviewFrame.contentWindow.anchorReviewPlayback;if(typeof currentPlaybackHandler!=='function')throw Error('애니메이션을 준비 중입니다. 잠시 후 다시 시도하세요.');return currentPlaybackHandler(currentActionName);}};
    window.anchorReviewSeekFrame=currentFrameNumber=>{{const currentSeekHandler=currentReviewFrame.contentWindow.anchorReviewSeekFrame;if(typeof currentSeekHandler!=='function')throw Error('애니메이션을 준비 중입니다. 잠시 후 다시 시도하세요.');return currentSeekHandler(currentFrameNumber);}};
  }}
  if(currentAnchorReview){{
    let currentPreviewObserver=null;
    currentReviewFrame.addEventListener('load',()=>{{
      currentPreviewObserver?.disconnect();
      const currentPreviewPanel=currentReviewFrame.contentDocument.querySelector('.anchor-workspace');
      if(!currentPreviewPanel)return;
      const updatePreviewHeight=()=>{{const currentContentHeight=Math.ceil(currentPreviewPanel.getBoundingClientRect().bottom+currentReviewFrame.contentWindow.scrollY);if(currentContentHeight>0)currentReviewFrame.height=String(currentContentHeight);}};
      currentPreviewObserver=new ResizeObserver(updatePreviewHeight);
      currentPreviewObserver.observe(currentPreviewPanel);
      updatePreviewHeight();
    }});
    window.addEventListener('pagehide',()=>currentPreviewObserver?.disconnect(),{{once:true}});
  }}
  currentReviewFrame.width='100%';currentReviewFrame.height='{STATIC_REVIEW_FRAME_HEIGHT}';currentReviewFrame.setAttribute('frameborder','0');
  const currentTerrainReview=selectedReviewPath.split('?')[0].endsWith('terrain-layout-manager.html');
  const currentPreviewLocation=currentTerrainReview?new URL('terrain-preview.html',staticReviewPageUrl):new URL(staticReviewPageUrl);
  currentPreviewLocation.searchParams.set('embedded','gradio-static');
  currentReviewFrame.src=currentPreviewLocation.href;
  if(currentTerrainReview){{
    currentReviewFrame.title='필드 탐색 게임 미리보기';
    currentReviewFrame.addEventListener('load',()=>{{const currentPreviewToolbar=currentReviewFrame.contentDocument?.querySelector('.preview-tools');if(currentPreviewToolbar){{const currentHiddenContainer=currentReviewFrame.contentDocument.createElement('div');currentHiddenContainer.hidden=true;currentPreviewToolbar.before(currentHiddenContainer);currentHiddenContainer.append(currentPreviewToolbar);}}}});
    window.terrainReviewControls=async(currentActionName,currentMapName)=>{{
      const currentPreviewDocument=currentReviewFrame.contentDocument;
      const currentStatusElement=currentPreviewDocument?.querySelector('#result');
      if(!currentStatusElement||!currentStatusElement.textContent.includes('타일'))throw Error('게임 미리보기를 준비 중입니다. 준비 후 다시 시도하세요.');
      if(currentActionName==='status')return currentStatusElement.textContent;
      if(currentActionName==='map'){{
        const currentMapSelector=currentPreviewDocument.querySelector('#map-choice');
        if(!Array.from(currentMapSelector.options).some(currentOptionValue=>currentOptionValue.value===currentMapName))throw Error('지원하지 않는 맵입니다.');
        currentMapSelector.value=currentMapName;currentMapSelector.onchange({{target:currentMapSelector}});
      }}else if(['zoom-out','zoom-in','preview-focus'].includes(currentActionName)){{
        const currentActionElement=currentPreviewDocument.getElementById(currentActionName);
        if(typeof currentActionElement?.onclick!=='function')throw Error('게임 미리보기 조작을 준비 중입니다.');
        currentActionElement.onclick();
      }}else if(currentActionName!=='status')throw Error('지원하지 않는 화면 조정입니다.');
      await new Promise(currentResolveFrame=>currentReviewFrame.contentWindow.requestAnimationFrame(()=>currentReviewFrame.contentWindow.requestAnimationFrame(currentResolveFrame)));
      return currentStatusElement.textContent;
    }};
  }}
  currentReviewFrame.addEventListener('load',()=>staticReviewRoot.setAttribute('aria-busy','false'));
  staticReviewRoot.replaceChildren(currentReviewFrame);
  return;
}}

}}"""


def build_static_review_interface(static_review_paths):
    with gr.Blocks(title='정적 검수') as interface_blocks_value:
        gr.Markdown('## 정적 검수\n게임 디자인과 등록 애니메이션을 검수합니다.')
        current_reload_button=gr.Button('검수 화면 새로고침')
        current_reload_button.click(fn=None,js="()=>{window.location.reload();}",queue=False)
        with gr.Column(visible=False) as current_terrain_controls:
            current_terrain_choice=gr.Dropdown(label='맵 선택',choices=TERRAIN_REVIEW_MAP_CHOICES,value='meadow')
            current_terrain_status=gr.Textbox(label='게임 미리보기 상태',value='미리보기를 준비 중입니다.',interactive=False)
            with gr.Row():
                for current_action_name,current_action_label in [('map','선택 맵 적용'),('zoom-out','축소'),('zoom-in','확대'),('preview-focus','기본 시점'),('status','상태 읽기')]:
                    current_action_button=gr.Button(current_action_label)
                    current_action_button.click(fn=None,inputs=current_terrain_choice,outputs=current_terrain_status,queue=False,js="async(currentMapName)=>{try{return await window.terrainReviewControls('"+current_action_name+"',currentMapName);}catch(currentErrorValue){return currentErrorValue.message;}}")
            gr.Markdown('지도를 드래그해 이동하고 휠로 확대합니다. 게임 메뉴와 회전은 미리보기 안에서 사용할 수 있습니다.')
        current_terrain_timer=gr.Timer(1)
        current_terrain_timer.tick(fn=None,inputs=current_terrain_status,outputs=current_terrain_status,queue=False,show_progress='hidden',js="async(currentDisplayedStatus)=>{if(typeof window.terrainReviewControls!=='function')return {__type__:'update'};try{const currentStatusText=await window.terrainReviewControls('status');return currentStatusText===currentDisplayedStatus?{__type__:'update'}:currentStatusText;}catch(currentErrorValue){return currentErrorValue.message===currentDisplayedStatus?{__type__:'update'}:currentErrorValue.message;}}")
        current_terrain_paths=json.dumps(static_review_paths,ensure_ascii=False)
        interface_blocks_value.load(fn=None,outputs=current_terrain_controls,queue=False,js="()=>{const currentReviewPaths="+current_terrain_paths+";const currentReviewId=new URLSearchParams(location.search).get('review');return {__type__:'update',visible:(currentReviewPaths[currentReviewId]||'').split('?')[0].endsWith('terrain-layout-manager.html')};}")
        with gr.Row():
            with gr.Column(visible=False,scale=1) as current_anchor_controls:
                gr.Markdown('프레임별 기준점을 원본 픽셀 단위로 조정합니다. 정지 상태에서 미리보기를 클릭하거나 조이패드를 사용하세요. 원점은 셀 왼쪽 위이며 오른쪽은 +X, 아래는 +Y입니다. 최종 앵커 이동 시 두 발 좌표도 함께 이동합니다.')
                current_anchor_feedback=gr.Textbox(label='프레임 탐색 상태',value='애니메이션을 준비 중입니다.',interactive=False)
                with gr.Row():
                    current_animation_action=gr.Dropdown(label='애니메이션 동작',choices=[],interactive=True)
                    current_animation_read=gr.Button('동작 목록 읽기')
                    current_animation_apply=gr.Button('선택 동작 불러오기')
                current_animation_read.click(fn=None,outputs=[current_animation_action,current_anchor_feedback],queue=False,js="()=>{try{return window.anchorReviewActions(null);}catch(currentErrorValue){return [{__type__:'update'},currentErrorValue.message];}}")
                current_animation_apply.click(fn=None,inputs=current_animation_action,outputs=[current_animation_action,current_anchor_feedback],queue=False,js="currentActionIdentifier=>{try{if(!currentActionIdentifier)throw Error('동작 목록을 읽고 동작을 선택하세요.');return window.anchorReviewActions(currentActionIdentifier);}catch(currentErrorValue){return [{__type__:'update'},currentErrorValue.message];}}")
                build_frame_navigator('anchorReviewPlayback','anchorReviewSeekFrame',current_anchor_feedback)
                with gr.Row():
                    current_anchor_direction=gr.Dropdown(label='방향',choices=[],interactive=True)
                    current_anchor_point=gr.Dropdown(label='편집할 좌표',choices=[],interactive=True)
                with gr.Row():
                    current_anchor_read=gr.Button('선택 목록 읽기')
                    current_anchor_apply=gr.Button('방향·좌표 선택 적용')
                current_anchor_outputs=[current_anchor_direction,current_anchor_point,current_anchor_feedback]
                current_anchor_read.click(fn=None,outputs=current_anchor_outputs,queue=False,js="()=>{try{return window.anchorReviewSelection(null,null);}catch(currentErrorValue){return [{__type__:'update'},{__type__:'update'},currentErrorValue.message];}}")
                current_anchor_apply.click(fn=None,inputs=[current_anchor_direction,current_anchor_point],outputs=current_anchor_outputs,queue=False,js="(currentDirectionName,currentPointName)=>{try{return window.anchorReviewSelection(currentDirectionName,currentPointName);}catch(currentErrorValue){return [{__type__:'update'},{__type__:'update'},currentErrorValue.message];}}")
                build_transform_joypad('anchorReviewCoordinates',current_anchor_feedback,current_scale_enabled=False)
                with gr.Row():
                    for current_command_name,current_command_label in [('undo','실행 취소'),('redo','다시 실행'),('previous','이전 프레임 앵커 가져오기'),('reset','현재 프레임 원본 복원'),('status','좌표 변경 상태 읽기')]:
                        build_browser_action_button(current_command_label,'anchorReviewCoordinateCommands',current_command_name,current_anchor_feedback)

                with gr.Accordion('미리보기 표시',open=False):
                    gr.Markdown('앵커는 타일 중심에 고정됩니다. 표시 설정은 좌표를 변경하지 않습니다.')
                    with gr.Row():
                        current_display_fields=[gr.Checkbox(label=current_display_label,value=True) for current_display_label in ['가이드','리그 보기','가상 타일','그림자']]
                    with gr.Row():
                        current_display_read=gr.Button('표시 설정 읽기')
                        current_display_apply=gr.Button('표시 설정 적용')
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
                        current_output_read=gr.Button('출력 설정 읽기')
                        current_output_apply=gr.Button('출력 설정 적용')
                    current_output_read.click(fn=None,outputs=[*current_output_fields,current_output_feedback],queue=False,js="()=>{try{return window.anchorReviewOutputSettings(null);}catch(currentErrorValue){return [...Array.from({length:5},()=>({__type__:'update'})),currentErrorValue.message];}}")
                    current_output_apply.click(fn=None,inputs=current_output_fields,outputs=[*current_output_fields,current_output_feedback],queue=False,js="(...currentOutputValues)=>{try{return window.anchorReviewOutputSettings(currentOutputValues);}catch(currentErrorValue){return [...Array.from({length:5},()=>({__type__:'update'})),currentErrorValue.message];}}")
                    build_browser_action_button('정규화 JSON 다운로드','anchorReviewDownloadSettings','download',current_output_feedback)

                build_browser_action_button('좌표 저장','anchorReviewSaveCoordinates','save',current_anchor_feedback)

            with gr.Column(scale=2):
                with gr.Column(visible=False) as current_anchor_legend:
                    gr.Markdown('### 프레임 미리보기\n노랑: 기준선 · 청록: 발 중심 · 빨강: 최종 앵커 · 자주: 권장 신체 높이')
                gr.HTML('<section id="static-review-root" aria-label="정적 검수" aria-live="polite" aria-busy="true"><p>검수 화면을 준비하고 있습니다…</p></section>')
        with gr.Column(visible=False) as current_anchor_history:
            build_browser_history_controls('anchorReviewHistory','anchor-standard-history',current_supported_actions=('list','result','restore','reset'))

        interface_blocks_value.load(fn=None,outputs=current_anchor_controls,queue=False,js="()=>{const currentReviewPaths="+current_terrain_paths+";const currentReviewId=new URLSearchParams(location.search).get('review');return {__type__:'update',visible:(currentReviewPaths[currentReviewId]||'').split('?')[0].endsWith('/anchors.html')};}")
        interface_blocks_value.load(fn=None,outputs=current_anchor_history,queue=False,js="()=>{const currentReviewPaths="+current_terrain_paths+";const currentReviewId=new URLSearchParams(location.search).get('review');return {__type__:'update',visible:(currentReviewPaths[currentReviewId]||'').split('?')[0].endsWith('/anchors.html')};}")
        interface_blocks_value.load(fn=None,outputs=current_anchor_legend,queue=False,js="()=>{const currentReviewPaths="+current_terrain_paths+";const currentReviewId=new URLSearchParams(location.search).get('review');return {__type__:'update',visible:(currentReviewPaths[currentReviewId]||'').split('?')[0].endsWith('/anchors.html')};}")
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
    build_static_review_interface(static_review_paths).queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,js=create_static_review_loader(arguments_value.review_port,static_review_paths),allowed_paths=[])

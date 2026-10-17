"""표준 Gradio 설정과 브라우저 맵 렌더러를 연결한다."""
import argparse
import json
from pathlib import Path
import sys

import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.gradio_browser_controls import build_browser_action_button

MAP_REVIEW_CANVAS_MARKUP='''<section id="map-review-root" aria-label="맵 검수">
<h3 id="map-title">맵 검수</h3><p id="status" role="status">맵을 준비하고 있습니다…</p>
<output id="zoom-level" aria-live="polite"></output>
<div style="position:relative;aspect-ratio:4/3"><canvas id="map" width="768" height="576" tabindex="0" aria-label="맵. 방향키로 이동, 더하기와 빼기로 확대·축소, 0 키로 전체 보기" style="position:absolute;width:100%;height:100%;touch-action:none"></canvas></div>
</section>'''


def create_map_review_loader(review_server_port, current_control_count=0):
    """스타일·HTML·전역 fetch를 주입하지 않고 모듈 준비 후 선택 항목을 반환한다."""
    current_script_url=json.dumps(f'http://127.0.0.1:{review_server_port}/isloon-map-review/block-map-review.js')
    return f"""async()=>{{
try{{
 if(new URLSearchParams(location.search).get('mapKind')==='battle')return Array({6+current_control_count}).fill({{__type__:'update'}});
 if(!document.getElementById('map')||!document.getElementById('applied-tile-list'))await new Promise((resolveMapMount,rejectMapMount)=>{{
  const currentMountObserver=new MutationObserver(()=>{{if(document.getElementById('map')&&document.getElementById('applied-tile-list')){{clearTimeout(currentMountTimeout);currentMountObserver.disconnect();resolveMapMount();}}}});
  const currentMountTimeout=setTimeout(()=>{{currentMountObserver.disconnect();rejectMapMount(Error('맵 화면을 준비하지 못했습니다. 새로고침하세요.'));}},10000);
  currentMountObserver.observe(document.body,{{childList:true,subtree:true}});
 }});
 await import({current_script_url});
 if(!window.mapReviewControlOptions)throw Error('맵 초기화 실패. 맵·타일 원본 연결과 브라우저 오류를 확인하세요.');
 const currentControlOptions=window.mapReviewControlOptions();
 return [{{__type__:'update',interactive:true,choices:currentControlOptions.maps,value:currentControlOptions.selected,visible:!currentControlOptions.townSpecific}},{{__type__:'update',interactive:true,visible:!currentControlOptions.townSpecific}},{{__type__:'update',interactive:true,choices:currentControlOptions.buildings,value:null,visible:!currentControlOptions.field&&!currentControlOptions.characterReview}},{{__type__:'update',visible:currentControlOptions.field}},{{__type__:'update',visible:currentControlOptions.characterReview}},'맵을 불러왔습니다. 시점과 표시 옵션을 조정하세요.',...Array({current_control_count}).fill({{__type__:'update',interactive:true}})];
}}catch(currentLoadError){{
 const currentStatusElement=document.getElementById('status');if(currentStatusElement)currentStatusElement.textContent=currentLoadError.message;
 return [{{__type__:'update',interactive:false}},{{__type__:'update',interactive:false}},{{__type__:'update',interactive:false}},{{__type__:'update'}},{{__type__:'update'}},currentLoadError.message,...Array({current_control_count}).fill({{__type__:'update',interactive:false}})];
}}
}}"""


def capture_character_review_images(current_capture_settings):
    """GUI 설정도 CLI와 동일한 게이트웨이 명령으로 캡처한다."""
    from tools.review.common.management_client import execute_remote_management_command
    current_capture_record=execute_remote_management_command('character-review','capture',current_capture_settings)
    return list(current_capture_record['images'].values())


def build_map_review_interface(review_server_port, character_review_enabled=False):
    with gr.Blocks(title='캐릭터 표현 검수' if character_review_enabled else '맵 검수') as current_interface_blocks:
        gr.Markdown('## 캐릭터 표현 검수' if character_review_enabled else '## 맵 검수')
        current_refresh_button=gr.Button('검수 화면 새로고침')
        current_refresh_button.click(fn=None,queue=False,js="()=>{window.location.reload();}")
        if not character_review_enabled:
            current_kind_choice=gr.Radio(label='맵 종류',choices=[('야외필드','field'),('도시맵','town'),('전투필드','battle')],value='field',interactive=True)
            current_kind_choice.input(fn=None,inputs=current_kind_choice,queue=False,js="async currentMapKind=>{const currentMapUrl=new URL(location.href);currentMapUrl.searchParams.set('mapKind',currentMapKind);currentMapUrl.searchParams.delete('townPage');if(currentMapKind!=='battle'){const currentMapResponse=await fetch('http://127.0.0.1:"+str(review_server_port)+"/isloon-map-review/block-map-index.json');if(!currentMapResponse.ok)throw Error('맵 목록 조회 실패');const currentMapRecords=await currentMapResponse.json();const currentFirstMap=currentMapRecords.find(currentMapRecord=>currentMapRecord.kind===currentMapKind);if(!currentFirstMap)throw Error('등록된 맵이 없습니다.');currentMapUrl.searchParams.set('map',currentFirstMap.id);}location.assign(currentMapUrl.href);}")
            with gr.Group() as current_battle_group:
                current_battle_choice=gr.Dropdown(label='전투필드 선택',choices=[],interactive=False)
                current_battle_status=gr.Textbox(label='전투필드 로딩 상태',interactive=False)
                current_battle_choice.input(fn=None,inputs=current_battle_choice,outputs=[current_battle_choice,current_battle_status],queue=False,js="currentFieldIdentifier=>window.battlefieldReviewControls(currentFieldIdentifier)")
                gr.HTML('<section id="battle-map-review-root" aria-label="전투필드 검수"></section>')
                current_battle_timer=gr.Timer(1)
                current_battle_timer.tick(fn=None,outputs=[current_battle_choice,current_battle_status],queue=False,show_progress='hidden',js="()=>{if(typeof window.battlefieldReviewControls!=='function')return [{__type__:'update'},{__type__:'update'}];const currentBattleValues=window.battlefieldReviewControls(null);currentBattleValues[0].interactive=true;return currentBattleValues;}")
        with gr.Group() as current_surface_group:
            if character_review_enabled:
                gr.Markdown('3×3 바닥 위에서 기본 캐릭터를 비교합니다. 초기 배율은 실제 게임 크기 100%이며 오른쪽 맵을 클릭하면 양쪽 캐릭터가 함께 이동합니다.')
            with gr.Row():
                current_map_choice=gr.Dropdown(label='맵 선택',choices=[],interactive=False)
                current_load_button=gr.Button('맵 불러오기',interactive=False)
            current_camera_feedback=gr.Textbox(label='검수 안내',value='맵을 불러온 뒤 사용할 수 있습니다.',interactive=False)
            current_load_button.click(fn=None,inputs=current_map_choice,outputs=current_camera_feedback,queue=False,js="(currentMapIdentifier)=>{try{if(!window.mapReviewSelectMap)throw Error('맵을 준비 중입니다.');window.mapReviewSelectMap(currentMapIdentifier);return '맵을 불러옵니다.';}catch(currentLoadError){return currentLoadError.message;}}")
            current_ready_controls=[]
            gr.Markdown('맵 준비가 완료되면 시점·표시 옵션과 캡처를 사용할 수 있습니다. 로딩 실패 시 검수 안내를 확인하고 새로고침하세요.')
            with gr.Row():
                for current_camera_action,current_camera_label in (('zoom-out','지도 축소'),('zoom-in','지도 확대'),('actual-size','사람 중심 · 100%'),('fit','전체 보기')):
                    current_ready_controls.append(build_browser_action_button(current_camera_label,'mapReviewCameraControls',current_camera_action,current_camera_feedback,current_button_enabled=False))
            current_building_choice=gr.Dropdown(label='건물 선택',choices=[],interactive=False)
            current_building_choice.input(fn=None,inputs=current_building_choice,outputs=current_camera_feedback,queue=False,js="(currentBuildingIdentifier)=>{try{if(!window.mapReviewFocusBuilding)throw Error('맵을 준비 중입니다.');window.mapReviewFocusBuilding(currentBuildingIdentifier);return '선택한 건물로 이동했습니다.';}catch(currentFocusError){return currentFocusError.message;}}")
            with gr.Row():
                with gr.Column(min_width=200):
                    current_character_check=gr.Checkbox(interactive=False,label='기본 캐릭터',value=True)
                with gr.Column(min_width=200) as current_boundary_column:
                    current_boundary_check=gr.Checkbox(interactive=False,label='결계탑 · 결계 오러',value=True)
                with gr.Column(min_width=200):
                    current_edges_check=gr.Checkbox(interactive=False,label='메시 경계',value=False)
                with gr.Column(min_width=220,visible=character_review_enabled) as current_shadow_profile_column:
                    current_shadow_profile=gr.Dropdown(label='캐릭터 시인성 검수',choices=[('이전 기본 그림자','baseline'),('게임 적용 · 접지 대비 강화','contrast'),('넓은 접지 그림자','broad')],value='contrast',interactive=False)
            current_display_inputs=[current_character_check,current_boundary_check,current_edges_check,current_shadow_profile]
            current_ready_controls.extend(current_display_inputs)
            for current_display_control in current_display_inputs:
                current_display_control.input(fn=None,inputs=current_display_inputs,outputs=current_camera_feedback,queue=False,js="(...currentDisplayValues)=>{try{if(!window.mapReviewDisplayOptions)throw Error('맵을 준비 중입니다.');window.mapReviewDisplayOptions(...currentDisplayValues);return '표시 옵션을 적용했습니다.';}catch(currentDisplayError){return currentDisplayError.message;}}")
            if character_review_enabled:
                current_ground_preview=gr.Checkbox(interactive=False,label='바닥 대비 35% 낮추기 · 대비 65%',value=False)
                current_ground_preview.input(fn=None,inputs=current_ground_preview,outputs=current_camera_feedback,queue=False,js="(currentPreviewMode)=>{try{if(!window.mapReviewGroundPreview)throw Error('맵을 준비 중입니다.');return window.mapReviewGroundPreview(currentPreviewMode?'soft':'original');}catch(currentPreviewError){return currentPreviewError.message;}}")
                current_saturation_toggle=gr.Checkbox(interactive=False,label='바닥 채도 30% 낮추기 · 채도 70%',value=False)
                current_saturation_toggle.input(fn=None,inputs=current_saturation_toggle,outputs=current_camera_feedback,queue=False,js="(currentSaturationReduced)=>{try{if(!window.characterReviewGroundSaturation)throw Error('맵을 준비 중입니다.');return window.characterReviewGroundSaturation(currentSaturationReduced);}catch(currentSaturationError){return currentSaturationError.message;}}")
                current_brightness_toggle=gr.Checkbox(interactive=False,label='바닥 명도 30% 낮추기 · 명도 70%',value=False)
                current_brightness_toggle.input(fn=None,inputs=current_brightness_toggle,outputs=current_camera_feedback,queue=False,js="(currentBrightnessReduced)=>{try{if(!window.characterReviewGroundBrightness)throw Error('맵을 준비 중입니다.');return window.characterReviewGroundBrightness(currentBrightnessReduced);}catch(currentBrightnessError){return currentBrightnessError.message;}}")
                current_outline_preview=gr.Checkbox(interactive=False,label='어두운 형태선 · 1px' if character_review_enabled else '마을 캐릭터 1px 외곽선',value=True)
                current_outline_preview.input(fn=None,inputs=current_outline_preview,outputs=current_camera_feedback,queue=False,js="(currentOutlineEnabled)=>{try{if(!window.mapReviewOutlinePreview)throw Error('맵을 준비 중입니다.');return window.mapReviewOutlinePreview(currentOutlineEnabled);}catch(currentPreviewError){return currentPreviewError.message;}}")
                current_rim_preview=gr.Checkbox(interactive=False,label='밝은 분리선' if character_review_enabled else '마을 캐릭터 밝은 윤곽광',value=True)
                current_rim_preview.input(fn=None,inputs=current_rim_preview,outputs=current_camera_feedback,queue=False,js="(currentRimEnabled)=>{try{if(!window.mapReviewRimPreview)throw Error('맵을 준비 중입니다.');return window.mapReviewRimPreview(currentRimEnabled);}catch(currentPreviewError){return currentPreviewError.message;}}")
                current_ready_controls.extend([current_ground_preview,current_saturation_toggle,current_brightness_toggle,current_outline_preview,current_rim_preview])
            if character_review_enabled:
                current_shadow_check=gr.Checkbox(interactive=False,label='접지 그림자',value=True)
                current_ready_controls.append(current_shadow_check)
                current_shadow_check.input(fn=None,inputs=current_shadow_check,outputs=current_camera_feedback,queue=False,js="(currentShadowEnabled)=>{try{if(!window.characterReviewContactShadow)throw Error('맵을 준비 중입니다.');return window.characterReviewContactShadow(currentShadowEnabled);}catch(currentShadowError){return currentShadowError.message;}}")
            gr.Markdown('바닥·측벽·계단 타일 원본: 128×128 · '+('바닥 흐림 없음' if character_review_enabled else '게임 공용 렌더러 · 원본 채도 · 바닥 흐림 없음')+' · 캐릭터·건물 해상도 유지')
            if character_review_enabled:
                current_ground_choice=gr.Radio(interactive=False,label='검수 바닥',choices=[('석판','paving'),('잔디·들꽃','grass'),('흙·자갈','meadow-road')],value='paving')
                current_ready_controls.append(current_ground_choice)
                current_ground_choice.input(fn=None,inputs=current_ground_choice,outputs=current_camera_feedback,queue=False,js="(currentTextureIdentifier)=>{try{if(!window.characterReviewGroundTile)throw Error('맵을 준비 중입니다.');return window.characterReviewGroundTile(currentTextureIdentifier);}catch(currentTextureError){return currentTextureError.message;}}")
                with gr.Row(equal_height=True):
                    with gr.Column(min_width=280):
                        gr.Markdown('### 원본 · 현재 게임 렌더링 설정')
                        gr.HTML('<div style="position:relative;aspect-ratio:4/3"><canvas id="character-baseline-map" width="768" height="576" aria-label="원본 캐릭터 비교 맵" style="position:absolute;width:100%;height:100%"></canvas></div>')
                    with gr.Column(min_width=280):
                        gr.Markdown('### 조정본 · 선택한 표현 적용')
                        gr.HTML(MAP_REVIEW_CANVAS_MARKUP.replace('<h3 id="map-title">맵 검수</h3><p id="status" role="status">맵을 준비하고 있습니다…</p>\n<output id="zoom-level" aria-live="polite"></output>','').replace('id="map"','id="map" data-character-review="true"'))
                gr.HTML('<h3 id="map-title">캐릭터 표현 검수</h3><p id="status" role="status">맵을 준비하고 있습니다…</p><output id="zoom-level" aria-live="polite"></output>')
            else:
                gr.HTML(MAP_REVIEW_CANVAS_MARKUP)
            if character_review_enabled:
                gr.Markdown('PNG 캡처는 현재 바닥·캐릭터 위치·표현 설정을 배율 200%, 표시 영역 768×576에서 내부 해상도 2배인 1536×1152 PNG로 렌더링합니다. 원본·조정본·좌우 비교 3개 파일을 저장합니다.')
                current_capture_settings=gr.JSON(value={},visible=False)
                current_capture_button=gr.Button('렌더링 PNG 캡처',interactive=False)
                current_ready_controls.append(current_capture_button)
                current_capture_files=gr.File(label='캡처 결과 · 원본 / 조정본 / 비교',file_count='multiple',interactive=False)
                current_capture_button.click(fn=None,inputs=None,outputs=current_capture_settings,queue=False,js="()=>{if(!window.characterReviewCaptureSettings)throw Error('맵을 준비 중입니다.');return window.characterReviewCaptureSettings();}").then(fn=capture_character_review_images,inputs=current_capture_settings,outputs=current_capture_files)
            with gr.Accordion('조작 방법 · 타일 안내',open=False):
                gr.Markdown('휠 또는 확대·축소 버튼으로 배율을 조절하고 드래그 또는 방향키로 이동합니다. 0 키는 전체 보기입니다. 맵은 고정 시점이며 회전하지 않습니다. 이동 가능한 바닥을 클릭하면 기본 캐릭터를 배치합니다. 캐릭터를 가리는 앞쪽 빌보드·지형은 원래 불투명도의 40%로 표시되며, 가림이 없어지면 복원됩니다. 맵에 포커스를 둔 뒤 Shift+좌우로 캐릭터 열, Shift+상하로 행을 이동합니다. 메시 경계는 지면·절벽 면의 꼭짓점을 표시합니다. 미등록 지형은 임시 색상으로 표시됩니다.')
            with gr.Accordion('적용 타일 원본',open=True):
                gr.HTML('<ul id="applied-tile-list" aria-live="polite"></ul>')
            current_interface_blocks.load(fn=None,outputs=[current_map_choice,current_load_button,current_building_choice,current_boundary_column,current_shadow_profile_column,current_camera_feedback,*current_ready_controls],js=create_map_review_loader(review_server_port,len(current_ready_controls)),queue=False)
        if not character_review_enabled:
            current_native_loader=Path(__file__).with_name('game_native_loader.js').read_text()
            current_mode_script="""async()=>{
__NATIVE_LOADER__
const currentQueryValues=new URLSearchParams(location.search),currentBattleMode=currentQueryValues.get('mapKind')==='battle';
if(currentBattleMode){
 const currentSourceResponse=await fetch('http://127.0.0.1:__PORT__/manager-source.json',{cache:'no-store'});
 if(!currentSourceResponse.ok)throw Error('검수 목록 조회 실패');
 const currentSourceRecord=await currentSourceResponse.json();
 const currentBattleRecord=currentSourceRecord.pages.find(currentPageRecord=>currentPageRecord.path.split('?')[0].endsWith('/battlefield-preview.html'));
 if(!currentBattleRecord)throw Error('전투필드 검수 번들이 없습니다.');
 const currentBattleUrl=new URL(currentBattleRecord.path,'http://127.0.0.1:__PORT__/');
 currentBattleUrl.searchParams.set('field',currentQueryValues.get('field')||'meadow-crossroads');
 if(!document.getElementById('battle-map-review-root'))await new Promise((resolveBattleMount,rejectBattleMount)=>{const currentBattleObserver=new MutationObserver(()=>{if(document.getElementById('battle-map-review-root')){clearTimeout(currentMountTimeout);currentBattleObserver.disconnect();resolveBattleMount();}});const currentMountTimeout=setTimeout(()=>{currentBattleObserver.disconnect();rejectBattleMount(Error('전투필드 화면 준비 실패'));},10000);currentBattleObserver.observe(document.body,{childList:true,subtree:true});});
 await mountNativeGameReview(document.getElementById('battle-map-review-root'),currentBattleUrl);
}
return [{__type__:'update',visible:!currentBattleMode},{__type__:'update',visible:currentBattleMode},{__type__:'update',value:currentQueryValues.get('mapKind')||(currentQueryValues.get('category')==='town-map-review'?'town':'field')}];
}""".replace('__NATIVE_LOADER__',current_native_loader).replace('__PORT__',str(review_server_port))
            current_interface_blocks.load(fn=None,outputs=[current_surface_group,current_battle_group,current_kind_choice],queue=False,js=current_mode_script)
    return current_interface_blocks


from tools.review.ui.gradio.management_menu_app import compose_management_interface

if __name__=='__main__':
    current_argument_parser=argparse.ArgumentParser()
    current_argument_parser.add_argument('--port',type=int,required=True)
    current_argument_parser.add_argument('--review-port',type=int,required=True)
    current_argument_parser.add_argument('--owner-pid',type=int,required=True)
    current_argument_parser.add_argument('--root-path',default='/management/frame/map-review/')
    current_argument_values=current_argument_parser.parse_args()
    compose_management_interface(build_map_review_interface(current_argument_values.review_port),current_argument_values.review_port).queue().launch(server_name='127.0.0.1',server_port=current_argument_values.port,root_path=current_argument_values.root_path,allowed_paths=[])

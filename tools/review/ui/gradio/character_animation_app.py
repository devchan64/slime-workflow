"""공용 게이트웨이를 사용하는 캐릭터 애니메이션 Gradio 클라이언트."""
import argparse
import html
import json
import math
import os
from pathlib import Path
import sys
import threading
import time

import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.gradio_logs import build_execution_logs, LOG_PANEL_STYLES
from tools.review.common.gradio_history import HISTORY_CARD_SELECTION_SCRIPT, build_generation_history_view
from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
from tools.review.common.management_client import execute_remote_management_command as execute_management_command

from tools.review.domains.character_animation.character_animation_assets import compose_direction_prompts

DIRECTION_LABEL_VALUES=[('전방 좌측','down_left'),('전방 우측','down_right'),('후방 좌측','up_left'),('후방 우측','up_right')]

def execute_animation_gateway(command_name_value, payload_value):
    return execute_management_command('character-animation',command_name_value,payload_value)

def read_animation_catalog():
    return execute_animation_gateway('catalog',{})

def format_unavailable_asset_notice(catalog_record_value):
    unavailable_asset_records = catalog_record_value.get('unavailable_assets',[])
    if not unavailable_asset_records:
        return ''
    notice_lines = ['### 일부 등록 자산을 사용할 수 없습니다', '파일이 교체·삭제된 자산은 선택지에서 제외했습니다. 자산을 복구하거나 설정을 갱신하면 다음 새로고침부터 다시 표시됩니다.']
    for asset_record_value in unavailable_asset_records:
        asset_kind_label = '모션' if asset_record_value['kind']=='motion' else '캐릭터'
        notice_lines.append(f"- **{asset_kind_label} · {asset_record_value['label']}**: {asset_record_value['reason']}")
    return '\n\n'.join(notice_lines)

def select_motion_prompt_values(catalog_record_value, selected_motion_name):
    selected_motion_record=next(record for record in catalog_record_value['motions'] if record['id']==selected_motion_name)
    return selected_motion_record['prompts']

def describe_motion_prompt_words(catalog_record_value, selected_motion_name, *direction_prompt_values):
    selected_prompt_values=select_motion_prompt_values(catalog_record_value,selected_motion_name)
    auxiliary_prompt_values={direction_name_value:prompt_text_value for (_,direction_name_value),prompt_text_value in zip(DIRECTION_LABEL_VALUES,direction_prompt_values)}
    final_prompt_records=compose_direction_prompts(selected_prompt_values,auxiliary_prompt_values)
    summary_line_values=[f"기본 {len(selected_prompt_values['base'].split())}단어 · 전방 공통 보조 {len(selected_prompt_values['auxiliary'].split())}단어 · 후방 공통 보조 {len(selected_prompt_values['auxiliary_rear'].split())}단어"]
    for direction_label_text,direction_name_value in DIRECTION_LABEL_VALUES:
        extra_prompt_words=len(auxiliary_prompt_values.get(direction_name_value,'').split())
        summary_line_values.append(f"{direction_label_text}: 추가 보조 {extra_prompt_words}단어 · 최종 {final_prompt_records[direction_name_value]['words']}단어")
    return '  \n'.join(summary_line_values)

def build_animation_request(motion_name_value,character_name_value,source_name_value,direction_name_values,start_frame_value,end_frame_value,resolution_value,step_value,target_fps_value,speed_value,generation_tag_value,*direction_prompt_values):
    return {'motion':motion_name_value,'character':character_name_value,'source':source_name_value,'directions':direction_name_values,'start_frame':start_frame_value,'end_frame':end_frame_value,'resolution':resolution_value,'steps':step_value,'target_fps':target_fps_value,'speed':speed_value,'tag':generation_tag_value.strip(),'direction_auxiliary_prompts':{direction: text for (_,direction),text in zip(DIRECTION_LABEL_VALUES,direction_prompt_values or ['']*4)}}

def restore_animation_inputs(current_history_record):
    current_request_record=current_history_record.get('request',{})
    return current_request_record.get('motion'),current_request_record.get('character'),current_request_record.get('source','anny'),current_request_record.get('directions',[]),current_request_record.get('start_frame',1),current_request_record.get('end_frame'),current_request_record.get('resolution',512),current_request_record.get('steps',4),8,(current_request_record.get('speed',2) if current_request_record.get('target_fps') == 8 and current_request_record.get('speed',2) in (1,2,4) else 2),current_request_record.get('tag',''),*[current_request_record.get('direction_auxiliary_prompts',{}).get(direction,'') for _,direction in DIRECTION_LABEL_VALUES],'선택한 이력의 입력값을 불러왔습니다. 이전 FPS·미지원 배속 이력은 신규 생성 기준 8 FPS·2배로 설정합니다. 생성 전에 내용을 확인하세요.'

def calculate_preview_frame_numbers(selected_start_frame,selected_end_frame,source_frame_rate,target_frame_rate,generation_speed_ratio):
    if type(target_frame_rate) is not int or target_frame_rate != 8:
        raise ValueError('타겟 FPS는 8만 지원합니다.')
    if type(generation_speed_ratio) not in (int,float) or generation_speed_ratio not in (1,2,4):
        raise ValueError('생성 배속은 1·2·4 중 하나여야 합니다.')
    selected_range_frame_count=selected_end_frame-selected_start_frame+1
    selected_frame_count=math.ceil(selected_range_frame_count/generation_speed_ratio)
    return [selected_start_frame+math.floor(frame_index_value*generation_speed_ratio) for frame_index_value in range(selected_frame_count)]


def clamp_selected_frame_range(selected_start_frame,selected_end_frame,maximum_frame_number):
    normalized_start_frame=selected_start_frame if type(selected_start_frame) is int else 1
    normalized_end_frame=selected_end_frame if type(selected_end_frame) is int else maximum_frame_number
    normalized_start_frame=max(1,min(normalized_start_frame,maximum_frame_number))
    normalized_end_frame=max(normalized_start_frame,min(normalized_end_frame,maximum_frame_number))
    return normalized_start_frame,normalized_end_frame

def create_motion_preview_player(selected_motion_name,selected_source_kind,selected_direction_name,selected_start_frame,selected_end_frame,source_frame_rate,target_frame_rate,generation_speed_ratio,server_base_address):
    if type(selected_start_frame) is not int or type(selected_end_frame) is not int or selected_start_frame > selected_end_frame:
        return '<div>시작 프레임과 종료 프레임을 확인하세요.</div>'
    selected_frame_numbers=calculate_preview_frame_numbers(selected_start_frame,selected_end_frame,source_frame_rate,target_frame_rate,generation_speed_ratio)
    frame_url_values=[f'{server_base_address}/character-animation/asset/{selected_motion_name}/{selected_source_kind}/{selected_direction_name}/{frame_number}' for frame_number in selected_frame_numbers]
    player_payload_value={'frames':frame_url_values,'sourceFrames':selected_frame_numbers,'fps':target_frame_rate}
    player_source_text='''<!doctype html><meta charset="utf-8"><style>*{box-sizing:border-box}body{margin:8px;background:#10151f;color:#e5e7eb;font:14px sans-serif}button,input{padding:8px;background:#243449;color:inherit;border:1px solid #526078;border-radius:6px}button:disabled{opacity:.45;cursor:not-allowed}nav{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}img{width:min(100%,720px);max-height:440px;object-fit:contain;background:#000}#seek{width:min(100%,720px)}</style><nav><button id="load">미리보기 불러오기</button><button id="previous">이전</button><button id="play" disabled>재생</button><button id="stop">중지</button><button id="next">다음</button></nav><img hidden id="frame" alt="입력 포즈 프레임"><p id="count">미리보기 불러오기를 누르면 선택 프레임을 준비합니다.</p><input hidden id="seek" type="range" min="0" value="0"><script>const data=__PAYLOAD__,$=id=>document.getElementById(id),cache=[],ready=[];let i=0,t=null,next=0,loading=0,prepared=0,failed=0;function update(){const total=prepared+failed;$('count').textContent='미리보기 준비 '+total+' / '+data.frames.length+' 프레임'+(failed?' · '+failed+'개 실패':'');if(total===data.frames.length){$('play').disabled=failed>0;draw()}}function preloadNext(){while(loading<4&&next<data.frames.length){const index=next++,image=new Image();cache[index]=image;loading++;image.onload=()=>{ready[index]=true;prepared++;loading--;update();preloadNext()};image.onerror=()=>{ready[index]=false;failed++;loading--;update();preloadNext()};image.src=data.frames[index]}}function draw(){const frame=i;if(!ready[frame]){$('count').textContent='원본 프레임 '+data.sourceFrames[frame]+' 준비 중입니다.';return}$('frame').hidden=false;$('seek').hidden=false;$('frame').src=cache[frame].src;$('count').textContent='원본 프레임 '+data.sourceFrames[frame]+' · '+(frame+1)+' / '+data.frames.length;$('seek').value=frame;$('seek').max=data.frames.length-1}function stop(){clearInterval(t);t=null}function step(n){i=(i+n+data.frames.length)%data.frames.length;draw()}$('load').onclick=()=>{$('load').disabled=true;preloadNext()};$('previous').onclick=()=>{stop();step(-1)};$('next').onclick=()=>{stop();step(1)};$('stop').onclick=stop;$('play').onclick=()=>{if($('play').disabled)return;stop();t=setInterval(()=>step(1),1000/data.fps)};$('seek').oninput=()=>{stop();i=+$('seek').value;draw()};new ResizeObserver(()=>{if(window.frameElement)window.frameElement.style.height=(document.body.getBoundingClientRect().height+16)+'px'}).observe(document.body)</script>'''.replace('__PAYLOAD__',json.dumps(player_payload_value).replace('<','\\u003c'))
    return '<iframe title="입력 포즈 미리보기" style="width:100%;height:100px;border:0" sandbox="allow-scripts allow-same-origin" srcdoc="'+html.escape(player_source_text,quote=True)+'"></iframe>'

def create_animation_player(generation_job_identifier,generation_status_record,server_base_address):
    result_record_value=generation_status_record.get('result') or {}
    frame_values=result_record_value.get('frames',{})
    player_payload_value={'id':generation_job_identifier,'frames':frame_values,'fps':result_record_value.get('fps',4),'base':server_base_address}
    player_source_text='''<!doctype html><meta charset="utf-8"><style>body{margin:8px;background:#10151f;color:#e5e7eb;font:14px sans-serif}button,select,input{padding:8px;background:#243449;color:inherit;border:1px solid #526078;border-radius:6px}nav{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}img{width:min(100%,720px);min-height:240px;max-height:560px;object-fit:contain;background:#000}#seek{width:min(100%,720px)}</style><nav><select id="direction"></select><button id="previous">이전</button><button id="play">재생</button><button id="stop">중지</button><button id="next">다음</button><select id="fps"><option>4</option><option>8</option><option>12</option><option>16</option></select></nav><img id="frame" alt="생성 결과 프레임"><p id="count">이미지를 불러오는 중입니다.</p><input id="seek" type="range" min="0" value="0"><script>const data=__PAYLOAD__,$=id=>document.getElementById(id),names={down_left:'전방 좌측',down_right:'전방 우측',up_left:'후방 좌측',up_right:'후방 우측'};let i=0,t=null,request=0;for(const d of Object.keys(data.frames))$('direction').add(new Option(names[d]||d,d));function draw(){const f=data.frames[$('direction').value]||[];if(!f.length){$('count').textContent='표시할 결과 프레임이 없습니다.';return}$('seek').max=f.length-1;i=Math.min(i,f.length-1);const current=++request,frame=i,pending=new Image();$('count').textContent=(frame+1)+' / '+f.length+' 프레임 · 이미지를 불러오는 중';pending.onload=()=>{if(current!==request)return;$('frame').src=pending.src;$('count').textContent=(frame+1)+' / '+f.length+' 프레임';$('seek').value=frame};pending.onerror=()=>{if(current===request)$('count').textContent=(frame+1)+' / '+f.length+' 프레임 이미지를 불러오지 못했습니다.'};pending.src=data.base+'/character-animation/files/'+data.id+'/'+f[frame]}function stop(){clearInterval(t);t=null}function step(n){const f=data.frames[$('direction').value]||[];if(!f.length)return;i=(i+n+f.length)%f.length;draw()}$('previous').onclick=()=>{stop();step(-1)};$('next').onclick=()=>{stop();step(1)};$('stop').onclick=stop;$('play').onclick=()=>{stop();t=setInterval(()=>step(1),1000/+$('fps').value)};$('fps').onchange=()=>{if(t)$('play').click()};$('direction').onchange=()=>{i=0;draw()};$('seek').oninput=()=>{stop();i=+$('seek').value;draw()};draw()</script>'''.replace('__PAYLOAD__',json.dumps(player_payload_value).replace('<','\\u003c'))
    return '<iframe title="캐릭터 애니메이션 결과 재생" style="width:100%;height:680px;border:0" sandbox="allow-scripts allow-same-origin" srcdoc="'+html.escape(player_source_text,quote=True)+'"></iframe>'

def build_character_baseline_preview(selected_character_identifier, server_base_address):
    """생성 입력과 동일한 등록 신체 베이스를 4방향으로 표시한다."""
    from urllib.parse import urlencode
    if not selected_character_identifier:
        return '<p>캐릭터를 선택하세요.</p>'
    preview_card_values = []
    for current_frame_number, (current_direction_label, current_direction_name) in enumerate(DIRECTION_LABEL_VALUES, 1):
        current_query_string = urlencode({'source_id': 'workflow:' + selected_character_identifier, 'frame': current_frame_number})
        current_image_address = server_base_address + '/animation-separation/source-preview?' + current_query_string
        preview_card_values.append('<figure style="margin:0;flex:1;min-width:120px"><img style="width:100%;max-height:240px;object-fit:contain" src="' + html.escape(current_image_address, quote=True) + '" alt="' + current_direction_label + ' 신체 베이스"><figcaption>' + current_direction_label + '</figcaption></figure>')
    return '<section><h3>선택한 신체 베이스라인 · 4방향</h3><div style="display:flex;flex-wrap:wrap;gap:8px">' + ''.join(preview_card_values) + '</div></section>'


def build_character_animation_interface(server_base_address):
    catalog_record_value=read_animation_catalog()
    motion_choice_values=[(record['label'],record['id']) for record in catalog_record_value['motions']]
    character_choice_values=[(record['label'],record['id']) for record in catalog_record_value['characters']]
    motion_catalog_records={record['id']:record for record in catalog_record_value['motions']}
    motion_frame_count_values={motion_identifier_value:motion_record_value['frames'] for motion_identifier_value,motion_record_value in motion_catalog_records.items()}
    def restore_registered_animation_inputs(current_history_record):
        restored_input_values=list(restore_animation_inputs(current_history_record))
        if restored_input_values[0] not in motion_frame_count_values:
            raise gr.Error('폐기된 모션의 입력은 복원할 수 없습니다. 등록된 모션을 선택하세요.')
        selected_frame_count=motion_frame_count_values[restored_input_values[0]]
        restored_start_frame,restored_end_frame=clamp_selected_frame_range(restored_input_values[4],restored_input_values[5],selected_frame_count)
        restored_input_values[4]=gr.update(value=restored_start_frame,maximum=selected_frame_count)
        restored_input_values[5]=gr.update(value=restored_end_frame,maximum=selected_frame_count)
        return restored_input_values

    with gr.Blocks(title='캐릭터 애니메이션 생성기',js=HISTORY_CARD_SELECTION_SCRIPT) as interface_blocks_value:
        gr.Markdown('## 캐릭터 애니메이션 생성기\n등록된 모션과 캐릭터 레퍼런스로 방향별 프레임을 생성합니다.')
        unavailable_asset_notice = format_unavailable_asset_notice(catalog_record_value)
        if unavailable_asset_notice:
            gr.Markdown(unavailable_asset_notice)
        if not motion_choice_values or not character_choice_values:
            missing_asset_kind_values = []
            if not motion_choice_values:missing_asset_kind_values.append('모션')
            if not character_choice_values:missing_asset_kind_values.append('캐릭터')
            gr.Markdown('> ⚠️ 사용할 수 있는 '+ '·'.join(missing_asset_kind_values) +' 자산이 없어 새 생성을 시작할 수 없습니다. 위 안내를 확인한 뒤 자산 또는 등록 설정을 갱신하세요.')
            return interface_blocks_value
        with gr.Column(elem_classes=['character-animation-workspace']):
            with gr.Column():
                gr.Markdown('### 생성 설정')
                with gr.Row():
                    motion_select_value=gr.Dropdown(motion_choice_values,value=motion_choice_values[0][1],label='모션')
                    character_select_value=gr.Dropdown(character_choice_values,value=character_choice_values[0][1],label='캐릭터')
                character_preview_value=gr.HTML(build_character_baseline_preview(character_choice_values[0][1],server_base_address))
                character_select_value.change(lambda selected_character_identifier: build_character_baseline_preview(selected_character_identifier,server_base_address),character_select_value,character_preview_value,queue=False)
                with gr.Row():
                    source_select_value=gr.Radio([('ANNY','anny'),('OpenPose','openpose')],value='anny',label='포즈 입력')
                    direction_select_value=gr.CheckboxGroup(DIRECTION_LABEL_VALUES,value=[value for _,value in DIRECTION_LABEL_VALUES],label='생성 방향')
                initial_motion_frame_count=motion_frame_count_values[motion_choice_values[0][1]]
                with gr.Row():
                    start_frame_value=gr.Slider(value=1,minimum=1,maximum=initial_motion_frame_count,step=1,label='시작 프레임',elem_classes=['management-frame-slider'])
                    end_frame_value=gr.Slider(value=initial_motion_frame_count,minimum=1,maximum=initial_motion_frame_count,step=1,label='종료 프레임',elem_classes=['management-frame-slider'])
                with gr.Row():
                    resolution_select_value=gr.Dropdown([512,768,1024,1280],value=512,label='해상도')
                    step_select_value=gr.Radio([4,30],value=4,label='생성 스텝')
                with gr.Row():
                    target_fps_select_value=gr.Dropdown([8],value=8,label='타겟 FPS',info='재생은 8 FPS 고정입니다. 생성 배속 2는 원본 1·3·5… 프레임을 선택합니다.')
                    speed_select_value=gr.Dropdown([1,2,4],value=2,label='생성 배속')
                generation_tag_value=gr.Textbox(label='생성 이력 태그 · 선택 사항',placeholder='예: 돌온재 걷기 후보',max_lines=1)
                prompt_text_value=gr.Textbox(value=select_motion_prompt_values(catalog_record_value,motion_choice_values[0][1])['base'],label='선택 모션의 고정 기본 프롬프트',interactive=False,lines=4)
                reset_base_prompt_button=gr.Button('기본 프롬프트 초기화',size='sm')
                with gr.Accordion('방향별 보조 프롬프트 · 선택 사항',open=False):
                    gr.Markdown('비워 두면 추가 지시 없이 생성합니다. 입력한 내용은 해당 방향의 고정 프롬프트 뒤에 추가됩니다.')
                    direction_prompt_components=[]
                    for direction_label_text,direction_name_value in DIRECTION_LABEL_VALUES:
                        direction_prompt_components.append(gr.Textbox(value=motion_catalog_records[motion_choice_values[0][1]].get('direction_auxiliary_prompts',{}).get(direction_name_value,''),label=direction_label_text+' 보조 프롬프트',lines=2))
                    reset_auxiliary_prompt_button=gr.Button('보조 프롬프트 초기화',size='sm')
                    gr.Markdown('초기화하면 선택한 모션의 기본 보조 문구로 복원합니다. 기본 문구가 없으면 빈 값으로 복원합니다.')
                prompt_word_count_value=gr.Markdown(describe_motion_prompt_words(catalog_record_value,motion_choice_values[0][1],*[motion_catalog_records[motion_choice_values[0][1]].get('direction_auxiliary_prompts',{}).get(direction,'') for _,direction in DIRECTION_LABEL_VALUES]))
                def reset_base_prompt_value(selected_motion_name):
                    return select_motion_prompt_values(read_animation_catalog(),selected_motion_name)['base']
                def reset_auxiliary_prompt_values(selected_motion_name):
                    current_catalog_record=read_animation_catalog()
                    selected_motion_record=next(record for record in current_catalog_record['motions'] if record['id']==selected_motion_name)
                    return [selected_motion_record.get('direction_auxiliary_prompts',{}).get(direction,'') for _,direction in DIRECTION_LABEL_VALUES]
                reset_base_prompt_button.click(reset_base_prompt_value,inputs=motion_select_value,outputs=prompt_text_value,queue=False)
                reset_auxiliary_prompt_button.click(reset_auxiliary_prompt_values,inputs=motion_select_value,outputs=direction_prompt_components,queue=False)
            with gr.Accordion('입력 포즈 미리보기',open=False):
                preview_direction_value=gr.Dropdown(DIRECTION_LABEL_VALUES,value='down_left',label='미리보기 방향')
                generation_identifier_value=gr.State('')
                initial_motion_record=motion_catalog_records[motion_choice_values[0][1]]
                motion_preview_html_value=gr.HTML(create_motion_preview_player(motion_choice_values[0][1],'anny','down_left',1,initial_motion_frame_count,initial_motion_record['fps'],8,2,server_base_address))
            generation_pending_value=gr.State(False)
            generation_button_value=gr.Button('애니메이션 생성 시작',variant='primary',elem_id='character-generation-start')
            status_text_value=gr.Markdown('생성 가능 · 설정을 확인하세요.')
        logs_text_value,log_refresh_enabled,_=build_execution_logs()
        read_history_page,history_output_values=build_generation_history_view(execute_animation_gateway,server_base_address,'이력 목록만 초기화합니다. 생성 프레임과 로그 파일은 유지됩니다. 생성 중에는 초기화할 수 없습니다.',restore_input_callback=restore_registered_animation_inputs,restore_output_components=[motion_select_value,character_select_value,source_select_value,direction_select_value,start_frame_value,end_frame_value,resolution_select_value,step_select_value,target_fps_select_value,speed_select_value,generation_tag_value,*direction_prompt_components,status_text_value],result_renderer_callback=create_animation_player,record_folder_route='/character-animation',allow_individual_delete=True)
        def start_animation(*selection_values):
            yield gr.skip(),'생성 요청을 접수하고 있습니다.',gr.update(interactive=False,value='요청 접수 중…'),True
            try:
                request_payload_value=build_animation_request(*selection_values)
                generation_record_value=execute_animation_gateway('generate',request_payload_value)
                yield generation_record_value['id'],'작업을 접수했습니다. 추가 생성은 확인 후 대기열에 등록됩니다.',gr.update(interactive=True,value='대기열에 추가'),False
            except Exception as generation_request_error:
                yield gr.skip(),'생성 요청 실패: '+str(generation_request_error),gr.update(interactive=True,value='애니메이션 생성 시작'),False
        bind_gpu_generation_confirmation(generation_button_value,start_animation,[motion_select_value,character_select_value,source_select_value,direction_select_value,start_frame_value,end_frame_value,resolution_select_value,step_select_value,target_fps_select_value,speed_select_value,generation_tag_value,*direction_prompt_components],[generation_identifier_value,status_text_value,generation_button_value,generation_pending_value])
        def change_motion_range(selected_motion_name,selected_source_kind,selected_direction_name,selected_target_frame_rate,selected_speed_ratio,current_start_frame,current_end_frame):
            selected_motion_record=motion_catalog_records[selected_motion_name]
            selected_frame_count=selected_motion_record['frames']
            restored_start_frame,restored_end_frame=1,selected_frame_count
            return gr.update(value=restored_start_frame,maximum=selected_frame_count),gr.update(value=restored_end_frame,maximum=selected_frame_count),create_motion_preview_player(selected_motion_name,selected_source_kind,selected_direction_name,restored_start_frame,restored_end_frame,selected_motion_record['fps'],selected_target_frame_rate,selected_speed_ratio,server_base_address)
        def refresh_motion_preview(selected_motion_name,selected_source_kind,selected_direction_name,selected_start_frame,selected_end_frame,selected_target_frame_rate,selected_speed_ratio):
            return create_motion_preview_player(selected_motion_name,selected_source_kind,selected_direction_name,selected_start_frame,selected_end_frame,motion_catalog_records[selected_motion_name]['fps'],selected_target_frame_rate,selected_speed_ratio,server_base_address)
        preview_component_values=[motion_select_value,source_select_value,preview_direction_value,start_frame_value,end_frame_value,target_fps_select_value,speed_select_value]
        motion_select_value.input(change_motion_range,[motion_select_value,source_select_value,preview_direction_value,target_fps_select_value,speed_select_value,start_frame_value,end_frame_value],[start_frame_value,end_frame_value,motion_preview_html_value],queue=False)
        motion_select_value.input(lambda motion: [motion_catalog_records[motion].get('direction_auxiliary_prompts',{}).get(direction,'') for _,direction in DIRECTION_LABEL_VALUES],motion_select_value,direction_prompt_components,queue=False)
        motion_select_value.change(lambda selected_motion_name: select_motion_prompt_values(catalog_record_value,selected_motion_name)['base'],motion_select_value,prompt_text_value,queue=False)
        for prompt_input_component in [motion_select_value,*direction_prompt_components]:
            prompt_input_component.change(lambda selected_motion_name,*direction_prompt_values: describe_motion_prompt_words(catalog_record_value,selected_motion_name,*direction_prompt_values),[motion_select_value,*direction_prompt_components],prompt_word_count_value,queue=False)
        for preview_input_value in (source_select_value,preview_direction_value,start_frame_value,end_frame_value,target_fps_select_value,speed_select_value):
            preview_input_value.change(refresh_motion_preview,preview_component_values,motion_preview_html_value,queue=False)
        interface_blocks_value.load(lambda:read_history_page(1),outputs=history_output_values)
        def refresh_status(identifier,refresh_logs,request_pending):
            if request_pending:return gr.skip(),gr.skip(),gr.skip()
            if not identifier:return '생성 가능 · 설정을 확인하세요.',gr.skip(),gr.update(interactive=True,value='애니메이션 생성 시작')
            status_record_value=execute_animation_gateway('status',{'id':identifier})
            return '상태: '+status_record_value['status'],gr.update(value=status_record_value['log']) if refresh_logs else gr.skip(),gr.update(interactive=True,value='대기열에 추가' if status_record_value['status'] in ('running','queued') else '애니메이션 생성 시작')
        refresh_button_value=gr.Button('상태 새로고침')
        refresh_button_value.click(refresh_status,[generation_identifier_value,log_refresh_enabled,generation_pending_value],[status_text_value,logs_text_value,generation_button_value],queue=False)
        if hasattr(gr,'Timer'):gr.Timer(2).tick(refresh_status,[generation_identifier_value,log_refresh_enabled,generation_pending_value],[status_text_value,logs_text_value,generation_button_value],show_progress='hidden')
    return interface_blocks_value

from pathlib import Path as ManagementStylePath
MANAGEMENT_DENSITY_STYLES=(ManagementStylePath(__file__).parents[1]/'shared/management-density.css').read_text()
MANAGEMENT_SHARED_STYLES=(ManagementStylePath(__file__).parents[1]/'shared/management.css').read_text()+MANAGEMENT_DENSITY_STYLES

if __name__=='__main__':
    parser_value=argparse.ArgumentParser();parser_value.add_argument('--port',type=int,required=True);parser_value.add_argument('--review-port',type=int,required=True);parser_value.add_argument('--owner-pid',type=int,required=True);parser_value.add_argument('--root-path',default='/character-animation/');arguments_value=parser_value.parse_args()
    def monitor_parent_process():
        while os.getppid()==arguments_value.owner_pid:time.sleep(1)
        os._exit(0)
    threading.Thread(target=monitor_parent_process,daemon=True).start()
    build_character_animation_interface(f'http://127.0.0.1:{arguments_value.review_port}').queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,theme=gr.themes.Soft(),css=LOG_PANEL_STYLES+MANAGEMENT_SHARED_STYLES,allowed_paths=[])

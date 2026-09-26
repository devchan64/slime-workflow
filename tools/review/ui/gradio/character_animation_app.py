"""공용 게이트웨이를 사용하는 캐릭터 애니메이션 Gradio 클라이언트."""
import argparse
import html
import json
import os
from pathlib import Path
import sys
import threading
import time

import gradio as gr

WORKFLOW_ROOT_DIRECTORY=Path(__file__).resolve().parents[4]
if str(WORKFLOW_ROOT_DIRECTORY) not in sys.path:sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.gradio_logs import build_execution_logs, LOG_PANEL_STYLES
from tools.review.common.gradio_history import build_generation_history_view
from tools.review.common.management_gateway import execute_management_command

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

def build_animation_request(motion_name_value,character_name_value,source_name_value,direction_name_values,resolution_value,step_value,target_fps_value,speed_value):
    return {'motion':motion_name_value,'character':character_name_value,'source':source_name_value,'directions':direction_name_values,'resolution':resolution_value,'steps':step_value,'target_fps':target_fps_value,'speed':speed_value}

def restore_animation_inputs(current_history_record):
    current_request_record=current_history_record.get('request',{})
    return current_request_record.get('motion'),current_request_record.get('character'),current_request_record.get('source','openpose'),current_request_record.get('directions',[]),current_request_record.get('resolution',512),current_request_record.get('steps',4),current_request_record.get('target_fps',4),current_request_record.get('speed',1),'선택한 이력의 입력값을 불러왔습니다. 생성 전에 내용을 확인하세요.'

def create_animation_player(generation_job_identifier,generation_status_record,server_base_address):
    result_record_value=generation_status_record.get('result') or {}
    frame_values=result_record_value.get('frames',{})
    player_payload_value={'id':generation_job_identifier,'frames':frame_values,'fps':result_record_value.get('fps',4),'base':server_base_address}
    player_source_text='''<!doctype html><meta charset="utf-8"><style>body{margin:8px;background:#10151f;color:#e5e7eb;font:14px sans-serif}button,select,input{padding:8px;background:#243449;color:inherit;border:1px solid #526078;border-radius:6px}nav{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}img{width:min(100%,720px);max-height:560px;object-fit:contain;background:#000}#seek{width:min(100%,720px)}</style><nav><select id="direction"></select><button id="previous">이전</button><button id="play">재생</button><button id="stop">중지</button><button id="next">다음</button><select id="fps"><option>4</option><option>8</option><option>12</option><option>16</option></select></nav><img id="frame"><p id="count"></p><input id="seek" type="range" min="0" value="0"><script>const data=__PAYLOAD__,$=id=>document.getElementById(id),names={down_left:'전방 좌측',down_right:'전방 우측',up_left:'후방 좌측',up_right:'후방 우측'};let i=0,t=null;for(const d of Object.keys(data.frames))$('direction').add(new Option(names[d]||d,d));function draw(){const f=data.frames[$('direction').value]||[];if(!f.length)return;$('seek').max=f.length-1;i=Math.min(i,f.length-1);$('frame').src=data.base+'/character-animation/files/'+data.id+'/'+f[i];$('count').textContent=(i+1)+' / '+f.length+' 프레임';$('seek').value=i}function stop(){clearInterval(t);t=null}function step(n){const f=data.frames[$('direction').value]||[];if(!f.length)return;i=(i+n+f.length)%f.length;draw()}$('previous').onclick=()=>{stop();step(-1)};$('next').onclick=()=>{stop();step(1)};$('stop').onclick=stop;$('play').onclick=()=>{stop();t=setInterval(()=>step(1),1000/+$('fps').value)};$('fps').onchange=()=>{if(t)$('play').click()};$('direction').onchange=()=>{i=0;draw()};$('seek').oninput=()=>{stop();i=+$('seek').value;draw()};draw()</script>'''.replace('__PAYLOAD__',json.dumps(player_payload_value).replace('<','\\u003c'))
    return '<iframe title="캐릭터 애니메이션 결과 재생" style="width:100%;height:680px;border:0" sandbox="allow-scripts" srcdoc="'+html.escape(player_source_text,quote=True)+'"></iframe>'

def build_character_animation_interface(server_base_address):
    catalog_record_value=read_animation_catalog()
    motion_choice_values=[(record['label'],record['id']) for record in catalog_record_value['motions']]
    character_choice_values=[(record['label'],record['id']) for record in catalog_record_value['characters']]
    with gr.Blocks(title='캐릭터 애니메이션 생성기') as interface_blocks_value:
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
        with gr.Row():
            with gr.Column(scale=1):
                motion_select_value=gr.Dropdown(motion_choice_values,value=motion_choice_values[0][1],label='모션')
                character_select_value=gr.Dropdown(character_choice_values,value=character_choice_values[0][1],label='캐릭터')
                source_select_value=gr.Radio([('OpenPose','openpose'),('ANNY','anny')],value='openpose',label='포즈 입력')
                direction_select_value=gr.CheckboxGroup(DIRECTION_LABEL_VALUES,value=[value for _,value in DIRECTION_LABEL_VALUES],label='생성 방향')
                with gr.Row():
                    resolution_select_value=gr.Dropdown([512,768,1024,1280],value=512,label='해상도')
                    step_select_value=gr.Radio([4,30],value=4,label='생성 스텝')
                with gr.Row():
                    target_fps_select_value=gr.Dropdown([1,2,3,4],value=4,label='타겟 FPS')
                    speed_select_value=gr.Dropdown([1,1.5,2,4],value=1,label='생성 배속')
                prompt_text_value=gr.Textbox(value=catalog_record_value['prompts']['base'],label='고정 기본 프롬프트',interactive=False,lines=4)
                generation_button_value=gr.Button('애니메이션 생성 시작',variant='primary')
                status_text_value=gr.Markdown('생성 가능 · 설정을 확인하세요.')
            with gr.Column(scale=2):
                generation_identifier_value=gr.Textbox(label='생성 ID',interactive=False)
                player_html_value=gr.HTML('<div>완료된 생성 결과를 선택하면 재생합니다.</div>')
                cancel_button_value=gr.Button('생성 취소')
        logs_text_value,log_refresh_enabled,_=build_execution_logs()
        read_history_page,history_output_values=build_generation_history_view(execute_animation_gateway,server_base_address,'이력 목록만 초기화합니다. 생성 프레임과 로그 파일은 유지됩니다. 생성 중에는 초기화할 수 없습니다.',restore_input_callback=restore_animation_inputs,restore_output_components=[motion_select_value,character_select_value,source_select_value,direction_select_value,resolution_select_value,step_select_value,target_fps_select_value,speed_select_value,status_text_value],result_renderer_callback=create_animation_player,record_folder_route='/character-animation')
        def start_animation(*selection_values):
            request_payload_value=build_animation_request(*selection_values)
            generation_record_value=execute_animation_gateway('generate',request_payload_value)
            return generation_record_value['id'],'상태: running'
        generation_button_value.click(start_animation,[motion_select_value,character_select_value,source_select_value,direction_select_value,resolution_select_value,step_select_value,target_fps_select_value,speed_select_value],[generation_identifier_value,status_text_value])
        interface_blocks_value.load(lambda:read_history_page(1),outputs=history_output_values)
        def refresh_status(identifier,refresh_logs):
            if not identifier:return '생성 ID를 선택하세요.',gr.skip()
            status_record_value=execute_animation_gateway('status',{'id':identifier})
            return '상태: '+status_record_value['status'],gr.update(value=status_record_value['log']) if refresh_logs else gr.skip()
        refresh_button_value=gr.Button('상태 새로고침')
        refresh_button_value.click(refresh_status,[generation_identifier_value,log_refresh_enabled],[status_text_value,logs_text_value],queue=False)
        if hasattr(gr,'Timer'):gr.Timer(2).tick(refresh_status,[generation_identifier_value,log_refresh_enabled],[status_text_value,logs_text_value],show_progress='hidden')
        cancel_button_value.click(lambda identifier:execute_animation_gateway('cancel',{'id':identifier}),generation_identifier_value,status_text_value)
    return interface_blocks_value

from pathlib import Path as ManagementStylePath
MANAGEMENT_DENSITY_STYLES=(ManagementStylePath(__file__).parents[1]/'shared/management-density.css').read_text()

if __name__=='__main__':
    parser_value=argparse.ArgumentParser();parser_value.add_argument('--port',type=int,required=True);parser_value.add_argument('--review-port',type=int,required=True);parser_value.add_argument('--owner-pid',type=int,required=True);parser_value.add_argument('--root-path',default='/character-animation/');arguments_value=parser_value.parse_args()
    def monitor_parent_process():
        while os.getppid()==arguments_value.owner_pid:time.sleep(1)
        os._exit(0)
    threading.Thread(target=monitor_parent_process,daemon=True).start()
    build_character_animation_interface(f'http://127.0.0.1:{arguments_value.review_port}').queue().launch(server_name='127.0.0.1',server_port=arguments_value.port,root_path=arguments_value.root_path,theme=gr.themes.Soft(),css=LOG_PANEL_STYLES+MANAGEMENT_DENSITY_STYLES,allowed_paths=[])

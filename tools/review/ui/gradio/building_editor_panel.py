"""공용 맵 에셋 화면의 건물 원본·앵커 관리."""
import base64
import hashlib
import json
from pathlib import Path
import gradio as gr
from tools.review.common.management_client import execute_remote_management_command

BUILDING_SHADOW_DEFAULT_VALUES = {'shadowShape':'circle','shadowOffsetColumn':0,'shadowOffsetRow':0,'shadowScaleX':1,'shadowScaleY':1}

BUILDING_TOWER_IMAGE_SCALE = 112 / 207


def register_building_editor_panel(current_catalog,current_identifier,current_image_path,current_anchor_x,current_anchor_y):
    if not current_catalog or not current_image_path:raise gr.Error('건물 목록을 불러오고 PNG를 선택하세요.')
    current_request={'texture':current_identifier.strip(),'generation':current_catalog['generation'],'imageBase64':base64.b64encode(Path(current_image_path).read_bytes()).decode(),'properties':{'anchorX':current_anchor_x,'anchorY':current_anchor_y}}
    current_request['requestId']='building-register-'+hashlib.sha256(json.dumps(current_request,sort_keys=True,allow_nan=False).encode()).hexdigest()
    current_result=execute_remote_management_command('map-assets','building-register',current_request)
    return f"건물 등록 완료 · {current_result['asset']} · 목록을 다시 불러오세요."


def prepare_building_retirement(current_selected):
    if not current_selected:raise gr.Error('건물을 먼저 선택하세요.')
    if current_selected.get('texture') == 'ward-tower-v1':raise gr.Error('공용 결계탑은 삭제할 수 없습니다.')
    if current_selected.get('maps'):raise gr.Error('맵에서 사용 중인 건물은 삭제할 수 없습니다.')
    return dict(current_selected),f"**{current_selected['texture']}**을 건물 목록과 공용 속성에서 삭제합니다. 이미지 원본과 등록 이력은 보존합니다.",gr.update(visible=True)


def retire_building_editor_panel(current_catalog,current_selected,current_confirmed):
    if not current_confirmed or current_selected.get('texture')!=current_confirmed.get('texture'):raise gr.Error('선택이 변경되었습니다. 다시 확인하세요.')
    if current_selected.get('texture') == 'ward-tower-v1':raise gr.Error('공용 결계탑은 삭제할 수 없습니다.')
    if current_selected.get('maps'):raise gr.Error('맵에서 사용 중인 건물은 삭제할 수 없습니다.')
    current_request={'texture':current_selected['texture'],'generation':current_catalog['generation']}
    current_request['requestId']='building-retire-'+hashlib.sha256(json.dumps(current_request,sort_keys=True).encode()).hexdigest()
    current_result=execute_remote_management_command('map-assets','building-retire',current_request)
    return f"건물 삭제 완료 · {current_result['asset']} · 목록을 다시 불러오세요.",gr.update(visible=False),{}


def load_building_editor_panel():
    current_catalog=execute_remote_management_command('map-assets','building-list',{})
    current_rows=current_catalog['assets']
    return current_catalog,[(current_row['image'],current_row['texture']) for current_row in current_rows],f"건물 {len(current_rows)}종 · DB 세대 {current_catalog['generation']}. 썸네일을 선택하세요.",{},None,0.5,1.0,'',gr.update(interactive=False),'',gr.update(choices=[],value=None,interactive=False),'[]',gr.update(interactive=False),gr.update(visible=False)


def select_building_editor_panel(current_catalog,current_event:gr.SelectData):
    current_rows=current_catalog.get('assets',[])
    if type(current_event.index) is not int or not 0<=current_event.index<len(current_rows):raise gr.Error('건물을 다시 선택하세요.')
    current_selected=dict(current_rows[current_event.index])
    current_selected['preview']='data:image/png;base64,'+base64.b64encode(Path(current_selected['image']).read_bytes()).decode()
    current_usages=current_selected['maps']
    current_details='\n'.join(f"- {row['map']} · {row['name']} · {row['width']}×{row['height']} · {row['facing']}" for row in current_usages) or '사용 맵 없음'
    current_placement_choices=[(f"{row['map']} · {row['name']} · {row['width']}×{row['height']} · {row['facing']}",str(index)) for index,row in enumerate(current_usages)]
    current_delete_notice=('\n\n결계탑은 공용 에셋이므로 삭제할 수 없습니다.' if current_selected['texture']=='ward-tower-v1' else '\n\n사용 중인 건물은 맵에서 제거한 후 삭제할 수 있습니다.' if current_usages else '')
    return current_selected,current_selected['image'],gr.update(value=current_selected['properties']['anchorX'],interactive=True),gr.update(value=current_selected['properties']['anchorY'],interactive=True),f"**{current_selected['texture']}** · {current_selected['width']}×{current_selected['height']} px\n\n{current_details}{current_delete_notice}",gr.update(interactive=True),current_selected['preview'],gr.update(choices=current_placement_choices,value='0' if current_placement_choices else None,interactive=bool(current_placement_choices)),json.dumps(current_usages,ensure_ascii=False),gr.update(value=current_selected['properties'].get('displayWidthAdjustment',0),interactive=True),gr.update(value=current_selected['properties'].get('displayHeightAdjustment',0),interactive=True),gr.update(interactive=not current_usages and current_selected['texture']!='ward-tower-v1'),gr.update(visible=False),*(current_selected['properties'].get(current_field_name,current_default_value) for current_field_name,current_default_value in BUILDING_SHADOW_DEFAULT_VALUES.items())


def save_building_editor_panel(current_catalog,current_selected,current_anchor_x,current_anchor_y,current_width_adjustment=0,current_height_adjustment=0,current_shadow_shape="circle",current_shadow_column=0,current_shadow_row=0,current_shadow_scale_x=1,current_shadow_scale_y=1):
    if not current_selected:raise gr.Error('건물을 먼저 선택하세요.')
    if any(type(value) not in (int,float) or not float(value).is_integer() or not -2048 <= value <= 2048 for value in (current_width_adjustment,current_height_adjustment)):
        raise gr.Error('크기 보정은 -2048~2048의 정수여야 합니다.')
    for current_usage in current_selected.get('maps',[]):
        current_base_width=(current_selected['width']*BUILDING_TOWER_IMAGE_SCALE if current_usage.get('tower') else (current_usage['width']+current_usage['height'])*40*1.04/current_usage['contentWidth'])
        current_base_height=current_base_width*current_selected['height']/current_selected['width']
        if current_base_width+current_width_adjustment<=0 or current_base_height+current_height_adjustment<=0:
            raise gr.Error('사용 중인 맵에서 건물 크기가 0 이하가 됩니다.')
    current_anchor_values={'anchorX':round(current_anchor_x,7),'anchorY':round(current_anchor_y,7),'displayWidthAdjustment':int(current_width_adjustment),'displayHeightAdjustment':int(current_height_adjustment)}
    current_anchor_values.update(dict(zip(BUILDING_SHADOW_DEFAULT_VALUES,(current_shadow_shape,current_shadow_column,current_shadow_row,current_shadow_scale_x,current_shadow_scale_y))))
    current_previous_values={**current_selected['properties'],'displayWidthAdjustment':current_selected['properties'].get('displayWidthAdjustment',0),'displayHeightAdjustment':current_selected['properties'].get('displayHeightAdjustment',0)}
    if current_anchor_values==current_previous_values:
        return current_catalog,current_selected,'변경된 앵커 값이 없습니다.',current_selected['preview']
    current_result=execute_remote_management_command('map-assets','building-save',{'texture':current_selected['texture'],'generation':current_catalog['generation'],'expected':current_previous_values,'properties':current_anchor_values})
    current_new_catalog=execute_remote_management_command('map-assets','building-list',{})
    current_new_selected=next((dict(row) for row in current_new_catalog['assets'] if row['texture']==current_selected['texture']),None)
    if current_new_selected is None:raise gr.Error('저장 후 건물 목록을 다시 불러오지 못했습니다.')
    current_new_selected['preview']='data:image/png;base64,'+base64.b64encode(Path(current_new_selected['image']).read_bytes()).decode()
    return current_new_catalog,current_new_selected,f"저장 완료 · DB 세대 {current_result['generation']} · 원장에 주기적으로 반영됩니다.",current_new_selected['preview']


def build_building_editor_panel():
    with gr.Group():
        gr.Markdown('등록 건물의 원본과 사용 맵을 확인하고 공용 앵커를 편집합니다. 점유 크기와 출입구는 각 마을 맵에서 관리합니다.')
        current_catalog=gr.State({});current_selected=gr.State({});current_preview_data=gr.Textbox(visible=False);current_placement_data=gr.Textbox(visible=False)
        current_load=gr.Button('건물 목록 불러오기')
        current_feedback=gr.Markdown('건물 목록을 불러오세요.')
        with gr.Accordion('신규 건물 등록',open=False):
            gr.Markdown('목록을 불러온 뒤 512px 이하 투명 PNG와 고유 건물 ID를 입력하세요. 등록 후 앵커를 조정할 수 있습니다.')
            current_new_identifier=gr.Textbox(label='건물 ID',placeholder='town-iseulon-house-v1')
            current_new_image=gr.File(label='건물 투명 PNG',file_types=['.png'],type='filepath')
            with gr.Row():
                current_new_anchor_x=gr.Number(label='앵커 X',value=0.5,minimum=0,maximum=16,step=0.01)
                current_new_anchor_y=gr.Number(label='앵커 Y',value=1,minimum=0,maximum=16,step=0.01)
            current_register=gr.Button('건물 등록')
        current_gallery=gr.Gallery(label='건물 원본 · 선택하여 편집',columns=5,rows=2,object_fit='contain',height='auto',allow_preview=False)
        with gr.Row():
            with gr.Column():
                current_image=gr.Image(label='선택 건물 원본',interactive=False,type='filepath')
                current_placement_choice=gr.Dropdown(label='미리보기 맵 배치',choices=[],interactive=False,info='건물을 선택하면 실제 사용 맵의 배치 중에서 고를 수 있습니다.')
                gr.HTML('<canvas id="building-anchor-preview" width="480" height="360" style="max-width:100%;height:auto" aria-label="건물 타일 배치 미리보기"></canvas>')
                current_preview_feedback=gr.Markdown('노랑: 점유 타일 · 빨강: 앵커 · 회색 점선: 주변 타일')
            with gr.Column():
                with gr.Accordion("에셋 정보·사용 맵",open=False):
                    current_details=gr.Markdown()
                current_anchor_x=gr.Number(label='앵커 X · 이미지 폭 기준',value=0.5,minimum=0,maximum=16,precision=7,step=0.01)
                current_anchor_y=gr.Number(label='앵커 Y · 이미지 높이 기준',value=1,minimum=0,maximum=16,precision=7,step=0.01)
                gr.Markdown('공용 표시 크기를 기존 크기 기준 픽셀 단위로 조정하고 앵커와 함께 저장합니다.')
                current_width_adjustment=gr.Number(label='가로 크기 조정 · px',value=0,precision=0,step=1)
                current_height_adjustment=gr.Number(label='세로 크기 조정 · px',value=0,precision=0,step=1)
                current_size_reset=gr.Button('크기 보정 초기화')
                gr.Markdown('그림자는 점유 영역의 중심을 기준으로 배치합니다. 위치는 타일 단위, 크기는 점유 영역 대비 배율입니다.')
                current_shadow_shape=gr.Radio(choices=[('원형','circle'),('사각형','rectangle')],value='circle',label='그림자 형태')
                with gr.Row():
                    current_shadow_column=gr.Number(label='그림자 열 방향 이동 · 타일',value=0,minimum=-4,maximum=4,step=.1)
                    current_shadow_row=gr.Number(label='그림자 행 방향 이동 · 타일',value=0,minimum=-4,maximum=4,step=.1)
                with gr.Row():
                    current_shadow_scale_x=gr.Number(label='그림자 열 방향 크기 · 배',value=1,minimum=.1,maximum=4,step=.1)
                    current_shadow_scale_y=gr.Number(label='그림자 행 방향 크기 · 배',value=1,minimum=.1,maximum=4,step=.1)
                current_save=gr.Button('선택 건물 표시·그림자 저장',interactive=False,variant='primary')
                current_retire=gr.Button('선택 건물 삭제',interactive=False)
                gr.Markdown('건물을 선택하세요. 맵에서 사용 중이면 삭제할 수 없습니다.')
                current_confirmed=gr.State({})
                with gr.Group(visible=False) as current_retire_group:
                    current_retire_notice=gr.Markdown()
                    with gr.Row():
                        current_retire_confirm=gr.Button('삭제 확인',variant='stop')
                        current_retire_cancel=gr.Button('취소')
        current_load.click(load_building_editor_panel,outputs=[current_catalog,current_gallery,current_feedback,current_selected,current_image,current_anchor_x,current_anchor_y,current_details,current_save,current_preview_data,current_placement_choice,current_placement_data,current_retire,current_retire_group])
        current_preview_script="(preview,anchorX,anchorY,placementIndex,placementJson,widthAdjustment,heightAdjustment,currentShadowShape,currentShadowColumnOffset,currentShadowRowOffset,currentShadowColumnScale,currentShadowRowScale)=>{\n const root=document.querySelector('gradio-app')?.shadowRoot||document;\n const canvas=root.getElementById('building-anchor-preview');\n if(!canvas||!preview)return '건물을 선택하세요.';\n let placements;try{placements=JSON.parse(placementJson||'[]');}catch(error){return '맵 배치 정보를 읽지 못했습니다.';}\n const placement=placements[Number(placementIndex)];\n const ctx=canvas.getContext('2d');const img=new Image();\n const ticket=(canvas.__buildingPreviewTicket||0)+1;canvas.__buildingPreviewTicket=ticket;\n img.onload=()=>{\n  if(canvas.__buildingPreviewTicket!==ticket)return;\n  ctx.clearRect(0,0,canvas.width,canvas.height);ctx.fillStyle='#e9eef2';ctx.fillRect(0,0,canvas.width,canvas.height);\n  if(!placement){const scale=Math.min(440/img.width,320/img.height);ctx.drawImage(img,(canvas.width-img.width*scale)/2,(canvas.height-img.height*scale)/2,img.width*scale,img.height*scale);return;}\n  const TILE_WIDTH=80,TILE_HEIGHT=40,FOOTPRINT_MARGIN=1.04,PADDING=18;\n  const cols=placement.width,rows=placement.height,contentWidth=placement.contentWidth;\n  if(!Number.isInteger(cols)||!Number.isInteger(rows)||cols<1||rows<1||!Number.isFinite(contentWidth)||contentWidth<=0)return;\n  const project=(c,r)=>({x:(c-r)*TILE_WIDTH/2,y:(c+r)*TILE_HEIGHT/2});\n  const front=placement?.tower?project(cols/2,rows/2):project(cols,rows),baseWidth=placement?.tower?img.width*112/207:(cols+rows)*TILE_WIDTH/2*FOOTPRINT_MARGIN/contentWidth,baseHeight=baseWidth*img.height/img.width;\n  const imageWidth=baseWidth+Number(widthAdjustment||0),imageHeight=baseHeight+Number(heightAdjustment||0);if(imageWidth<=0||imageHeight<=0)return;\n  const imageLeft=front.x-Number(anchorX)*imageWidth,imageTop=front.y-Number(anchorY)*imageHeight;\n  const currentShadowCenter=project(cols/2+Number(currentShadowColumnOffset),rows/2+Number(currentShadowRowOffset));\n  const buildShadowOutline=(currentLayerScale)=>{const currentHalfColumn=cols*Number(currentShadowColumnScale)*currentLayerScale/2,currentHalfRow=rows*Number(currentShadowRowScale)*currentLayerScale/2;return (currentShadowShape==='circle'?Array.from({length:48},(_,index)=>({column:Math.cos(index*Math.PI/24)*currentHalfColumn,row:Math.sin(index*Math.PI/24)*currentHalfRow})):[{column:-currentHalfColumn,row:-currentHalfRow},{column:currentHalfColumn,row:-currentHalfRow},{column:currentHalfColumn,row:currentHalfRow},{column:-currentHalfColumn,row:currentHalfRow}]).map(point=>{const offset=project(point.column,point.row);return {x:currentShadowCenter.x+offset.x,y:currentShadowCenter.y+offset.y};});};\n  const bounds=[...buildShadowOutline(1),project(-1,-1),project(cols+1,-1),project(-1,rows+1),project(cols+1,rows+1),{x:imageLeft,y:imageTop},{x:imageLeft+imageWidth,y:imageTop+imageHeight}];\n  const minX=Math.min(...bounds.map(p=>p.x)),maxX=Math.max(...bounds.map(p=>p.x)),minY=Math.min(...bounds.map(p=>p.y)),maxY=Math.max(...bounds.map(p=>p.y));\n  const scale=Math.min((canvas.width-2*PADDING)/(maxX-minX),(canvas.height-2*PADDING)/(maxY-minY));\n  ctx.save();ctx.translate((canvas.width-(maxX-minX)*scale)/2-minX*scale,(canvas.height-(maxY-minY)*scale)/2-minY*scale);ctx.scale(scale,scale);\n  const outline=(c,r)=>{const points=[project(c,r),project(c+1,r),project(c+1,r+1),project(c,r+1)];ctx.beginPath();ctx.moveTo(points[0].x,points[0].y);for(const p of points.slice(1))ctx.lineTo(p.x,p.y);ctx.closePath();};\n  for(let r=-1;r<=rows;r++)for(let c=-1;c<=cols;c++){outline(c,r);ctx.fillStyle=c>=0&&c<cols&&r>=0&&r<rows?'#c2d6a3':'#d8dfd4';ctx.fill();ctx.strokeStyle='#aab8a4';ctx.lineWidth=1/scale;ctx.stroke();}\n  for(const layer of [{scale:1,alpha:.14},{scale:.78,alpha:.20},{scale:.5,alpha:.26}]){const points=buildShadowOutline(layer.scale);ctx.beginPath();ctx.moveTo(points[0].x,points[0].y);for(const point of points.slice(1))ctx.lineTo(point.x,point.y);ctx.closePath();ctx.fillStyle=`rgba(24,32,27,${layer.alpha})`;ctx.fill();}\n  ctx.drawImage(img,imageLeft,imageTop,imageWidth,imageHeight);\n  for(let r=-1;r<=rows;r++)for(let c=-1;c<=cols;c++){const occupied=c>=0&&c<cols&&r>=0&&r<rows;outline(c,r);ctx.strokeStyle=occupied?'#f1b900':'#737d82';ctx.lineWidth=(occupied?1.5:1)/scale;ctx.setLineDash(occupied?[]:[4/scale,4/scale]);ctx.stroke();}\n  ctx.setLineDash([]);ctx.strokeStyle='#ef3340';ctx.lineWidth=2/scale;ctx.beginPath();ctx.moveTo(front.x-8/scale,front.y);ctx.lineTo(front.x+8/scale,front.y);ctx.moveTo(front.x,front.y-8/scale);ctx.lineTo(front.x,front.y+8/scale);ctx.stroke();ctx.restore();\n };\n img.src=preview;\n return placement?`${placement.map} · ${placement.name} · ${placement.width}×${placement.height} · 공용 80×40 · 노랑: 점유, 빨강: 앵커, 점선: 주변 타일`:'맵 배치 미리보기 정보가 없어 원본 이미지만 표시합니다.';\n}\n"
        current_selection=current_gallery.select(select_building_editor_panel,inputs=[current_catalog],outputs=[current_selected,current_image,current_anchor_x,current_anchor_y,current_details,current_save,current_preview_data,current_placement_choice,current_placement_data,current_width_adjustment,current_height_adjustment,current_retire,current_retire_group,current_shadow_shape,current_shadow_column,current_shadow_row,current_shadow_scale_x,current_shadow_scale_y])
        current_selection.then(fn=None,inputs=[current_preview_data,current_anchor_x,current_anchor_y,current_placement_choice,current_placement_data,current_width_adjustment,current_height_adjustment,current_shadow_shape,current_shadow_column,current_shadow_row,current_shadow_scale_x,current_shadow_scale_y],outputs=[current_preview_feedback],js=current_preview_script,queue=False)
        for current_control in (current_anchor_x,current_anchor_y,current_placement_choice,current_width_adjustment,current_height_adjustment,current_shadow_shape,current_shadow_column,current_shadow_row,current_shadow_scale_x,current_shadow_scale_y):
            current_control.change(fn=None,inputs=[current_preview_data,current_anchor_x,current_anchor_y,current_placement_choice,current_placement_data,current_width_adjustment,current_height_adjustment,current_shadow_shape,current_shadow_column,current_shadow_row,current_shadow_scale_x,current_shadow_scale_y],outputs=[current_preview_feedback],js=current_preview_script,queue=False)
        current_size_reset.click(lambda: (0,0),outputs=[current_width_adjustment,current_height_adjustment],queue=False)
        current_save.click(save_building_editor_panel,inputs=[current_catalog,current_selected,current_anchor_x,current_anchor_y,current_width_adjustment,current_height_adjustment,current_shadow_shape,current_shadow_column,current_shadow_row,current_shadow_scale_x,current_shadow_scale_y],outputs=[current_catalog,current_selected,current_feedback,current_preview_data],concurrency_limit=1,trigger_mode='once')
        current_register.click(register_building_editor_panel,inputs=[current_catalog,current_new_identifier,current_new_image,current_new_anchor_x,current_new_anchor_y],outputs=[current_feedback],concurrency_limit=1,trigger_mode='once')
        current_retire.click(prepare_building_retirement,inputs=[current_selected],outputs=[current_confirmed,current_retire_notice,current_retire_group],queue=False)
        current_retire_confirm.click(retire_building_editor_panel,inputs=[current_catalog,current_selected,current_confirmed],outputs=[current_feedback,current_retire_group,current_confirmed],concurrency_limit=1,trigger_mode='once')
        current_retire_cancel.click(lambda: (gr.update(visible=False),{}),outputs=[current_retire_group,current_confirmed],queue=False)


def build_building_editor_interface(current_review_port):
    with gr.Blocks(title='건물 에셋 관리') as current_interface_blocks:
        gr.Markdown('## 건물 에셋 관리')
        build_building_editor_panel()
    return current_interface_blocks

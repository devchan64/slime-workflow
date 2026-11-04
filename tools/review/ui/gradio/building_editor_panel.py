"""공용 맵 에셋 화면의 건물 원본·앵커 관리."""
import base64
import json
from pathlib import Path
import gradio as gr
from tools.review.common.management_client import execute_remote_management_command


def load_building_editor_panel():
    current_catalog=execute_remote_management_command('map-assets','building-list',{})
    current_rows=current_catalog['assets']
    return current_catalog,[(current_row['image'],current_row['texture']) for current_row in current_rows],f"건물 {len(current_rows)}종 · DB 세대 {current_catalog['generation']}. 썸네일을 선택하세요.",{},None,0.5,1.0,'',gr.update(interactive=False),'',gr.update(choices=[],value=None,interactive=False),'[]'


def select_building_editor_panel(current_catalog,current_event:gr.SelectData):
    current_rows=current_catalog.get('assets',[])
    if type(current_event.index) is not int or not 0<=current_event.index<len(current_rows):raise gr.Error('건물을 다시 선택하세요.')
    current_selected=dict(current_rows[current_event.index])
    current_selected['preview']='data:image/png;base64,'+base64.b64encode(Path(current_selected['image']).read_bytes()).decode()
    current_usages=current_selected['maps']
    current_details='\n'.join(f"- {row['map']} · {row['name']} · {row['width']}×{row['height']} · {row['facing']}" for row in current_usages) or '사용 맵 없음'
    current_placement_choices=[(f"{row['map']} · {row['name']} · {row['width']}×{row['height']} · {row['facing']}",str(index)) for index,row in enumerate(current_usages)]
    return current_selected,current_selected['image'],current_selected['properties']['anchorX'],current_selected['properties']['anchorY'],f"**{current_selected['texture']}** · {current_selected['width']}×{current_selected['height']} px\n\n{current_details}",gr.update(interactive=True),current_selected['preview'],gr.update(choices=current_placement_choices,value='0' if current_placement_choices else None,interactive=bool(current_placement_choices)),json.dumps(current_usages,ensure_ascii=False),current_selected['properties'].get('displayWidthAdjustment',0),current_selected['properties'].get('displayHeightAdjustment',0)


def save_building_editor_panel(current_catalog,current_selected,current_anchor_x,current_anchor_y,current_width_adjustment=0,current_height_adjustment=0):
    if not current_selected:raise gr.Error('건물을 먼저 선택하세요.')
    if any(type(value) not in (int,float) or not float(value).is_integer() or not -2048 <= value <= 2048 for value in (current_width_adjustment,current_height_adjustment)):
        raise gr.Error('크기 보정은 -2048~2048의 정수여야 합니다.')
    for current_usage in current_selected.get('maps',[]):
        current_base_width=(current_usage['width']+current_usage['height'])*40*1.04/current_usage['contentWidth']
        current_base_height=current_base_width*current_selected['height']/current_selected['width']
        if current_base_width+current_width_adjustment<=0 or current_base_height+current_height_adjustment<=0:
            raise gr.Error('사용 중인 맵에서 건물 크기가 0 이하가 됩니다.')
    current_anchor_values={'anchorX':round(current_anchor_x,3),'anchorY':round(current_anchor_y,3),'displayWidthAdjustment':int(current_width_adjustment),'displayHeightAdjustment':int(current_height_adjustment)}
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
        current_gallery=gr.Gallery(label='건물 원본 · 선택하여 편집',columns=5,rows=2,object_fit='contain',height='auto',allow_preview=False)
        with gr.Row():
            with gr.Column():
                current_image=gr.Image(label='선택 건물 원본',interactive=False,type='filepath')
                current_placement_choice=gr.Dropdown(label='미리보기 맵 배치',choices=[],interactive=False,info='건물을 선택하면 실제 사용 맵의 배치 중에서 고를 수 있습니다.')
                gr.HTML('<canvas id="building-anchor-preview" width="480" height="360" aria-label="건물 타일 배치 미리보기"></canvas>')
                current_preview_feedback=gr.Markdown('노랑: 점유 타일 · 빨강: 앵커 · 회색 점선: 주변 타일')
            with gr.Column():
                current_details=gr.Markdown()
                current_anchor_x=gr.Number(label='앵커 X · 이미지 폭 기준',value=0.5,minimum=0,maximum=16,precision=3,step=0.01)
                current_anchor_y=gr.Number(label='앵커 Y · 이미지 높이 기준',value=1,minimum=0,maximum=16,precision=3,step=0.01)
                gr.Markdown('공용 표시 크기를 기존 크기 기준 픽셀 단위로 조정하고 앵커와 함께 저장합니다.')
                current_width_adjustment=gr.Number(label='가로 크기 조정 · px',value=0,precision=0,step=1)
                current_height_adjustment=gr.Number(label='세로 크기 조정 · px',value=0,precision=0,step=1)
                current_size_reset=gr.Button('크기 보정 초기화')
                current_save=gr.Button('선택 건물 앵커·크기 저장',interactive=False,variant='primary')
        current_load.click(load_building_editor_panel,outputs=[current_catalog,current_gallery,current_feedback,current_selected,current_image,current_anchor_x,current_anchor_y,current_details,current_save,current_preview_data,current_placement_choice,current_placement_data])
        current_preview_script="(preview,anchorX,anchorY,placementIndex,placementJson,widthAdjustment,heightAdjustment)=>{\n const root=document.querySelector('gradio-app')?.shadowRoot||document;\n const canvas=root.getElementById('building-anchor-preview');\n if(!canvas||!preview)return '건물을 선택하세요.';\n let placements;try{placements=JSON.parse(placementJson||'[]');}catch(error){return '맵 배치 정보를 읽지 못했습니다.';}\n const placement=placements[Number(placementIndex)];\n const ctx=canvas.getContext('2d');const img=new Image();\n const ticket=(canvas.__buildingPreviewTicket||0)+1;canvas.__buildingPreviewTicket=ticket;\n img.onload=()=>{\n  if(canvas.__buildingPreviewTicket!==ticket)return;\n  ctx.clearRect(0,0,canvas.width,canvas.height);ctx.fillStyle='#e9eef2';ctx.fillRect(0,0,canvas.width,canvas.height);\n  if(!placement){const scale=Math.min(440/img.width,320/img.height);ctx.drawImage(img,(canvas.width-img.width*scale)/2,(canvas.height-img.height*scale)/2,img.width*scale,img.height*scale);return;}\n  const TILE_WIDTH=80,TILE_HEIGHT=40,FOOTPRINT_MARGIN=1.04,PADDING=18;\n  const cols=placement.width,rows=placement.height,contentWidth=placement.contentWidth;\n  if(!Number.isInteger(cols)||!Number.isInteger(rows)||cols<1||rows<1||!Number.isFinite(contentWidth)||contentWidth<=0)return;\n  const project=(c,r)=>({x:(c-r)*TILE_WIDTH/2,y:(c+r)*TILE_HEIGHT/2});\n  const front=project(cols,rows),baseWidth=(cols+rows)*TILE_WIDTH/2*FOOTPRINT_MARGIN/contentWidth,baseHeight=baseWidth*img.height/img.width;\n  const imageWidth=baseWidth+Number(widthAdjustment||0),imageHeight=baseHeight+Number(heightAdjustment||0);if(imageWidth<=0||imageHeight<=0)return;\n  const imageLeft=front.x-Number(anchorX)*imageWidth,imageTop=front.y-Number(anchorY)*imageHeight;\n  const bounds=[project(-1,-1),project(cols+1,-1),project(-1,rows+1),project(cols+1,rows+1),{x:imageLeft,y:imageTop},{x:imageLeft+imageWidth,y:imageTop+imageHeight}];\n  const minX=Math.min(...bounds.map(p=>p.x)),maxX=Math.max(...bounds.map(p=>p.x)),minY=Math.min(...bounds.map(p=>p.y)),maxY=Math.max(...bounds.map(p=>p.y));\n  const scale=Math.min((canvas.width-2*PADDING)/(maxX-minX),(canvas.height-2*PADDING)/(maxY-minY));\n  ctx.save();ctx.translate((canvas.width-(maxX-minX)*scale)/2-minX*scale,(canvas.height-(maxY-minY)*scale)/2-minY*scale);ctx.scale(scale,scale);\n  const outline=(c,r)=>{const points=[project(c,r),project(c+1,r),project(c+1,r+1),project(c,r+1)];ctx.beginPath();ctx.moveTo(points[0].x,points[0].y);for(const p of points.slice(1))ctx.lineTo(p.x,p.y);ctx.closePath();};\n  for(let r=-1;r<=rows;r++)for(let c=-1;c<=cols;c++){outline(c,r);ctx.fillStyle=c>=0&&c<cols&&r>=0&&r<rows?'#c2d6a3':'#d8dfd4';ctx.fill();ctx.strokeStyle='#aab8a4';ctx.lineWidth=1/scale;ctx.stroke();}\n  ctx.drawImage(img,imageLeft,imageTop,imageWidth,imageHeight);\n  for(let r=-1;r<=rows;r++)for(let c=-1;c<=cols;c++){const occupied=c>=0&&c<cols&&r>=0&&r<rows;outline(c,r);ctx.strokeStyle=occupied?'#f1b900':'#737d82';ctx.lineWidth=(occupied?1.5:1)/scale;ctx.setLineDash(occupied?[]:[4/scale,4/scale]);ctx.stroke();}\n  ctx.setLineDash([]);ctx.strokeStyle='#ef3340';ctx.lineWidth=2/scale;ctx.beginPath();ctx.moveTo(front.x-8/scale,front.y);ctx.lineTo(front.x+8/scale,front.y);ctx.moveTo(front.x,front.y-8/scale);ctx.lineTo(front.x,front.y+8/scale);ctx.stroke();ctx.restore();\n };\n img.src=preview;\n return placement?`${placement.map} · ${placement.name} · ${placement.width}×${placement.height} · 공용 80×40 · 노랑: 점유, 빨강: 앵커, 점선: 주변 타일`:'사용 중인 맵 배치가 없어 원본 이미지만 표시합니다.';\n}\n"
        current_selection=current_gallery.select(select_building_editor_panel,inputs=[current_catalog],outputs=[current_selected,current_image,current_anchor_x,current_anchor_y,current_details,current_save,current_preview_data,current_placement_choice,current_placement_data,current_width_adjustment,current_height_adjustment])
        current_selection.then(fn=None,inputs=[current_preview_data,current_anchor_x,current_anchor_y,current_placement_choice,current_placement_data,current_width_adjustment,current_height_adjustment],outputs=[current_preview_feedback],js=current_preview_script,queue=False)
        for current_control in (current_anchor_x,current_anchor_y,current_placement_choice,current_width_adjustment,current_height_adjustment):
            current_control.change(fn=None,inputs=[current_preview_data,current_anchor_x,current_anchor_y,current_placement_choice,current_placement_data,current_width_adjustment,current_height_adjustment],outputs=[current_preview_feedback],js=current_preview_script,queue=False)
        current_size_reset.click(lambda: (0,0),outputs=[current_width_adjustment,current_height_adjustment],queue=False)
        current_save.click(save_building_editor_panel,inputs=[current_catalog,current_selected,current_anchor_x,current_anchor_y,current_width_adjustment,current_height_adjustment],outputs=[current_catalog,current_selected,current_feedback,current_preview_data],concurrency_limit=1,trigger_mode='once')


def build_building_editor_interface(current_review_port):
    with gr.Blocks(title='건물 에셋 관리') as current_interface_blocks:
        gr.Markdown('## 건물 에셋 관리')
        build_building_editor_panel()
    return current_interface_blocks

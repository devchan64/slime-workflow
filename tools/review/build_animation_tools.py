from pathlib import Path
import json, shutil, yaml

ROOT = Path(__file__).resolve().parents[2]
DIRECTIONS = ('down_left', 'down_right', 'up_left', 'up_right')


def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def openpose_selector_page(motions):
    config = json.dumps({'motions': motions, 'interval_ms': 250}, ensure_ascii=False).replace('<', '\u003c')
    return ('<!doctype html><meta charset="utf-8"><title>MoMask 애니메이션 OpenPose 맵 플레이어</title>'
            '<link rel="stylesheet" href="../animation-tools-common/player.css"><main>'
            '<h1>MoMask 애니메이션 OpenPose 맵 플레이어</h1>'
            '<p>동작과 방향을 선택하면 해당 OpenPose 맵 프레임만 반복 재생합니다.</p>'
            '<p><label>동작 <select id="motion"></select></label><label>방향 <select id="direction"></select></label></p>'
            '<div class="stage"><img id="image"></div><p><button id="previous">이전</button><button id="play">재생</button><button id="next">다음</button><input id="range" type="range"><output id="count"></output></p></main>'
            '<script>window.ANIMATION_TOOL='+config+';</script><script src="../animation-tools-common/player.js"></script>')


def write_common_player(output):
    common = output / 'animation-tools-common'
    common.mkdir(parents=True, exist_ok=True)
    (common / 'player.css').write_text('body{margin:0;padding:28px;background:#101814;color:#e7f2e9;font:14px system-ui}main{max-width:1080px;margin:auto}.stage{height:600px;display:grid;place-items:center;background:#07100b;border:1px solid #3c6249;border-radius:12px}img{max-width:100%;max-height:580px;image-rendering:pixelated}button,input,select{margin:12px 8px 0 0;padding:8px}pre{white-space:pre-wrap;background:#07100b;padding:12px;border-radius:8px;color:#bce6c8}', encoding='utf-8')
    player = """const config=window.ANIMATION_TOOL||{};const image=document.querySelector('#image'),range=document.querySelector('#range'),count=document.querySelector('#count'),play=document.querySelector('#play');let index=0,timer,frames=config.frames||[];const stop=()=>{if(timer){clearInterval(timer);timer=null;play.textContent='재생'}};const draw=()=>{image.src=frames[index]||'';count.textContent=`${index+1} / ${frames.length}`;range.max=Math.max(0,frames.length-1);range.value=index};const step=n=>{if(!frames.length)return;index=(index+n+frames.length)%frames.length;draw()};document.querySelector('#previous').onclick=()=>step(-1);document.querySelector('#next').onclick=()=>step(1);range.oninput=()=>{index=Number(range.value);draw()};play.onclick=()=>{if(timer)stop();else{timer=setInterval(()=>step(1),config.interval_ms||150);play.textContent='정지'}};if(config.motions){const motion=document.querySelector('#motion'),direction=document.querySelector('#direction');for(const [id,item] of Object.entries(config.motions))motion.add(new Option(item.label,id));const selectDirection=()=>{direction.replaceChildren();for(const [id,item] of Object.entries(config.motions[motion.value].directions))direction.add(new Option(item.label,id));};const selectFrames=()=>{stop();frames=config.motions[motion.value].directions[direction.value].frames;index=0;draw()};motion.onchange=()=>{selectDirection();selectFrames()};direction.onchange=selectFrames;selectDirection();selectFrames()}else draw();"""
    (common / 'player.js').write_text(player, encoding='utf-8')


def build_animation_tools(output):
    write_common_player(output)
    records=[]
    standing_motion_selection=yaml.safe_load((ROOT/'generators/animation/config/default_standing_motion.yaml').read_text())
    records.append({'id':'momask-generator','label':'MoMask 모션 생성기','path':'/momask-generator/','anchorEditor':False,'category':'animation-tool','description':'고정 포즈 스크립트 · 방향 선택 · 생성 로그·취소·결과 재생'})
    attribute_page = '''<!doctype html><meta charset="utf-8"><title>Anny 속성 렌더러</title><link rel="stylesheet" href="../animation-tools-common/player.css"><main><h1>Anny 속성 렌더러</h1><p>네이버랩스 Anny의 체형·국소 속성 입력을 검토합니다. 값은 새 렌더 후보의 입력으로 기록됩니다.</p><form id="attributes"><h2>기본 체형</h2><label>나이 <input name="age" type="range" min="0" max="1" step="0.05" value="0.15"><output></output></label><label>체중 <input name="weight" type="range" min="0" max="1" step="0.05" value="0.25"><output></output></label><label>키 <input name="height" type="range" min="0" max="1" step="0.05" value="0.25"><output></output></label><h2>국소 체형</h2><label>몸통 너비 <input name="torso-scale-horiz-incr" type="range" min="-1" max="1" step="0.05" value="-0.5"><output></output></label><label>몸통 깊이 <input name="torso-scale-depth-incr" type="range" min="-1" max="1" step="0.05" value="-0.5"><output></output></label><label>어깨 너비 <input name="measure-shoulder-dist-incr" type="range" min="-1" max="1" step="0.05" value="0.5"><output></output></label><label>다리 길이 <input name="upperlegs-height-incr" type="range" min="-1" max="1" step="0.05" value="0.7"><output></output></label><button type="button" id="export">렌더 입력 JSON 내려받기</button></form><pre id="preview"></pre></main><script>const f=document.querySelector('#attributes'),p=document.querySelector('#preview');const render=()=>{for(const i of f.querySelectorAll('input'))i.nextElementSibling.textContent=i.value;const a=Object.fromEntries(new FormData(f));p.textContent=JSON.stringify({phenotype_kwargs:{age:+a.age,weight:+a.weight,height:+a.height},local_changes_kwargs:Object.fromEntries(Object.entries(a).filter(([k])=>!['age','weight','height'].includes(k)).map(([k,v])=>[k,+v]))},null,2)};f.oninput=render;render();document.querySelector('#export').onclick=()=>{const b=new Blob([p.textContent],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='anny-attributes.json';a.click();URL.revokeObjectURL(a.href)}</script>'''
    folder=output/'anny-attribute-renderer';folder.mkdir(parents=True,exist_ok=True);(folder/'index.html').write_text(attribute_page,encoding='utf-8')
    records.append({'id':'anny-attribute-renderer','label':'Anny 속성 렌더러','path':'/anny-attributes/','anchorEditor':False,'category':'animation-tool','description':'나이·체중·키와 몸통·어깨·다리 로컬 속성의 렌더 입력 검토'})
    loop_source = ROOT / 'assets/motion-sheet/momask-standing-loops-v1'
    for action, identifier, title, note in (
        ('standing', 'momask-normal-breath-standing', 'MoMask 대기 스탠딩', '40프레임 · 10초 · 4방향 · 미세 체중 이동'),
        ('deep-breath', 'momask-deep-breath', 'MoMask 심호흡', '8프레임 · 2초 · 4방향'),
        ('stretch', 'momask-stretch', 'MoMask 스트레칭', '20프레임 · 5초 · 4방향'),
    ):
        folder = output / identifier
        if action=='standing':
            for direction in DIRECTIONS:
                for frame_number in range(1,standing_motion_selection['frames']+1):
                    frame_file_name=f'{direction}-{frame_number:04d}.png'
                    copy(ROOT/standing_motion_selection['openpose_path']/direction/f'openpose-{frame_number:04d}.png',folder/frame_file_name)
            (folder/'index.html').write_text(openpose_selector_page({'standing':{'label':'대기 · v3 · 16프레임', 'directions':{direction:{'label':direction,'frames':[f'{direction}-{number:04d}.png' for number in range(1,standing_motion_selection['frames']+1)]} for direction in DIRECTIONS}}}),encoding='utf-8')
            records.append({'id':identifier,'label':title,'path':identifier+'/index.html','anchorEditor':False,'category':'animation-tool','description':'승인 대기 v3 · 16프레임 · 4초 · 4방향'})
            continue
        copy(loop_source / 'artifact.json', folder / 'artifact.json')
        copy(loop_source / action / 'source-motion.npz', folder / 'source-motion.npz')
        copy(loop_source / action / 'pose-sheets' / 'manifest.json', folder / 'pose-sheets-manifest.json')
        action_images = []
        for direction in DIRECTIONS:
            name = f'{direction}.png'
            copy(loop_source / action / 'pose-sheets' / name, folder / name)
            action_images.append(f'<img src="{name}" alt="{title} {direction}" style="width:100%">')
        (folder / 'index.html').write_text('<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="../animation-tools-common/player.css"><main><h1>'+title+'</h1><p>'+note+'</p><p>HumanML3D-22에는 눈 관절이 없어 눈깜박임은 이미지 프레임 단계에서 추가합니다.</p><p><a href="artifact.json">생성 메타데이터</a> · <a href="source-motion.npz" download>원본 모션 다운로드</a></p><section style="display:grid;grid-template-columns:1fr 1fr;gap:12px">'+''.join(action_images)+'</section></main>', encoding='utf-8')
        records.append({'id':identifier,'label':title,'path':identifier+'/index.html','anchorEditor':False,'category':'animation-tool','description':note})
    return records

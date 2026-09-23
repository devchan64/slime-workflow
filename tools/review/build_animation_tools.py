from pathlib import Path
import json, shutil

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'assets/motion-sheet/mannequin-walk-v6'
DIRECTIONS = ('down_left', 'down_right', 'up_left', 'up_right')


def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def page(title, note, frames, command=''):
    config = json.dumps({'frames': frames}, ensure_ascii=False).replace('<', '\\u003c')
    command_html = '<pre>'+command+'</pre>' if command else ''
    return f'''<!doctype html><meta charset="utf-8"><title>{title}</title><link rel="stylesheet" href="../animation-tools-common/player.css"><main><h1>{title}</h1><p>{note}</p>{command_html}<div class="stage"><img id="image"></div><p><button id="previous">이전</button><button id="play">재생</button><button id="next">다음</button><input id="range" type="range"><output id="count"></output></p></main><script>window.ANIMATION_TOOL={config};</script><script src="../animation-tools-common/player.js"></script>'''


def write_common_player(output):
    common = output / 'animation-tools-common'
    common.mkdir(parents=True, exist_ok=True)
    (common / 'player.css').write_text('body{margin:0;padding:28px;background:#101814;color:#e7f2e9;font:14px system-ui}main{max-width:1080px;margin:auto}.stage{height:600px;display:grid;place-items:center;background:#07100b;border:1px solid #3c6249;border-radius:12px}img{max-width:100%;max-height:580px;image-rendering:pixelated}button,input{margin:12px 8px 0 0;padding:8px}pre{white-space:pre-wrap;background:#07100b;padding:12px;border-radius:8px;color:#bce6c8}', encoding='utf-8')
    (common / 'player.js').write_text("const {frames=[]}=window.ANIMATION_TOOL;const image=document.querySelector('#image'),range=document.querySelector('#range'),count=document.querySelector('#count');let index=0,timer;range.max=Math.max(0,frames.length-1);function draw(){image.src=frames[index]||'';count.textContent=`${index+1} / ${frames.length}`;range.value=index}function step(n){index=(index+n+frames.length)%frames.length;draw()}document.querySelector('#previous').onclick=()=>step(-1);document.querySelector('#next').onclick=()=>step(1);range.oninput=()=>{index=Number(range.value);draw()};document.querySelector('#play').onclick=e=>{if(timer){clearInterval(timer);timer=null;e.target.textContent='재생'}else{timer=setInterval(()=>step(1),150);e.target.textContent='정지'}};draw();", encoding='utf-8')


def build_animation_tools(output):
    write_common_player(output)
    records=[]
    openpose=[]
    for direction in DIRECTIONS:
        for number in range(1,9):
            name=f'{direction}-{number:04d}.png'; copy(SOURCE/direction/f'openpose-{number:04d}.png', output/'momask-openpose-player'/name); openpose.append(name)
    (output/'momask-openpose-player'/'index.html').write_text(page('MoMask 애니메이션 OpenPose 맵 플레이어','MoMask 걷기 모션에서 추출한 4방향 32개 OpenPose 맵입니다.',openpose),encoding='utf-8')
    records.append({'id':'momask-openpose-player','label':'MoMask 애니메이션 OpenPose 맵 플레이어','path':'momask-openpose-player/index.html','anchorEditor':False,'category':'animation-tool','description':'MoMask 걷기 · OpenPose 4방향 32프레임'})
    rig=[]
    for direction in DIRECTIONS:
        name=f'{direction}.png'; copy(SOURCE/'rig-sheets'/name,output/'momask-rig-player'/name); rig.append(name)
    (output/'momask-rig-player'/'index.html').write_text(page('MoMask 애니메이션 리그 플레이어','MoMask 모션을 Anny 리그에 적용한 방향별 리그 시트입니다.',rig),encoding='utf-8')
    records.append({'id':'momask-rig-player','label':'MoMask 애니메이션 리그 플레이어','path':'momask-rig-player/index.html','anchorEditor':False,'category':'animation-tool','description':'MoMask 걷기 · Anny 리그 시트 4방향'})
    standing_source = ROOT / 'assets/motion-sheet/momask-standing-idle-v1'
    copy(standing_source / 'artifact.json', output / 'momask-standing-idle' / 'artifact.json')
    copy(standing_source / 'source-motion.npz', output / 'momask-standing-idle' / 'source-motion.npz')
    (output / 'momask-standing-idle' / 'index.html').write_text('''<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="../animation-tools-common/player.css"><main><h1>MoMask 스탠딩 아이들 모션</h1><p>48프레임 · 20fps · 2.4초 원본 관절 모션입니다. 렌더링은 4방향 × 8샘플, 총 32프레임으로 제한합니다.</p><p>호흡·체중 이동·작은 어깨와 팔 스트레칭을 포함합니다. HumanML3D-22에는 눈 관절이 없어 눈깜박임은 이미지 프레임 단계에서 추가합니다.</p><p><a href="artifact.json">생성 메타데이터</a> · <a href="source-motion.npz" download>원본 모션 다운로드</a></p></main>''', encoding='utf-8')
    records.append({'id':'momask-standing-idle','label':'MoMask 스탠딩 아이들 모션','path':'momask-standing-idle/index.html','anchorEditor':False,'category':'animation-tool','description':'호흡·작은 스트레칭 · 48프레임 원본 · 4방향 32프레임 렌더 계획'})
    copy(SOURCE/'camera45-four-view.gif',output/'anny-model-viewer'/'turntable.gif'); copy(SOURCE/'mannequin.glb',output/'anny-model-viewer'/'mannequin.glb')
    (output/'anny-model-viewer'/'index.html').write_text('<!doctype html><meta charset="utf-8"><style>body{background:#101814;color:#e7f2e9;font:14px system-ui;padding:28px}img{max-width:100%}a{color:#9febb1}</style><h1>Anny 모델링 뷰어</h1><p>45° 4방향 워크 턴테이블과 로컬 GLB 원본입니다.</p><img src="turntable.gif"><p><a href="mannequin.glb" download>mannequin.glb 다운로드</a></p>',encoding='utf-8')
    records.append({'id':'anny-model-viewer','label':'Anny 모델링 뷰어','path':'anny-model-viewer/index.html','anchorEditor':False,'category':'animation-tool','description':'Anny 리그 45° 턴테이블 · GLB 원본'})
    for identifier,title,note,command in [('openpose-frame-generator','OpenPose 맵 애니메이션 프레임 생성기','캐릭터 기준 이미지와 OpenPose 맵으로 Qwen 프레임을 생성합니다.','python3 generators/animation/generate_pose_transfer_openpose_qwen.py --output-dir .tmp/<run>/frame --prompt-file generators/animation/config/pose_transfer_openpose_qwen_prompt.txt --direction down_right'),('anypose-frame-generator','AnyPose 애니메이션 프레임 생성기','캐릭터 기준 이미지와 리그 참조로 AnyPose 프레임을 생성합니다.','python3 generators/animation/generate_pose_transfer_any_pose_frame.py --output-dir .tmp/<run>/frame --prompt-file <prompt.txt>')]:
        folder=output/identifier;folder.mkdir(parents=True,exist_ok=True);copy(SOURCE/'down_right'/'openpose-0001.png',folder/'reference.png');(folder/'index.html').write_text(page(title,note,['reference.png'],command),encoding='utf-8');records.append({'id':identifier,'label':title,'path':identifier+'/index.html','anchorEditor':False,'category':'animation-tool','description':note})
    return records

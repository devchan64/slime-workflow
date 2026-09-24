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
    openpose_motions = {}
    openpose_sources = (
        ('walk', '걷기', SOURCE, {direction: list(range(1, 9)) for direction in DIRECTIONS}),
        ('standing', '일반호흡 스탠딩', ROOT / 'assets/motion-sheet/momask-standing-loops-v1' / 'standing' / 'openpose', {direction: list(range(1, 5)) for direction in DIRECTIONS}),
        ('deep-breath', '심호흡', ROOT / 'assets/motion-sheet/momask-standing-loops-v1' / 'deep-breath' / 'openpose', {direction: list(range(1, 9)) for direction in DIRECTIONS}),
        ('stretch', '스트레칭', ROOT / 'assets/motion-sheet/momask-standing-loops-v1' / 'stretch' / 'openpose', {direction: list(range(1, 21)) for direction in DIRECTIONS}),
    )
    for motion_id, label, source_root, direction_numbers in openpose_sources:
        motion_directions = {}
        for direction in DIRECTIONS:
            frames = []
            for number in direction_numbers[direction]:
                name = f'{motion_id}-{direction}-{number:04d}.png'
                copy(source_root / direction / f'openpose-{number:04d}.png', output / 'momask-openpose-player' / name)
                frames.append(name)
            motion_directions[direction] = {'label': direction, 'frames': frames}
        openpose_motions[motion_id] = {'label': label, 'directions': motion_directions}
    (output/'momask-openpose-player'/'index.html').write_text(openpose_selector_page(openpose_motions),encoding='utf-8')
    records.append({'id':'momask-openpose-player','label':'MoMask 애니메이션 OpenPose 맵 플레이어','path':'momask-openpose-player/index.html','anchorEditor':False,'category':'animation-tool','description':'걷기·일반호흡·심호흡·스트레칭 선택 · 각 4방향'})
    rig=[]
    for direction in DIRECTIONS:
        name=f'{direction}.png'; copy(SOURCE/'rig-sheets'/name,output/'momask-rig-player'/name); rig.append(name)
    (output/'momask-rig-player'/'index.html').write_text(page('MoMask 애니메이션 리그 플레이어','MoMask 모션을 Anny 리그에 적용한 방향별 리그 시트입니다.',rig),encoding='utf-8')
    records.append({'id':'momask-rig-player','label':'MoMask 애니메이션 리그 플레이어','path':'momask-rig-player/index.html','anchorEditor':False,'category':'animation-tool','description':'MoMask 걷기 · Anny 리그 시트 4방향'})
    copy(SOURCE/'camera45-four-view.gif',output/'anny-model-viewer'/'turntable.gif'); copy(SOURCE/'mannequin.glb',output/'anny-model-viewer'/'mannequin.glb')
    (output/'anny-model-viewer'/'index.html').write_text('<!doctype html><meta charset="utf-8"><style>body{background:#101814;color:#e7f2e9;font:14px system-ui;padding:28px}img{max-width:100%}a{color:#9febb1}</style><h1>Anny 모델링 뷰어</h1><p>45° 4방향 워크 턴테이블과 로컬 GLB 원본입니다.</p><img src="turntable.gif"><p><a href="mannequin.glb" download>mannequin.glb 다운로드</a></p>',encoding='utf-8')
    records.append({'id':'anny-model-viewer','label':'Anny 모델링 뷰어','path':'anny-model-viewer/index.html','anchorEditor':False,'category':'animation-tool','description':'Anny 리그 45° 턴테이블 · GLB 원본'})
    for identifier,title,note,command in [('openpose-frame-generator','OpenPose 맵 애니메이션 프레임 생성기','캐릭터 기준 이미지와 OpenPose 맵으로 Qwen 프레임을 생성합니다.','python3 generators/animation/generate_pose_transfer_openpose_qwen.py --output-dir .tmp/<run>/frame --prompt-file generators/animation/config/pose_transfer_openpose_qwen_prompt.txt --direction down_right'),('anypose-frame-generator','AnyPose 애니메이션 프레임 생성기','캐릭터 기준 이미지와 리그 참조로 AnyPose 프레임을 생성합니다.','python3 generators/animation/run_pose_transfer_any_pose_batch.py --batch-file <batch.yaml> --output-dir .tmp/<run> --resume')]:
        folder=output/identifier;folder.mkdir(parents=True,exist_ok=True);copy(SOURCE/'down_right'/'openpose-0001.png',folder/'reference.png');(folder/'index.html').write_text(page(title,note,['reference.png'],command),encoding='utf-8');records.append({'id':identifier,'label':title,'path':identifier+'/index.html','anchorEditor':False,'category':'animation-tool','description':note})
    loop_source = ROOT / 'assets/motion-sheet/momask-standing-loops-v1'
    for action, identifier, title, note in (
        ('standing', 'momask-normal-breath-standing', 'MoMask 일반호흡 스탠딩', '4프레임 · 1초 · 4방향'),
        ('deep-breath', 'momask-deep-breath', 'MoMask 심호흡', '8프레임 · 2초 · 4방향'),
        ('stretch', 'momask-stretch', 'MoMask 스트레칭', '20프레임 · 5초 · 4방향'),
    ):
        folder = output / identifier
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

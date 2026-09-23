from pathlib import Path
from PIL import Image,ImageDraw
import json,time
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/overlay/start {EXPERIMENT_OUTPUT_ROOT}',flush=True)
comparison_sheet_image=Image.new('RGB',(1280,640),'white')
for current_view_index,current_view_name in enumerate(['front','side']):
 reference_image_value=Image.open(EXPERIMENT_OUTPUT_ROOT/'inputs'/f'reference-{current_view_name}.png').convert('RGBA')
 overlay_image_value=Image.open(EXPERIMENT_OUTPUT_ROOT/f'overlay-{current_view_name}.png').convert('RGBA')
 overlay_image_value.putalpha(overlay_image_value.getchannel('A').point(lambda current_alpha_value:round(current_alpha_value*.6)))
 composite_image_value=Image.alpha_composite(reference_image_value,overlay_image_value)
 composite_image_value.save(EXPERIMENT_OUTPUT_ROOT/f'comparison-{current_view_name}.png')
 comparison_sheet_image.paste(composite_image_value.convert('RGB').resize((640,640)),(640*current_view_index,0))
comparison_sheet_image.save(EXPERIMENT_OUTPUT_ROOT/'overlay-comparison.jpg')
(EXPERIMENT_OUTPUT_ROOT/'preview.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>레퍼런스 자세 비교</title><style>body{background:#20252b;color:white;font:16px system-ui;margin:24px}main{max-width:1400px;margin:auto}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}img{width:100%}a{color:lightblue}</style><main><h1>목 높이·다리 길이 수정</h1><p>목 높이 1→0.5, 허벅지 길이 0.5→0.7, 종아리 길이 0.5→0.7로 변경했습니다. 목 세로 스케일 0.5와 나머지 체형·포즈는 유지했습니다.</p><h2>정면·측면</h2><div class="grid"><img src="front.png"><img src="side.png"></div><h2>후면·사선</h2><div class="grid"><img src="back.png"><img src="three-quarter.png"></div><h2>레퍼런스 60% 오버레이</h2><p>전체 높이만 균일 정규화. 정면·측면의 팔과 다리 자세를 레퍼런스와 비교합니다.</p><img src="overlay-comparison.jpg"><h2>변경 전 / 변경 후</h2><div class="grid"><img src="inputs/previous-front.png"><img src="front.png"></div><p><a href="anny-raw-rig.blend">Blender</a> · <a href="anny-raw-rig.glb">GLB</a> · <a href="inputs/attributes.json">입력 JSON</a> · <a href="generation.json">실제 적용값</a></p></main></html>')

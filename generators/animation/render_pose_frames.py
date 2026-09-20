"""승인된 v9 MoMask 리그의 한 주기를 4방향·6프레임으로 출력한다."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import threading
import traceback
import numpy as np
from PIL import Image, ImageDraw
import rig_builder as rig_render_module

WORKFLOW_REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_RIG_DIRECTORY = WORKFLOW_REPO_ROOT / '.result/workflow/reusable/rigs/five-head-walk/v9'
EXPERIMENT_OUTPUT_ROOT = WORKFLOW_REPO_ROOT / '.tmp' / datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
OUTPUT_SAMPLE_INDICES = np.arange(6) * 4
OUTPUT_FRAME_DURATION = 200
POSE_JOINT_INDICES = [15,12,17,19,21,16,18,20,2,5,8,1,4,7]
POSE_EDGE_INDICES = [(1,2),(2,3),(3,4),(1,5),(5,6),(6,7),(1,8),(8,9),(9,10),(1,11),(11,12),(12,13),(1,0)]
POSE_EDGE_COLORS = ['#ff5500','#ffaa00','#ffff00','#aaff00','#55ff00','#00ff00','#00ff55','#00ffaa','#00ffff','#00aaff','#0055ff','#0000ff','#ff0000']


def execute_six_frame_render():
    EXPERIMENT_OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    rig_render_module.RENDER_OUTPUT_PATH = EXPERIMENT_OUTPUT_ROOT
    rig_render_module.OUTPUT_ASSET_PATH = EXPERIMENT_OUTPUT_ROOT / 'rig'
    rig_render_module.OUTPUT_ASSET_PATH.mkdir()
    rig_render_module.OUTPUT_FRAME_COUNT = 6
    rig_render_module.RENDER_PIXEL_SIZE = 512
    threading.Thread(target=rig_render_module.emit_progress_heartbeat,daemon=True).start()
    try:
        source_artifact_record=json.loads((SOURCE_RIG_DIRECTORY/'artifact.json').read_text())
        source_motion_path=SOURCE_RIG_DIRECTORY/'retargeted-motion.npz'
        if hashlib.sha256(source_motion_path.read_bytes()).hexdigest()!=source_artifact_record['files']['retargeted-motion.npz']:
            raise ValueError('v9 모션 해시 불일치')
        original_motion_path=WORKFLOW_REPO_ROOT/'.result/workflow/reusable/motions/walk-travel/v1/motion.npz'
        if hashlib.sha256(original_motion_path.read_bytes()).hexdigest()!=source_artifact_record['motion']['source_sha256']:
            raise ValueError('MoMask 원본 해시 불일치')
        with np.load(source_motion_path,allow_pickle=False) as source_motion_bundle:
            full_motion_joints=source_motion_bundle['joints'].copy()
            resting_joint_points=source_motion_bundle['rest'].copy()
        if full_motion_joints.shape!=(25,22,3) or not np.allclose(full_motion_joints[0],full_motion_joints[-1],atol=1e-8):
            raise ValueError('1.2초 루프 모션의 닫힌 끝점 계약 불일치')
        if not np.allclose(resting_joint_points,rig_render_module.REST_JOINT_POINTS):
            raise ValueError('승인 리그 체형 불일치')
        selected_joint_frames=full_motion_joints[OUTPUT_SAMPLE_INDICES]
        loop_step_distances=np.sqrt(np.mean((np.roll(selected_joint_frames,-1,axis=0)-selected_joint_frames)**2,axis=(1,2)))
        np.savez_compressed(EXPERIMENT_OUTPUT_ROOT/'sampled-motion.npz',joints=selected_joint_frames,rest=resting_joint_points,sample_indices=OUTPUT_SAMPLE_INDICES)
        rig_render_module.write_trace_message('prepare','MoMask 출처·v9 체형·닫힌 루프 검증; 0,4,8,12,16,20 표본')
        render_result_record=rig_render_module.build_render_scene(selected_joint_frames)
        import bpy
        bpy.context.scene.render.fps=5
        bpy.context.scene.render.fps_base=1
        bpy.ops.wm.save_as_mainfile(filepath=str(EXPERIMENT_OUTPUT_ROOT/'rig/five-head-walk.blend'))
        world_joint_frames=selected_joint_frames[:,:,[0,2,1]].copy();world_joint_frames[:,:,1]*=-1
        direction_pose_records={}
        for direction_name_value,camera_point_values in rig_render_module.DIRECTION_CAMERA_POINTS.items():
            camera_target_point=np.array([0.,0.,1.])
            camera_offset_vector=np.array(camera_point_values)-camera_target_point
            camera_position_point=camera_target_point+camera_offset_vector/np.linalg.norm(camera_offset_vector)*6
            camera_forward_vector=(camera_target_point-camera_position_point)/6
            camera_right_vector=np.cross(camera_forward_vector,[0,0,1]);camera_right_vector/=np.linalg.norm(camera_right_vector)
            camera_up_vector=np.cross(camera_right_vector,camera_forward_vector)
            relative_joint_frames=world_joint_frames-camera_position_point
            projected_joint_frames=np.stack((.5+relative_joint_frames@camera_right_vector/2.65,.5-relative_joint_frames@camera_up_vector/2.65),axis=-1)*512
            direction_pose_records[direction_name_value]=projected_joint_frames[:,POSE_JOINT_INDICES].tolist()
            contact_sheet_image=Image.new('RGB',(512*6,512),'#202635')
            for frame_index_value in range(6):
                pose_frame_image=Image.new('RGB',(512,512),'black');pose_drawing_context=ImageDraw.Draw(pose_frame_image)
                pose_joint_points=projected_joint_frames[frame_index_value,POSE_JOINT_INDICES]
                for edge_joint_pair,edge_color_value in zip(POSE_EDGE_INDICES,POSE_EDGE_COLORS):
                    pose_drawing_context.line([tuple(pose_joint_points[edge_joint_pair[0]]),tuple(pose_joint_points[edge_joint_pair[1]])],fill=edge_color_value,width=5)
                for joint_point_value,joint_color_value in zip(pose_joint_points,POSE_EDGE_COLORS+[POSE_EDGE_COLORS[0]]):
                    horizontal_pixel_value,vertical_pixel_value=joint_point_value
                    pose_drawing_context.ellipse((horizontal_pixel_value-4,vertical_pixel_value-4,horizontal_pixel_value+4,vertical_pixel_value+4),fill=joint_color_value)
                pose_frame_image.save(EXPERIMENT_OUTPUT_ROOT/direction_name_value/f'openpose-{frame_index_value+1:04d}.png')
                preview_frame_image=Image.open(EXPERIMENT_OUTPUT_ROOT/direction_name_value/f'preview-{frame_index_value+1:04d}.png').convert('RGBA')
                contact_sheet_image.paste(preview_frame_image,(frame_index_value*512,0),preview_frame_image)
            contact_sheet_image.save(EXPERIMENT_OUTPUT_ROOT/direction_name_value/'contact-sheet.png')
        manifest_result_record={'source':source_artifact_record['motion'],'rig':'five-head-walk/v9','directions':list(direction_pose_records),'frames_per_direction':6,'frame_duration_ms':200,'cycle_seconds':1.2,'loop':True,'sample_indices':OUTPUT_SAMPLE_INDICES.tolist(),'duplicate_end_frame':False,'closed_endpoint_max_error':float(np.abs(full_motion_joints[0]-full_motion_joints[-1]).max()),'step_rms_m':loop_step_distances.tolist(),'neutral_height_m':2.,'head_height_m':.4,'neutral_head_units':5,'render':render_result_record,'quality_status':'awaiting_user_review','notes':['5등신은 중립 리그 메시 기준이며 투영 자세에서는 겉보기 등신이 달라질 수 있음','원본 루프와 발 회전 검증; 6프레임의 시각적 부드러움은 검수 필요']}
        (EXPERIMENT_OUTPUT_ROOT/'manifest.json').write_text(json.dumps(manifest_result_record,ensure_ascii=False,indent=2)+'\n')
        (EXPERIMENT_OUTPUT_ROOT/'openpose-keypoints.json').write_text(json.dumps({'format':'COCO18-compatible projected MoMask rig; nose=head center, eyes/ears omitted','frames':direction_pose_records},indent=2)+'\n')
        preview_html_text='''<!doctype html><meta charset="utf-8"><title>MoMask 4방향 · 6프레임 루프</title><style>body{background:#141924;color:#eee;font:16px sans-serif;margin:24px}main{display:grid;grid-template-columns:repeat(4,minmax(200px,1fr));gap:16px}img{width:100%;background:#242b39}button,select{font-size:16px;margin:10px}p{color:#b8c5d8}</style><h1>MoMask · v9 5등신 리그 · 4방향 6프레임</h1><p>1.2초 루프 / 200ms씩 / 마지막 중복 프레임 제외. 중립 리그 5등신, 최종 캐릭터 이미지 아님.</p><button id="toggle">일시정지</button><select id="mode"><option value="preview">리그</option><option value="openpose">OpenPose</option><option value="depth">Depth</option></select><span id="counter"></span><main></main><script>const directionNameValues=['down_left','down_right','up_left','up_right'];let currentFrameIndex=0;let animationIsPlaying=true;const previewMainElement=document.querySelector('main');for(const directionNameValue of directionNameValues){previewMainElement.insertAdjacentHTML('beforeend',`<section><h2>${directionNameValue}</h2><img data-direction="${directionNameValue}"><a href="${directionNameValue}/contact-sheet.png">6프레임 펼쳐보기</a></section>`)}function updatePreviewImages(){for(const imageElementValue of document.querySelectorAll('img'))imageElementValue.src=`${imageElementValue.dataset.direction}/${document.querySelector('#mode').value}-${String(currentFrameIndex+1).padStart(4,'0')}.png`;document.querySelector('#counter').textContent=`${currentFrameIndex+1} / 6`;}document.querySelector('#toggle').onclick=()=>{animationIsPlaying=!animationIsPlaying;document.querySelector('#toggle').textContent=animationIsPlaying?'일시정지':'재생'};document.querySelector('#mode').onchange=updatePreviewImages;updatePreviewImages();setInterval(()=>{if(animationIsPlaying){currentFrameIndex=(currentFrameIndex+1)%6;updatePreviewImages()}},200);</script>'''
        (EXPERIMENT_OUTPUT_ROOT/'preview.html').write_text(preview_html_text)
        rig_render_module.write_trace_message('complete',str(EXPERIMENT_OUTPUT_ROOT))
    except Exception:
        rig_render_module.write_trace_message('failure',traceback.format_exc())
        raise
    finally:
        rig_render_module.HEARTBEAT_STOP_EVENT.set()

if __name__=='__main__':
    execute_six_frame_render()

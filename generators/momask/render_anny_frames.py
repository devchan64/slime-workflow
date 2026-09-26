"""MoMask HumanML3D 관절 모션을 Anny 모델 프레임으로 리타깃·렌더한다."""
from pathlib import Path
import math
import argparse, hashlib, json, shutil, subprocess
import numpy as np
import yaml

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'generators/momask/templates'
BLENDER=ROOT/'.local/blender-runtime/bin/python'
DIRECTIONS={'down_left','down_right','up_left','up_right'}
RETARGET_PROFILE_PATH = ROOT/'generators/momask/config/humanml22-anny-retarget.yaml'
RETARGET_ALGORITHM_VERSION = 'position-profile-transport-v2'

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def render(motion_path, output_dir, directions, sample_indices, camera_azimuth_degrees=45):
    motion_path=Path(motion_path).resolve();output_dir=Path(output_dir).resolve()
    if not output_dir.is_relative_to(ROOT/'.tmp'): raise ValueError('Anny 출력은 .tmp 하위여야 합니다.')
    joints=np.load(motion_path,allow_pickle=False)['joints']
    if joints.ndim!=3 or joints.shape[1:]!=(22,3) or not len(joints) or not np.isfinite(joints).all(): raise ValueError('HumanML3D-22 관절 모션이 필요합니다.')
    if not sample_indices or min(sample_indices)<0 or max(sample_indices)>=len(joints): raise ValueError('유효한 샘플 인덱스가 필요합니다.')
    if not set(directions) or set(directions)-DIRECTIONS: raise ValueError('방향 선택 오류')
    output_dir.mkdir(parents=True,exist_ok=False);(output_dir/'inputs').mkdir()
    source_motion=output_dir/'inputs/mannequin-motion.npz';np.savez_compressed(source_motion,joints=joints,rest=joints[0],contacts=np.zeros((len(joints),2),dtype=np.float32),sample_indices=np.array(sample_indices))
    (output_dir/'inputs/artifact.json').write_text(json.dumps({'files':{'mannequin-motion.npz':digest(source_motion)},'fps':4,'source_motion':str(motion_path.relative_to(ROOT))},ensure_ascii=False))
    baseline_selection_record=yaml.safe_load((ROOT/'generators/animation/config/anny_model_baseline.yaml').read_text())
    baseline_selection_record=yaml.safe_load((ROOT/baseline_selection_record['active_profile_path']).read_text())
    baseline_manifest_record=yaml.safe_load((ROOT/baseline_selection_record['manifest_path']).read_text())
    baseline_blend_path=ROOT/baseline_selection_record['blend_path']
    baseline_blend_hash=digest(baseline_blend_path)
    if baseline_blend_hash!=baseline_manifest_record['files'][baseline_blend_path.name]['sha256']:raise ValueError('기준 모델 Blender 해시 불일치')
    baseline_model_record={'baseline_id':baseline_selection_record['profile_id'],'source_generation_id':baseline_manifest_record['source_generation_id'],'blend_sha256':baseline_blend_hash,'attributes_sha256':baseline_selection_record['attributes_sha256']}
    (output_dir/'baseline-model.json').write_text(json.dumps(baseline_model_record,ensure_ascii=False,indent=2))
    print('ANNY 기준 모델: '+baseline_selection_record['profile_id'],flush=True)
    shutil.copy2(baseline_blend_path,output_dir/'inputs/anny-reference-fit-rig.blend')
    for name in ('run_stage.py','retarget_loop.py','render_asset.py'):
        shutil.copy2(SOURCE/name,output_dir/name)
    shutil.copy2(ROOT/'generators/momask/position_retarget.py',output_dir/'position_retarget.py')
    shutil.copy2(RETARGET_PROFILE_PATH,output_dir/'retarget-profile.yaml')
    retarget_result_record={'renderer':'Anny Blender retarget','frames':len(sample_indices),'directions':directions,'samples':16,'hand_pose':'inherit-rest-local','arm_retarget':RETARGET_ALGORITHM_VERSION,'skinning':'dual-quaternion','baseline_model':baseline_model_record,'profile_sha256':digest(output_dir/'retarget-profile.yaml'),'solver_sha256':digest(output_dir/'position_retarget.py')}
    (output_dir/'retarget-contract.json').write_text(json.dumps(retarget_result_record,ensure_ascii=False,indent=2))
    if not 0<camera_azimuth_degrees<90:raise ValueError('카메라 수평 방향각 범위 오류')
    camera_horizontal_x=math.sqrt(52)*math.sin(math.radians(camera_azimuth_degrees))
    camera_horizontal_y=math.sqrt(52)*math.cos(math.radians(camera_azimuth_degrees))
    cameras={key:value for key,value in {'down_left':(camera_horizontal_x,-camera_horizontal_y,3),'down_right':(-camera_horizontal_x,-camera_horizontal_y,3),'up_left':(camera_horizontal_x,camera_horizontal_y,3),'up_right':(-camera_horizontal_x,camera_horizontal_y,3)}.items() if key in directions}
    (output_dir/'camera-settings.json').write_text(json.dumps({'azimuth_degrees':camera_azimuth_degrees,'elevation_degrees':math.degrees(math.atan2(2.2,math.sqrt(52))),'positions':cameras}))
    renderer=(output_dir/'render_asset.py').read_text()
    renderer=renderer.replace('OUTPUT_SAMPLE_FRAMES=[1,4,7,10,13,16,19,22]',f'OUTPUT_SAMPLE_FRAMES={[index+1 for index in sample_indices]!r}')
    renderer=renderer.replace("DIRECTION_CAMERA_POINTS={'down_left':(CAMERA_HORIZONTAL_OFFSET,-CAMERA_HORIZONTAL_OFFSET,3),'down_right':(-CAMERA_HORIZONTAL_OFFSET,-CAMERA_HORIZONTAL_OFFSET,3),'up_left':(CAMERA_HORIZONTAL_OFFSET,CAMERA_HORIZONTAL_OFFSET,3),'up_right':(-CAMERA_HORIZONTAL_OFFSET,CAMERA_HORIZONTAL_OFFSET,3)}",f'DIRECTION_CAMERA_POINTS={cameras!r}')
    renderer=renderer.replace("scene_render_value.cycles.samples=64", "scene_render_value.cycles.samples=16")
    (output_dir/'render_asset.py').write_text(renderer)
    for script in ('retarget_loop.py','render_asset.py'):
        subprocess.run([str(BLENDER),str(output_dir/'run_stage.py'),str(output_dir/script)],cwd=output_dir,check=True)
    for direction in directions:
        target=output_dir/direction/'frames';target.mkdir()
        for number in range(1,len(sample_indices)+1): shutil.copy2(output_dir/direction/f'preview-{number:04d}.png',target/f'anny-{number:04d}.png')
    (output_dir/'result.json').write_text(json.dumps(retarget_result_record,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--motion',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--directions',required=True);p.add_argument('--sample-indices',required=True);p.add_argument('--camera-azimuth-degrees',type=float,default=45);a=p.parse_args();render(a.motion,a.output_dir,a.directions.split(','),[int(x) for x in a.sample_indices.split(',')],camera_azimuth_degrees=a.camera_azimuth_degrees)

"""OpenPose 맵 생성 결과와 입력 맵을 비교하는 시트를 만든다."""
from pathlib import Path
import argparse, json, shutil
from build_pose_transfer_review import FRAME_NUMBERS, SUPPORTED_DIRECTIONS, sha256_file

ROOT = Path(__file__).resolve().parents[2]

def build_openpose_review(report_path: Path, output_path: Path) -> Path:
    report_path, output_path = report_path.resolve(), output_path.resolve()
    if not report_path.is_relative_to(ROOT / 'report') or not report_path.is_dir(): raise ValueError(f'리포트 경로가 올바르지 않습니다: {report_path}')
    if not output_path.is_relative_to(ROOT / '.tmp') or output_path.exists(): raise ValueError(f'출력 경로를 사용할 수 없습니다: {output_path}')
    output_path.mkdir(parents=True)
    records=[]
    for direction in SUPPORTED_DIRECTIONS:
        frames=[]
        for number in FRAME_NUMBERS:
            frame=report_path/direction/f'frame-{number:02d}'; files={}
            for role, name in (('result','result.png'),('rig','openpose-reference.png')):
                source=frame/name; relative=Path(direction)/f'frame-{number:02d}'/f'{role}.png'; target=output_path/relative
                if not source.is_file(): raise ValueError(f'비교 이미지가 없습니다: {source}')
                target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,target); files[role]={'path':relative.as_posix(),'sha256':sha256_file(source)}
            frames.append({'frame':number,'files':files,'size':json.loads((frame/'result.json').read_text())['size']})
        records.append({'direction':direction,'frames':frames})
    template=(Path(__file__).with_name('pose-transfer-review.html')).read_text()
    template=template.replace('3참조 포즈 전이 비교','OpenPose 맵 생성 비교').replace('결과·리그·OpenPose 기준 비교','OpenPose 생성 결과·입력 맵 비교').replace('Qwen 결과 캐릭터','OpenPose 맵 생성 결과').replace('리그 참조','OpenPose 입력 맵').replace('OpenPose 참조','OpenPose 입력 맵')
    data={'report':report_path.name,'directions':records}
    (output_path/'preview.html').write_text(template.replace('__POSE_TRANSFER_DATA__',json.dumps(data,ensure_ascii=False).replace('<','\\u003c')))
    return output_path

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--root',type=Path,required=True); parser.add_argument('--output',type=Path,required=True); args=parser.parse_args(); print(build_openpose_review(args.root,args.output))

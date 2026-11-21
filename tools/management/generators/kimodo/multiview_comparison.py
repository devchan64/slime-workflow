"""동일 입력의 2D·다중 시점 3D 보정 결과를 참조 관절과 비교한다."""
import json
from pathlib import Path

import numpy as np

from generators.kimodo.reference_proportions import REFERENCE_CONFIDENCE_THRESHOLD, REFERENCE_SEGMENT_GROUPS


def calculate_projected_body_ratios(current_body_points, current_segment_pairs):
    current_body_array=np.asarray(current_body_points,dtype=float)
    if current_body_array.ndim!=2 or current_body_array.shape[0] < 14 or current_body_array.shape[1] < 2 or not np.isfinite(current_body_array[:14,:2]).all():
        raise ValueError('비교할 BODY18 좌표 형식 오류')
    current_body_height=abs(float(current_body_array[[2,5],1].mean()-current_body_array[[10,13],1].mean()))
    if current_body_height<=1e-8:
        raise ValueError('비교 기준 어깨–발목 높이가 0입니다.')
    return {current_group_name:float(np.mean([np.linalg.norm(current_body_array[current_parent_index,:2]-current_body_array[current_child_index,:2]) for current_parent_index,current_child_index in current_pairs])/current_body_height) for current_group_name,current_pairs in current_segment_pairs.items()}


def compare_multiview_outputs(current_baseline_root,current_experiment_root,current_direction_mapping,current_reference_ratio_path=None):
    current_baseline_root=Path(current_baseline_root)
    current_experiment_root=Path(current_experiment_root)
    current_reference_path=Path(current_reference_ratio_path) if current_reference_ratio_path is not None else current_baseline_root/'reference-proportions.json'
    if not current_reference_path.is_file():
        raise ValueError('비교할 참조 관절 기록이 없습니다.')
    current_reference_record=json.loads(current_reference_path.read_text())
    current_baseline_direct=json.loads((current_baseline_root/'soma-direct-pose.json').read_text())['directions']
    current_experiment_direct=json.loads((current_experiment_root/'soma-direct-pose.json').read_text())['directions']
    if set(current_direction_mapping)!=set(current_baseline_direct) or set(current_direction_mapping)!=set(current_experiment_direct) or sorted(current_direction_mapping.values())!=list(range(1,9)):
        raise ValueError('출력 방향과 8개 참조 관측의 대응이 유효하지 않습니다.')
    current_comparison_rows=[]
    for current_direction_name,current_observation_number in current_direction_mapping.items():
        current_reference_points=current_reference_record['keypoints'][current_observation_number-1]
        current_segment_pairs={}
        for current_group_name,current_candidate_pairs in REFERENCE_SEGMENT_GROUPS.items():
            current_valid_pairs=[current_pair for current_pair in current_candidate_pairs if min(current_reference_points[current_pair[0]][2],current_reference_points[current_pair[1]][2])>=REFERENCE_CONFIDENCE_THRESHOLD]
            if current_group_name=='upper_arm':
                current_observation_rows=current_reference_record['evidence'][current_group_name]['observations']
                current_observation_record=next((current_row for current_row in current_observation_rows if current_row['image']==current_observation_number),None)
                if current_observation_record:
                    current_candidates=current_observation_record.get('candidates',[])
                    if any('겹친' in current_candidate.get('selection_reason','') for current_candidate in current_candidates):
                        current_valid_pairs=[tuple(current_observation_record['joint_pair'])]
            if current_valid_pairs:
                current_segment_pairs[current_group_name]=current_valid_pairs
        current_reference_ratios=calculate_projected_body_ratios(current_reference_points,current_segment_pairs)
        current_output_records={}
        for current_output_name,current_output_root,current_direct_records in [('baseline',current_baseline_root,current_baseline_direct),('multiview',current_experiment_root,current_experiment_direct)]:
            current_direct_frames=current_direct_records[current_direction_name]['body_points_832x480']
            current_dwpose_path=current_output_root/f'dwpose-{current_direction_name}'/'pose-keypoints-adjusted.json'
            current_dwpose_video=current_output_root/f'dwpose-{current_direction_name}.mp4'
            if not current_direct_frames:
                raise ValueError('비교할 직접 포즈 프레임이 없습니다.')
            current_direct_ratios=[calculate_projected_body_ratios(current_frame_points,current_segment_pairs) for current_frame_points in current_direct_frames]
            current_output_record={'direct_first':current_direct_ratios[0], 'direct_median':{current_group_name:float(np.median([current_frame[current_group_name] for current_frame in current_direct_ratios])) for current_group_name in current_segment_pairs},'direct_frames':len(current_direct_frames)}
            if current_dwpose_path.is_file() and current_dwpose_video.is_file():
                current_dwpose_frames=json.loads(current_dwpose_path.read_text())
                if not current_dwpose_frames: raise ValueError('DWPose 관절 기록이 비어 있습니다.')
                current_dwpose_ratios=[calculate_projected_body_ratios(current_frame_record[0][0][0],current_segment_pairs) for current_frame_record in current_dwpose_frames]
                current_output_record.update(dwpose_first=current_dwpose_ratios[0],dwpose_median={current_group_name:float(np.median([current_frame[current_group_name] for current_frame in current_dwpose_ratios])) for current_group_name in current_segment_pairs},dwpose_frames=len(current_dwpose_frames),dwpose_status='available')
            else:
                current_error_path=current_output_root/'dwpose-error.json'
                current_error_text=json.loads(current_error_path.read_text()).get('error') if current_error_path.is_file() else 'DWPose 관절 기록이 없습니다.'
                current_output_record.update(dwpose_first=None,dwpose_median=None,dwpose_frames=0,dwpose_status='unavailable',dwpose_error=current_error_text)
            current_output_records[current_output_name]=current_output_record
        current_comparison_rows.append({'direction':current_direction_name,'reference_observation':current_observation_number,'reference':current_reference_ratios,'reference_pairs':{current_name:[list(current_pair) for current_pair in current_pairs] for current_name,current_pairs in current_segment_pairs.items()},**current_output_records})
    current_summary_record={}
    for current_output_type in ('direct_first','direct_median','dwpose_first','dwpose_median'):
        current_summary_record[current_output_type]={}
        for current_group_name in REFERENCE_SEGMENT_GROUPS:
            current_valid_rows=[current_row for current_row in current_comparison_rows if current_group_name in current_row['reference'] and current_row['baseline'][current_output_type] is not None and current_row['multiview'][current_output_type] is not None]
            if not current_valid_rows:
                current_summary_record[current_output_type][current_group_name]={'baseline':None,'multiview':None,'paired_views':0}
                continue
            current_summary_record[current_output_type][current_group_name]={**{current_method_name:float(np.mean([abs(current_row[current_method_name][current_output_type][current_group_name]-current_row['reference'][current_group_name]) for current_row in current_valid_rows])) for current_method_name in ('baseline','multiview')},'paired_views':len(current_valid_rows)}
    return {'schema':'kimodo-multiview-comparison-v1','reference_source':str(current_reference_path),'normalization':'양 어깨 중점부터 양 발목 중점까지 영상 세로 거리','direction_mapping_assumed':current_direction_mapping,'views':current_comparison_rows,'mean_absolute_error':current_summary_record,'limitations':['대각 참조의 정확한 각도와 출력 방향 대응은 가정이다','2D 검출점이 정답이라는 보장은 없다','영상 중앙값과 단일 정지 참조의 비교에는 자세 변화가 포함된다','가림 판정은 위팔에만 적용했고 나머지 구간의 가림은 자동 판정하지 않았다']}


if __name__=='__main__':
    import argparse
    current_argument_parser=argparse.ArgumentParser(description='8방향 비율 보정 실험 비교')
    current_argument_parser.add_argument('baseline_root',type=Path)
    current_argument_parser.add_argument('experiment_root',type=Path)
    current_argument_parser.add_argument('mapping_json',type=Path)
    current_argument_parser.add_argument('output_json',type=Path)
    current_argument_parser.add_argument('--reference-json',type=Path,help='선택적 별도 참조 관절 기록')
    current_arguments=current_argument_parser.parse_args()
    current_result_record=compare_multiview_outputs(current_arguments.baseline_root,current_arguments.experiment_root,json.loads(current_arguments.mapping_json.read_text()),current_arguments.reference_json)
    current_arguments.output_json.write_text(json.dumps(current_result_record,ensure_ascii=False,indent=2))
    print(f'8방향 비율 비교 저장: {current_arguments.output_json}',flush=True)

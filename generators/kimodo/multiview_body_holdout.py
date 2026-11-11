"""방향·관절을 제외하고 공통 3D 몸 관측의 재투영 오차를 기록한다."""
import json
from pathlib import Path

import numpy as np

from generators.kimodo.multiview_body_face_experiment import fit_multiview_body_face
from generators.kimodo.multiview_provenance import calculate_multiview_observation_hash,calculate_multiview_fit_context_hash


def calculate_body_holdout_report(current_reference,current_initial,current_visibility,current_weights,current_selections):
    """지정한 몸 관측을 하나씩 제외하고 각 좌표 오차를 기록한다."""
    if not isinstance(current_selections,list) or not current_selections:
        raise ValueError('제외 검증할 몸 관측 목록이 필요합니다.')
    current_targets=[]
    for current_row in current_selections:
        if not isinstance(current_row,dict) or type(current_row.get('observation')) is not int or type(current_row.get('joint')) is not int or not 1<=current_row['observation']<=8 or current_row['joint'] not in (2,3,4,5,6,7,9,10,12,13):
            raise ValueError('제외 검증할 몸 관측 번호 오류')
        current_target=(current_row['observation'],current_row['joint'])
        if current_target in current_targets:
            raise ValueError('제외 검증할 몸 관측이 중복되었습니다.')
        current_targets.append(current_target)
    current_records=[]
    for current_index,(current_observation,current_joint) in enumerate(current_targets):
        current_target=np.asarray(current_reference['keypoints'][current_observation-1][current_joint][:2],dtype=float)
        try:
            current_fit=fit_multiview_body_face(current_reference,current_initial,current_visibility,current_joint_weight_table=current_weights,current_excluded_body=(current_observation-1,current_joint))
        except ValueError as current_error:
            current_records.append({'observation':current_observation,'joint':current_joint,'error_px':None,'reason':str(current_error)})
        else:
            current_prediction=np.asarray(current_fit['views'][current_observation-1]['body_xy'][current_joint-2],dtype=float)
            current_records.append({'observation':current_observation,'joint':current_joint,'error_px':float(np.linalg.norm(current_prediction-current_target)),'prediction':current_prediction.tolist(),'observed':current_target.tolist()})
        if (current_index+1)%5==0 or current_index+1==len(current_targets):
            print(f'Kimodo 몸 제외 관측 검증: {current_index+1}/{len(current_targets)}',flush=True)
    current_observation_hash=calculate_multiview_observation_hash(current_reference)
    current_context_hash=calculate_multiview_fit_context_hash(current_observation_hash,current_initial,current_visibility,current_weights)
    return {'excluded_observations':current_records,'observation_sha256':current_observation_hash,'fit_context_sha256':current_context_hash,'joint_weight_table':current_weights,'limitation':'초기 카메라와 다른 초기 관절은 기존 적합 결과를 사용하므로 완전히 독립된 검증이 아님. 골반은 정규화 기준이라 제외 검증하지 않음.'}


if __name__=='__main__':
    import argparse
    current_parser=argparse.ArgumentParser(description='지정한 몸 관측 제외 검증')
    for current_name in ('reference','initial','visibility','weights','selections','output'):
        current_parser.add_argument(current_name,type=Path)
    current_arguments=current_parser.parse_args()
    if current_arguments.output.exists():
        raise ValueError('기존 몸 제외 검증 기록을 덮어쓰지 않습니다.')
    current_inputs=[json.loads(getattr(current_arguments,current_name).read_text()) for current_name in ('reference','initial','visibility','weights','selections')]
    current_inputs[-1]=current_inputs[-1]['excluded_observations']
    current_result=calculate_body_holdout_report(*current_inputs)
    current_arguments.output.write_text(json.dumps(current_result,ensure_ascii=False,indent=2))

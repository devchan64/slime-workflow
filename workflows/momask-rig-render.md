# MoMask 리그 렌더 기준

기본 걷기는 **mannequin-walk/v8**이다. 선택 이력 `2026-09-24_22-04-47-42b7a56f`의 32프레임·4fps·4방향을 재사용한다. 기존 v1~v7 기본 선택은 폐기했다. ANNY 모델은 39eab167이며 모션 신규 추론 없이 재렌더한다.

```bash
.venv/bin/python generators/animation/render_momask_rig.py
```

CUDA가 필요한 실행은 샌드박스 밖에서 수행한다. 기본 리그 선택기는 default_walk_rig.yaml이며 등록 에셋의 해시를 검증한다. 고정 버전의 렌더 코드를 새 .tmp 폴더에 복사해 실행하므로 기존 에셋을 덮어쓰지 않는다. 완료 후 방향별 32프레임 ANNY 이미지가 생성된다. 기존 버전은 과거 이력과 재현 코드용으로만 보존한다. 구형 자체 리그 렌더 경로는 폐기했으며 현재 진입점은 render_momask_rig.py이다. AnyPose 기본 참조 선택은 별도 설정이다.


## 관리도구 대기 모션 생성과 보정

`#momask-generator`는 `generators/momask/run_managed_generation.py`를 통해 MoMask 모션을 새로 추론하고, 대기에만 `normalize_standing_arms.py` 보정을 적용한다. 위의 기존 보행 리그 재렌더 경로와 별도다. 기준 모델은 `generators/animation/config/anny_model_baseline.yaml`이 선택한 **anny-39eab167-v1**이며 원본 생성 ID는 `39eab167`이다.

### 대기 모션 프롬프트

현재 실행 프롬프트 원문은 다음과 같다.

```text
A person stands.
```

뜻은 “사람이 서 있다”이며, 관리 원본은 [`standing-loops-v1.json`](../generators/momask/config/standing-loops-v1.json)의 `actions.standing.prompt`이다. `run_managed_generation.py`가 이 값을 읽어 MoMask 추론에 전달한다. 관리도구에서는 고정 스크립트로 표시하며 사용자가 수정하지 않는다.

프롬프트에는 “가볍게” 또는 호흡 표현을 추가하지 않는다. 가슴 후방 회전 10°와 위팔 18°·아래팔 10° 벌림은 텍스트 지시가 아니라 생성 후 대기 보정 및 ANNY 리타기팅으로 적용한다. 입력 모션은 16프레임이며, 4fps·4초로 재생한다.

### 현재 보정값

관리 원본은 [`standing-corrections.yaml`](../generators/momask/config/standing-corrections.yaml)이다. 관리도구의 **대기 모션 보정값** 펼치기도 이 파일을 읽는다.

| 항목 | 설정 키 | 현재 값 |
|---|---|---|
| 원천 상체 전방 기울기 제한 | `max_torso_pitch_degrees` | 1° |
| 위팔 바깥 벌림 | `upper_arm_outward_degrees` | 18° |
| 아래팔 바깥 벌림 | `forearm_outward_degrees` | 10° |
| 가슴 후방 호흡 회전 | `chest_backward_rotation_degrees` | 최대 10° |

- 대기는 **16프레임, 4fps, 4초 루프**이며 프레임 샘플링 없이 모두 렌더한다. 선택한 네 방향에 동일 모션을 투영한다.
- 골반의 수평 이동과 양발 지지점은 첫 프레임 기준으로 고정한다. 상체 기준 위치를 안정화한 후 호흡을 적용한다.
- 가슴 아래 HumanML3D 관절 6을 중심으로 가슴·목·머리·어깨를 뒤로 회전한다. 회전량은 `(1 - cos(phase)) / 2` 곡선으로 0° → 10° → 0°를 따른다. 마지막 프레임은 첫 프레임의 중복이 아니며 반복 재생 시 이어진다.
- 별도의 어깨 상하 이동이나 전신 상하 흔들림은 추가하지 않는다. 회전에 따른 어깨·머리 위치 변화는 남는다.
- 팔은 가슴 회전을 복제하지 않는다. 위팔 18°·아래팔 10°의 내린 방향을 유지하고 어깨 위치 이동만 따라가며, 팔 길이를 유지한다.

### ANNY 가슴 리타기팅

`render_anny_frames.py`는 모션 옆의 `standing-corrections.yaml` 기록이 있는 경우 대기 전용 척추 매핑을 적용한다. 골반에서 가슴까지의 전체 기울기로 호흡을 희석하지 않고, **관절 6→9의 첫 프레임 대비 회전**을 전달한다.

| ANNY 본 | 적용 |
|---|---|
| `spine01`, `spine02` | 가슴 상대 회전 100% |
| `spine03` | 가슴 상대 회전 50% |
| 나머지 척추 본 | 기준 회전 유지 |

OpenPose와 ANNY는 같은 보정 모션을 사용하지만 서로 다른 골격이므로 표면 움직임이 완전히 같지는 않다. 관절 회전 검증과 실제 재생 검수를 함께 수행한다.

### 기록과 검증

보정 설정은 실행별 `motion-run/motion/standing-corrections.yaml`에 저장한다. 모델 ID·해시는 `result/anny/baseline-model.json` 및 결과 JSON에 남는다. 관리도구 작업은 현재 `.tmp/momask-generator/jobs/<생성 ID>/`에 누적되며 기존 결과는 새 보정으로 덮어쓰지 않는다. 별도 실험은 `.tmp/test/<실험명>/<한국시간>/`에 보관한다.

검증 실행: `2026-09-24_20-31-23-13336ffa`.

- 원본 16프레임 × 4방향 생성 완료, ANNY 기준 모델 `anny-39eab167-v1` 확인.
- 보정 관절의 가슴 회전 범위 약 10°, 팔 벌림 각도 변화는 수치 오차 수준.
- ANNY 1·9프레임 본 행렬 비교: `spine01/02` 약 9.99°, `spine03` 약 5.00°, `spine05` 0°.
- 이 검증은 회전 전달 확인이며 최종 모션의 자연스러움에 대한 사용자 승인을 대신하지 않는다.

이전의 전신 상하 이동·가슴 상하/전후 이동량 보정은 현재 사용하지 않는다. 보정값 변경 후에는 새 생성 이력에서 결과를 확인한다. GPU 추론과 Blender CUDA 렌더는 샌드박스 밖에서 실행한다.

## 재사용 대기 에셋

선택 이력 `2026-09-24_21-58-55-a17ffc87`는 `assets/motion-sheet/momask-standing-v3`로 등록했다. 향후 포즈 생성에서는 `generators/animation/config/default_standing_motion.yaml`의 모션·OpenPose 경로를 사용한다. 관리도구 대기 페이지도 이 선택 설정을 따른다. 독립 OpenPose 플레이어는 폐기했으며 생성 결과는 MoMask 생성기에서 재생한다. 모션은 보정 적용본이며 원본 이력의 파일을 덮어쓰지 않는다.

## 심호흡 생성

심호흡은 대기와 별도의 MoMask 프롬프트를 사용하고 보정·리타기팅 경로는 공유하며, `deep-breath-corrections.yaml`에서 가슴 후방 회전을 **15°**로 확대한다. 심호흡의 팔 벌림은 위팔 25°·아래팔 15°이며, 대기는 위팔 18°·아래팔 10°를 유지한다. 골반·발 고정은 동일하다. **32프레임·4fps·8초**, 선택한 4방향 전체를 샘플링 없이 렌더한다. 관리도구의 심호흡 보정값 펼치기는 해당 설정을 표시한다.

실행별 `motion-run/motion/standing-corrections.yaml`은 공용 보정기의 적용값 사본이므로, 심호흡 실행에서는 15°가 기록된다. 기존 대기 에셋과 이전 심호흡 결과는 변경하지 않는다.

심호흡 실행 프롬프트 (`actions.deep_breath.prompt`):

```text
A person starts in a neutral standing posture with both arms relaxed at the sides, takes a deep breath in and out, then returns to the same neutral standing posture.
```

대기의 `A person stands.`와 구분한다. 32프레임·가슴 후방 회전 15°·위팔 25°·아래팔 15° 설정은 유지한다.

## ANNY 손 자세

신규 ANNY 렌더는 양손에 주먹 자세(`fist-v3`)를 적용한다. `anny_hand_pose.py`에서 손바닥 안쪽 방향을 계산해 검지부터 소지까지 각 마디를 85°·90°·45°, 엄지는 50°·40°·30° 굽힌다. 손가락 30개 본에 로컬 회전을 적용한다. 스트레칭은 처음 20% 구간에서 손을 쥐고 중간에 유지한 뒤 마지막 20%에서 손을 편다. 전환에는 smoothstep을 사용하며 나머지 동작은 주먹을 유지한다. 생성 결과 JSON에 `hand_pose`를 기록한다.

HumanML3D 22관절과 현재 COCO18 신체 포즈 맵에는 손가락 관절이 없으므로 주먹 표현은 ANNY 리그와 렌더에 적용된다. 기존 생성 이력과 등록 에셋은 변경하지 않으며 새 렌더부터 적용한다.

## 스트레칭 리타기팅 검수

쇄골과 어깨 본은 HumanML3D의 쇄골→어깨(13→16, 14→17) 방향을 전달한다. 팔을 올릴 때 위팔만 회전하던 경로를 수정하고 ANNY Armature의 체적 보존을 켠다.

생성 원본의 시작·종료에서 양손이 어깨보다 15cm 이상 낮지 않으면 품질 경고를 기록하고 렌더를 계속한다. 관리도구 상태와 결과 JSON의 `quality_warnings`에 표시하며 원본을 보존한다. 이 검사는 최소 자세 조건이며 자연스러움 전체를 보장하지 않는다. 스트레칭은 원본 120프레임 전체를 샘플링 없이 출력한다. 모델 기준 20fps에서 6초이며 관리도구 기본 재생 속도 4fps에서는 30초이다.

## ANNY 손·관절 변형 보정

`fist-v3`는 엄지 첫 마디를 다른 손가락 뿌리 쪽으로 대립시키며, 끝마디의 과도한 굽힘을 줄인다. `elbow-plane-limited-v1`는 팔꿈치 굽힘 평면으로 팔의 축 회전을 보완하되 보정량 ±25°, 프레임당 변화 5° 이내로 제한한다. 팔을 편 구간은 이전 평면을 사용한다. 원본 관절 방향·프레임 수는 유지한다.

체적 보존 스키닝 뒤 Corrective Smooth(계수 0.5, 4회, 길이 가중)를 적용해 접힘을 완화한다. 기준 모델의 가중치·체형 원본은 수정하지 않고 생성된 Blender 리그에 후처리를 보존한다. GLB 사용처는 Blender 수정자 지원이 다를 수 있으므로 동일한 표면 결과를 보장하지 않는다. 결과에는 손 자세·팔 리타기팅·스키닝 버전을 기록한다.

검증: 120프레임 팔 방향 보존, 보정량·프레임 변화 제한 확인. 시작·팔 올림·복귀·종료의 진단 렌더 확인. 완전한 자연스러움이나 손가락 관통 방지를 보장하는 IK/충돌 보정은 아니다.

## GUI·CLI 공용 실행

생성·이력·로그·취소는 [관리도구 통합 클라이언트](management-clients.md)를 사용한다. 웹 GUI와 `python3 tools/manager.py command momask ...`는 같은 작업 서비스를 호출하고 같은 생성 ID와 기록 경로를 공유한다.

## 스트레칭 내·외회전 보정

`generators/momask/config/stretch-arm-corrections.yaml`을 스트레칭 생성에만 전달한다. 추가 축 회전 적용 비율 0.4, 위팔 ±8°, 아래팔 ±12°, 프레임당 변화 2°로 제한한다. 이는 전체 관절 회전각이나 팔을 올리는 각도의 제한이 아니라 팔꿈치 평면에서 추정한 추가 축 회전 보정의 제한이다. 다른 동작은 기존 값을 유지한다. 실행별 `result/anny/arm-corrections.json`과 ANNY 결과 JSON에 적용값을 보존하고 GUI의 스트레칭 보정값 펼치기에서 현재 설정을 확인한다.

`2026-09-25_09-31-33-f319ece9` 원본의 40·45·50프레임을 비교 렌더하고 전체 120프레임의 축 회전 한도와 프레임 변화 제한을 검증했다. 원본 이력은 변경하지 않으며 새 생성부터 적용한다.

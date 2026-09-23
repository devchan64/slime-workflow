# ANNY 마네킹 생성·재현 워크플로우

## 보관 원본

`assets/motion-sheet/mannequin-walk-v3/`는 승인된 손·발 확대 모델의 재사용 제작 자산이다. 입력, 기준 리그, 재현 코드, 모션, 32프레임, 검증 기록과 파일 해시를 함께 보관한다. v1·v2는 유지한다.

- `inputs/attributes.json`: ANNY 도구의 JSON 계약 그대로 보관한 전체 phenotype·local changes·104본 local-ref 포즈.
- `inputs/anny-rest-rig.npz`: 원본 생성 배열 비교용. 이름과 달리 사용자 입력 포즈가 적용된 정점·본 행렬이다.
- `inputs/anny-reference-fit-rig.blend`: 승인한 정적 리그.
- `inputs/mannequin-motion.npz`, `inputs/artifact.json`: v1의 25프레임 닫힌 보행 루프와 해시. MoMask `walk-travel/v1`에서 파생되었다.
- `generate_attributes.py`, `build_preview.py`: CUDA ANNY 생성, Blender 리그 구성·정면/측면 렌더.
- `retarget_loop.py`, `render_asset.py`, `package_asset.py`: 모션 대응, 4방향 렌더, 관절 투영 및 시트 패킹.
- `validate_roundtrip.py`, `run_stage.py`: GLB 재수입 검증과 단계 실행.
- `review/`: 사용자 검수에 사용한 정면·측면 이미지.

## 입력과 v3 변경

좌우 `hand-scale-incr=0.5`, 좌우 `foot-scale-incr=0.75`를 적용했다. 0.5·0.75는 ANNY 변형 강도이며 실제 길이 증가율이 아니다. 다른 체형·포즈는 v2 기준과 같다. 목 높이 0.5, 허벅지·종아리 길이 0.7을 유지한다. 등신은 지정값을 강제하지 않고 생성 정점에서 측정하며 이번 결과는 약 5.639등신이다.

`phenotype_kwargs`는 0~1, `local_changes_kwargs`는 -1~1이며 실제 모델의 허용 라벨을 검증한다. `age`는 정규화 속성이므로 숫자를 연령으로 직접 해석하지 않는다. 알 수 없는 필드·중복 JSON 키·비정상 회전 행렬·CUDA 부재는 즉시 실패한다.

## 실행 환경

저장소 루트에서 실행한다. ANNY 0.6.0은 `.local/anny-runtime`, 가중치 캐시는 `.model/anny`를 사용한다. 모델 다운로드 파일은 에셋에 포함하지 않는다. Python 3.12 환경 `.venv`에는 PyTorch 2.11.0+cu128, NumPy, Pillow가 필요하다. Blender용 `.local/blender-runtime/bin/python`은 Python 3.11, bpy 4.5.3, NumPy 1.26.4 환경이다. CUDA GPU가 필수이며 GPU 확인·생성·렌더는 샌드박스 밖에서 실행한다. CPU 추론으로 대체하지 않는다. ANNY 라이선스는 에셋의 `ANNY-LICENSE.txt`를 따른다.

```bash
.venv/bin/python generators/animation/reproduce_anny_mannequin.py
```

실행기는 등록 파일의 SHA-256을 확인하고 새 `.tmp/anny-mannequin-replay/한국시간/`에 입력과 코드를 복사한다. 등록 자산을 덮어쓰지 않는다. 단계별 로그·5초 heartbeat와 성공/실패 `reproduction-validation.json`을 남긴다. 실패 시 명령과 로그 끝부분을 출력한다.

## 제작 순서

1. 전체 파라미터와 local-ref 포즈로 CUDA ANNY를 실행한다. 리그는 ANNY104, 토폴로지는 ANNY, 스키닝은 LBS다. 모델 배열을 보관 원본과 비교한다.
2. 정점·포즈 본 행렬·최대 9개 가중치를 Blender에 옮긴다. 검수 출력은 전신 높이 1.6m로 균일 정규화한다. 비균일 체형 후보정은 하지 않는다. 정면·측면을 검수하고 체형 변경은 먼저 native ANNY 입력에서 수행한다.
3. 같은 MoMask 파생 25프레임 루프를 새 본 길이와 체형에 대응시킨다. 원본 가중치를 유지하고 프레임별 표면 최저점을 지면에 맞춘다. 발 고정 IK는 적용하지 않는다.
4. 20fps의 0,3,6,9,12,15,18,21 프레임을 4방향에서 렌더한다. 총 32장, 방향별 8장, 150ms 간격, 1.2초 루프다. 시트는 2048×1024, 4열×2행이다.
5. 동일 카메라에서 리그 관절을 투영한다. OpenPose 검출 결과가 아니며 COCO18 호환 몸통·사지 14점만 사용한다. 머리 중심이 코를 대신하고 눈·귀·손가락·발가락 검출점은 포함하지 않는다.
6. GLB를 다시 불러 1·7·13·19·25 프레임 표면 오차가 0.0001m 이하인지 검사한다. 모션 배열 재현 오차 0.000001m 이하, 루프 끝점과 32프레임 수를 확인한다.

정식 채택 시에만 새 불변 버전 폴더, manifest·해시와 선택 설정을 함께 보관한다. 바이너리 바이트 일치 대신 모델 배열·모션 수치로 재현성을 검증한다. Blender 파일 메타데이터나 GPU 렌더 픽셀은 환경에 따라 달라질 수 있다.

## 검증의 범위

형태·데이터 재현과 GLB 변환 검증은 동작의 자연스러움이나 AnyPose 인식률을 보증하지 않는다. 손발 확대의 인식률 개선은 동일 캐릭터·프롬프트·시드·카메라로 별도 비교해야 한다. 현재 v3는 포즈 참조용이며 목 독립 회전, 발 미끄러짐, 극단 자세 충돌 및 게임 런타임 품질은 별도 검수 대상이다.

## 이번 재현 결과

2026-09-23 전체 재실행 통과. 정점·면·본 행렬·계층·이름·가중치·인덱스 배열이 보관 원본과 정확히 일치했다. 재생성한 모션은 허용 오차 1e-6 이내이며 32프레임과 GLB 5개 자세 검증을 완료했다. 증빙은 `assets/motion-sheet/mannequin-walk-v3/reproduction-validation.json`과 `roundtrip-validation.json`에 보관한다.

## v4 명암 개선 버전

`assets/motion-sheet/mannequin-walk-v4/`는 v3의 모델·리그·모션을 유지하고 카메라 기준 조명으로 32프레임을 다시 렌더한 버전이다. `lighting-profile.yaml`에 설정을 기록하며 실제 적용은 `render_asset.py`가 담당한다. 정적 체형 검수 사본과 명암 개선 비교 이미지는 README의 설명을 따른다. 기본 재현 실행은 v4이며 v3는 다음 명령으로 계속 재현할 수 있다.

```bash
.venv/bin/python generators/animation/reproduce_anny_mannequin.py --asset-version 3
.venv/bin/python generators/animation/reproduce_anny_mannequin.py --asset-version 4
```

v4의 GLB·Blender 기하 및 모션 원본은 v3와 바이트 단위로 동일하고, 모션 배열·투영 관절도 일치한다. 원본 3D 파일을 여는 것만으로 개선 조명이 적용되지는 않으며 렌더 실행기가 조명을 설정한다.

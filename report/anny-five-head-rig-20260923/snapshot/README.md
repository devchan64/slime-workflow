# ANNY 5등신 리그 실험

기존 이미지 기반 마네킨과 분리한 새 실험이다. ANNY 0.6.0의 기본 `anny` 토폴로지, `anny` 리그, LBS 가중치를 사용한다. 정식 채택 전 후보이며 외형은 어린 체형에 가깝다.

## 결과

- [검수 미리보기](preview.html), [Blender](anny-five-head-rig.blend), [GLB](anny-five-head-rig.glb).
- 13,718 정점 / 27,420 삼각형 / 손발 포함 104본.
- 전신 높이 ÷ 정수리–턱 아래 수직 길이 = 5.000. 턱 기준은 고정 토폴로지 정점 5155이며 사진의 등신 표기나 머리 분할 마스크로 대체하지 않았다. 해부학적 계측 인증은 아니다.
- 기본 파라미터: gender 0.5, age 0.12, muscle 0.25, weight 0.45, height 0.5, proportions 0.5. age는 나이(년)가 아닌 정규화된 모델 입력이다.
- 머리 수직·수평·깊이 local change를 같은 값 0.9357927739620209로 설정하여 5등신을 맞췄다. 본 위치도 ANNY에서 함께 생성된다. 출력은 검수용 높이 1.6m로 균일 정규화했다.
- 수동 팔·팔꿈치·고관절·무릎 가동 확인용 25프레임 액션 포함. 기존 MoMask 보행은 아직 연결하지 않았다.

## 검증과 개선 대상

`validation.json`: 기준 자세 정점 비교와 25프레임 유한 좌표 검사. `roundtrip-validation.json`: GLB 재수입 후 1/7/13/19/25프레임 정점 최근접 거리 비교, 최대 약 9.65e-6m(기준 1e-4m) 통과.

초기에는 head 분할 마스크에 목이 포함되어 등신 기준을 턱 정점으로 보정했다. 연령만으로는 목표에 도달하지 않아 머리 local change를 병행했다. 또한 ANNY의 rest_bone_poses를 기준 자세의 vertices와 섞어 생긴 당김을 bone_poses로 교체해 수정했다. 최종 스크립트와 최종 실행 로그를 보관한다. 초기 실패 실행 로그 전체는 별도 보존하지 않았다.

이번 모델은 연속 표면이다. 구체관절 외피, 보행 리타게팅, IK 컨트롤러, 충돌·발 접지 검증, 게임용 본 축소는 미적용이다. 눈·얼굴 표현과 어린 체형의 실루엣은 미술 검수가 필요하다. 가중치는 ANNY 원본의 최대 9개 영향을 보존하므로 4개 영향만 지원하는 런타임에는 별도 변환·검증이 필요하다.

## 실행 환경과 재현

Python 3.12 + torch 2.11.0+cu128 + ANNY 0.6.0 / RTX 5070 Laptop GPU. Blender 생성은 Python 3.11 + bpy 4.5.3 + numpy 1.26.4. ANNY 패키지와 roma, warp-lang은 `.local/anny-runtime/`, 모델 파싱 캐시는 `.model/anny/`에 둔다. 의존 버전은 `environment.txt`에 기록했다.

현재 폴더의 스크립트를 새 `.tmp/anny-five-head-rig/<한국시간>/`에 복사한다. 아래 명령의 `<새 실행 폴더>`를 복사 경로로 바꾸고 저장소 루트에서 실행한다. GPU 준비·생성·렌더는 샌드박스 밖에서 실행한다.

```bash
.venv/bin/python <새 실행 폴더>/generate_model.py
.local/blender-runtime/bin/python <새 실행 폴더>/run_stage.py <새 실행 폴더>/build_preview.py
.local/blender-runtime/bin/python <새 실행 폴더>/run_stage.py <새 실행 폴더>/validate_roundtrip.py
```

각 stdout/stderr를 새 실행 폴더의 단계별 로그로 보관한다. GPU가 없으면 실패하며 CPU 추론으로 전환하지 않는다. 검사 스크립트는 원본 Blender와 GLB를 같은 폴더에서 읽는다.

## 출처

- [NAVER LABS 소개](https://europe.naverlabs.com/blog/anny-a-free-to-use-3d-human-parametric-model-for-all-ages/)
- [공식 코드](https://github.com/naver/anny), 패키지 ANNY 0.6.0 고정.
- 배포 패키지 Apache-2.0 LICENSE 사본: `ANNY-LICENSE.txt`.
- 기본 ANNY만 사용하며 SMPL/SMPL-X/SOMA 대체 토폴로지를 사용하지 않았다.

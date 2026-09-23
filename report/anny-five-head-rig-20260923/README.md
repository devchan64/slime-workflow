# ANNY 기반 5등신 리그 실험

2026-09-23 생성한 ANNY 5등신 후보의 외부 공유용 이력·결과 사본이다. 기존 이미지 기반 구체관절 실험과 별도로 보관하며 최종 채택을 의미하지 않는다.

## 결과 보기

- [다방향·가동 자세 미리보기](snapshot/preview.html)
- [Blender 원본](snapshot/anny-five-head-rig.blend) · [GLB 리그](snapshot/anny-five-head-rig.glb)
- [생성 과정·재현 명령](snapshot/README.md) · [생성 파라미터](snapshot/generation.json)
- [리그 검사](snapshot/validation.json) · [GLB 재수입 검사](snapshot/roundtrip-validation.json)

ANNY 0.6.0의 기본 토폴로지와 원본 가중치를 사용했다. 13,718개 정점, 27,420개 삼각형, 손발 포함 104개 본이다. 머리 크기 파라미터를 조정해 전신 높이 / 정수리–턱 아래 기준점의 수직 길이를 **5.000**으로 맞췄다. 턱 기준은 고정 토폴로지 정점 5155이며 해부학적 계측 인증은 아니다. 검수용 출력 높이는 1.6m다.

## 과정과 한계

1. 공식 ANNY 패키지와 CUDA 실행 환경을 준비했다.
2. 성별 중간값과 낮은 근육량을 사용하고 연령·머리 크기 파라미터를 탐색했다. 최종 age 0.12는 실제 나이가 아닌 정규화된 모델 입력이다.
3. 머리 분할 마스크에 포함된 목 부분을 측정에서 제외하고 턱 기준점으로 바꿨다.
4. 메시와 골격의 기준 자세 불일치로 발생한 당김을 `bone_poses` 기준으로 수정했다.
5. 수동 가동 검사 25프레임과 다방향 이미지를 생성하고 GLB 재수입을 검사했다.

원본 실행의 최종 코드·로그·결과를 `snapshot/`에 보존했다. 초기 실패 로그 전체는 남아 있지 않으며 위 수정 이력이 이를 대신한다. 어린 체형에 가까운 연속 표면 후보이고 구체관절 외피는 구현하지 않았다. 얼굴·눈·어깨·팔꿈치의 디자인 검수, 기존 MoMask 보행 리타게팅, IK·발 접지·충돌 검사는 미완료다. 최대 9개 본 영향을 보존하므로 대상 엔진의 스키닝 지원 범위를 확인해야 한다.

## 사본 검증과 재현 범위

[사본 재검증 기록](verification/roundtrip-validation.json)은 원래 `.tmp` 파일이 아닌 이 리포트에서 복사한 Blender·GLB를 별도 실행 폴더에서 다시 검사한 결과다. 5개 자세의 GLB 정점과 Blender 정점 간 최대 최근접 거리는 약 9.65e-6m이며 허용값 1e-4m 이내다. 이 검사는 전체 관절의 충돌 검증이나 전체 생성 과정의 재실행을 의미하지 않는다.

파일 무결성은 리포트 디렉터리에서 아래 명령으로 확인한다.

```bash
sha256sum -c checksums.sha256
```

모델부터 다시 생성하려면 `snapshot/README.md`의 환경과 명령을 따른다. `snapshot/`의 스크립트를 워크플로우 저장소의 새 `.tmp/anny-five-head-rig/<한국시간>/`에 복사해 실행한다. GPU 생성·렌더는 샌드박스 밖에서 실행한다. 원본 패키지·캐시는 사본에 포함하지 않았으므로 ANNY 0.6.0 및 명시된 의존성이 필요하다. `environment.txt`는 당시 전체 Python 환경 기록이며 최소 설치 목록은 아니다. 이번 보관에서는 GPU 생성과 렌더를 다시 실행하지 않았다.

## 출처와 보관

[공식 소개](https://europe.naverlabs.com/blog/anny-a-free-to-use-3d-human-parametric-model-for-all-ages/) · [공식 코드](https://github.com/naver/anny) · [배포 LICENSE 사본](snapshot/ANNY-LICENSE.txt)

SMPL/SMPL-X/SOMA 대체 토폴로지는 사용하지 않았다. 모델 파싱 캐시는 `.model/anny/`, 실험 원본은 `.tmp/anny-five-head-rig/2026-09-23_07-47-56/`다. PDF는 생성하지 않았다.

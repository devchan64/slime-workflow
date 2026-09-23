# mannequin-walk/v6

사용자가 승인한 ANNY r3 + 기존 MoMask 보행 + 쉐이딩 강화 리그 제작 자산이다. v2·v3·v4 폐기 상태는 유지한다.

- 원본 체형: `report/anny-reference-baseline-20260923-r3`, upperleg01.R −8°, L +8° 기준.
- MoMask 신규 추론 없음. v1에서 검증한 25프레임/20fps 보행 루프 재사용.
- 4방향 × 8샘플 = 32프레임. 샘플 간격 150ms, 루프 1.2초.
- Blender 4.5.3 / ANNY104 / 미터 / Z-up / 512×512 정사영.
- 환경광 0.035, 주광 500W·크기 0.75, 보조광 35W, 역광 160W, AgX High Contrast, Cycles CUDA 64 samples.
- 투영 OpenPose 맵은 14개 관절이며 검출기 출력이 아니다.
- 최종 이미지 관리 원본: slime-frontend의 `public/assets/characters/mannequin-walk-v6/`.
- 이 경로의 프레임·시트는 AnyPose 등 제작 입력으로 재사용하는 해시 고정 사본이다. 게임 런타임 채택과 기본 생성기 선택은 별도이다.

## 재현

이 디렉터리를 새 실험 폴더로 복사한 뒤 저장소 루트에서 실행한다. 등록된 v5 원본을 덮어쓰지 않는다.

```bash
.local/blender-runtime/bin/python <실험폴더>/run_stage.py <실험폴더>/retarget_loop.py
.local/blender-runtime/bin/python <실험폴더>/run_stage.py <실험폴더>/render_asset.py
.venv/bin/python <실험폴더>/package_asset.py
```

CUDA 단계는 샌드박스 밖에서 실행한다. 조명은 render_asset.py가 설정하며 보관된 blend 자체에 저장되어 있지 않다. inputs에는 재현에 필요한 정적 r3 리그와 모션·속성·입력 해시가 보관된다. source-manifest.json의 임시 경로는 과거 출처 기록이며 실행 의존성이 아니다.

loop-validation.json은 이번 32프레임 실행 결과이고, roundtrip-validation.json 및 baseline-preservation.json은 같은 리그를 만든 8프레임 실행에서 확인한 기록이다. ANNY 라이선스는 ANNY-LICENSE.txt를 참조한다.

## v6 변경

v5의 모션·리그·쉐이딩을 유지하고 수평각만 45°로 변경했다. 카메라 XY 절댓값 sqrt(26), 높이 3m, 주시점 0.8m, 하향각 16.9662°, 정사영 배율 2를 유지한다. 32프레임과 OpenPose 맵을 재렌더했다. blend는 v5와 동일한 애니메이션 리그이며 v6 카메라는 render_asset.py가 설정한다. v5는 보존한다.

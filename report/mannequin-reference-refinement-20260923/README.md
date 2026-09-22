# 마네킨 체형·고관절 개선 실험 사본

2026-09-23 고관절 축소와 구체관절 개선 결과 및 추가 참고 도면을 보관한다. **검수 후보**이며 최종 디자인 승인이나 정식 에셋 등록을 의미하지 않는다. 이전 리포트는 그대로 유지한다.

- [결과 미리보기](snapshot/preview.html): 전후 비교, 고관절 상세, 보행 프레임.
- [실험 과정과 수정 이력](snapshot/README.md), [출처·파라미터](snapshot/provenance.yaml).
- [Blender 편집 원본](snapshot/rigged-mannequin.blend), [리그 GLB](snapshot/rigged-mannequin.glb).
- [고관절 스케치](snapshot/inputs/hip-joint-reference.jpg), [BJD 기구 설명](snapshot/inputs/hip-joint-mechanisms.jpg), [소켓 도면](snapshot/inputs/hip-socket-blueprint.jpg), [전신 관절 도면](snapshot/inputs/body-joint-blueprint.jpg), [탄성 줄 도면](snapshot/inputs/joint-elastic-routing.jpg).
- 기준 모델·모션·3방향 참조와 제작 스크립트, 로그는 `snapshot/`에 함께 보관했다. 중간 버전 전체 바이너리는 복제하지 않았으며 수정 이력과 주요 비교 이미지를 남겼다.

## 결과와 한계

고관절 구체 부피를 과대했던 중간안 대비 약 32% 축소하고, 골반 소켓과 허벅지 외피를 재구성했다. 고관절 가중치 혼합을 제거하여 골반과 허벅지를 분리 구동한다. 30개 메시, 24개 본, 97,088개 삼각형이며 25프레임 리그 검사와 GLB 검사를 통과했다.

정면 투영 외곽 IoU는 88.19% → 90.73%로 증가했으나 측면은 88.61% → 88.11%, 후면은 88.88% → 85.94%로 감소했다. 이는 전체 디자인 유사도 점수가 아니다. 얼굴 접합·골반 굴곡·후면 외곽은 추가 개선 대상이다. 수동 굽힘·벌림 이미지는 모든 각도에서의 충돌 검증이 아니며 실물 탄성 줄·이중 관절 기구는 구현하지 않았다.

## 사본 재현

Python 3.11, bpy 4.5.3, numpy 1.26.4, Pillow 12.3.0 환경에서 리포트 폴더를 현재 디렉터리로 사용한다.

```bash
python reproduce.py --verify-only
python reproduce.py --output /새로운/작업경로/.tmp/mannequin-report-reproduction/YYYY-MM-DD_HH-mm-ss
```

출력 폴더는 기존에 없어야 한다. 사본의 입력만으로 체형 보정 → 관절·리그 구성 → GLB export → 25프레임 검증을 실행한다. AI 추론과 렌더는 재실행하지 않는다. 렌더를 포함한 원래 절차는 `snapshot/README.md`를 참고한다.

GLB 구조·좌표·가중치·애니메이션과 모션 NPZ를 비교한다. 삼각형 순서는 정규화하되 연결과 winding은 같아야 한다. 수치 허용 오차는 1e-6, 노멀 성분은 1e-4다. 따라서 파일 바이트 동일성과 수치 동등성은 구분한다. `checksums.sha256`은 보관 파일 전체의 무결성을 검사한다.

## 사본 검증 결과

[실제 재현 기록](verification/reproduction-result.json): 2026-09-23 07:44 KST 새 폴더에서 재생성 및 검증 통과. GLB accessor 253개를 비교했으며 좌표·가중치·모션·노멀 최대 오차는 모두 0이었다. 삼각형 accessor 13개의 저장 순서는 달랐지만 연결과 winding은 같았다. 따라서 GLB SHA-256은 다르며 바이트 동일한 재생성을 주장하지 않는다. 25프레임 검사와 GLB 계약 검사도 통과했다. 검증 로그는 `verification/`에 보관한다.

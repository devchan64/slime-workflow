# mannequin-walk v4 — ANNY 기준 모델

사용자 지정 기준 모델의 104본 리그와 4방향 × 8프레임(32프레임) OpenPose 제작 자산. 기존 v1·v2·v3는 보존한다.
- 기준 모델: 목 높이 0.5, 허벅지·종아리 길이 0.7, 약 5.639등신. 입력 파라미터·기준 Blender 사본은 inputs/.
- 모션: 기존 mannequin-walk/v1의 25프레임 닫힌 루프를 새 ANNY 체형에 다시 리타게팅. 원천은 walk-travel/v1 MoMask 모션이다.
- mannequin.blend/glb: 104본, 20fps, 프레임 1~25(마지막은 루프 중복 끝점).
- mannequin-motion.npz: 새 ANNY 리그에서 추출한 HumanML3D22 대응 관절 위치, y-up 미터. rest는 새 체형이다. contacts는 기존 모션의 접촉 추정치를 승계했으며 새 표면 접촉 보증이 아니다.
- 방향별 preview-0001~0008.png / openpose-0001~0008.png: 512×512, 원본 0,3,6,9,12,15,18,21 표본, 150ms 간격, 1.2초 주기.
- pose-sheets/ 및 rig-sheets/: 2048×1024, 4열×2행, row-major.
- OpenPose는 검출 결과가 아닌 MoMask 기반 ANNY 관절 투영. 기존 계약과 같이 COCO18 호환 몸통·사지 14점이며 머리 중심이 코를 대신하고 눈·귀는 생략한다. 관절 가림은 제거하지 않는다.
- 루프 끝점·GLB 5프레임 재수입 검증 통과. 원본 가중치 유지. 발 고정 IK·목 독립 회전·극단 자세 충돌은 미검증이며 포즈 참조용 등록이 게임 런타임 품질 승인을 뜻하지 않는다.

## 재현
이 폴더의 inputs/와 Python 스크립트를 새 .tmp/anny-pose-asset-v4/한국시간/ 경로에 복사한다. 보관 자산을 직접 덮어쓰지 않는다.
1. Blender Python 3.11(bpy 4.5.3, NumPy): run_stage.py retarget_loop.py
2. CUDA Blender: run_stage.py render_asset.py
3. Pillow Python: package_asset.py
4. Blender: run_stage.py validate_roundtrip.py

ANNY 라이선스는 ANNY-LICENSE.txt. 외부 모델 가중치·비공개 프롬프트는 포함하지 않는다.

## v3 변경

좌우 `hand-scale-incr=0.5`, `foot-scale-incr=0.75`. ANNY 변형 강도이며 실제 크기의 증가율이 아니다. 다른 체형·입력 포즈는 v2와 동일하다. 검수 이미지는 review/. 모델 원본 재생성과 전체 절차는 ../../../workflows/anny-mannequin-generation.md 참고.

## v4 명암 개선

v3 손 0.5·발 0.75 체형, 리그, 모션, 카메라를 그대로 유지하고 32프레임 셰이딩을 변경했다. 환경광 강도 0.12, 카메라 기준 주광 420W/1.2m, 보조광 65W/2.5m, 윤곽광 180W/1.8m, AgX Medium High Contrast, CUDA 48samples·denoising. 상세 설정은 lighting-profile.yaml, 실제 적용 코드는 render_asset.py. mannequin.blend는 v3의 기하·모션 원본이며 개선 조명은 render_asset.py 실행 시 적용된다. review/front.png와 side.png는 v3 체형 승인 사본이며 개선 조명 비교는 review/lighting-comparison.jpg이다.

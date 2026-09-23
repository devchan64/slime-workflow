# mannequin-walk v2 — ANNY 기준 모델

사용자 지정 기준 모델의 104본 리그와 4방향 × 8프레임(32프레임) OpenPose 제작 자산. 기존 v1은 보존한다.
- 기준 모델: 목 높이 0.5, 허벅지·종아리 길이 0.7, 약 5.625등신. 입력 파라미터·기준 Blender 사본은 inputs/.
- 모션: 기존 mannequin-walk/v1의 25프레임 닫힌 루프를 새 ANNY 체형에 다시 리타게팅. 원천은 walk-travel/v1 MoMask 모션이다.
- mannequin.blend/glb: 104본, 20fps, 프레임 1~25(마지막은 루프 중복 끝점).
- mannequin-motion.npz: 새 ANNY 리그에서 추출한 HumanML3D22 대응 관절 위치, y-up 미터. rest는 새 체형이다. contacts는 기존 모션의 접촉 추정치를 승계했으며 새 표면 접촉 보증이 아니다.
- 방향별 preview-0001~0008.png / openpose-0001~0008.png: 512×512, 원본 0,3,6,9,12,15,18,21 표본, 150ms 간격, 1.2초 주기.
- pose-sheets/ 및 rig-sheets/: 2048×1024, 4열×2행, row-major.
- OpenPose는 검출 결과가 아닌 MoMask 기반 ANNY 관절 투영. 기존 계약과 같이 COCO18 호환 몸통·사지 14점이며 머리 중심이 코를 대신하고 눈·귀는 생략한다. 관절 가림은 제거하지 않는다.
- 루프 끝점·GLB 5프레임 재수입 검증 통과. 원본 가중치 유지. 발 고정 IK·목 독립 회전·극단 자세 충돌은 미검증이며 포즈 참조용 등록이 게임 런타임 품질 승인을 뜻하지 않는다.

## 재현
이 폴더의 inputs/와 Python 스크립트를 새 .tmp/anny-pose-asset-v2/한국시간/ 경로에 복사한다. 보관 자산을 직접 덮어쓰지 않는다.
1. Blender Python 3.11(bpy 4.5.3, NumPy): run_stage.py retarget_loop.py
2. CUDA Blender: run_stage.py render_asset.py
3. Pillow Python: package_asset.py
4. Blender: run_stage.py validate_roundtrip.py

ANNY 라이선스는 ANNY-LICENSE.txt. 외부 모델 가중치·비공개 프롬프트는 포함하지 않는다.

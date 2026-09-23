# ANNY 목 둘레 추가 보정 결과

이번 모델의 외부 공유·재현 확인용 사본이다. 정식 게임 에셋 채택은 별도다.

[전후 비교와 60% 오버레이](snapshot/preview.html) · [Blender 모델](snapshot/anny-reference-fit-rig.blend) · [GLB 리그](snapshot/anny-reference-fit-rig.glb)

## 과정과 결과

사용자 제공 ANNY 파라미터(gender 1, age 0.4, muscle 1, weight 0, height 0.3, proportions 0)로 생성한 모델을 5등신 레퍼런스에 후보정했다. age 0.4는 정규화된 파라미터이며 실제 나이 0.4세를 뜻하지 않는다.

1. 08:45 후보: 5등신 비율과 팔·다리 위치 피팅.
2. 08:51 후보: 어깨 폭 축소와 고관절 높이 상승.
3. 08:55 후보: 목·흉곽 단면 축소, 오버레이 60% 적용.
4. 09:21 이번 후보: 직전 모델의 목 가로·깊이를 중심부에서 최대 15% 추가 축소하고 턱·어깨 방향으로 가우시안 감쇠. 흉곽 보정·관절 위치·스킨 가중치 유지.

15%는 중심부 축소 계수이며 목 전체 둘레의 측정 감소율은 아니다. 결과는 약 5등신, 104본, 27,420 삼각형이다. 구체관절 레퍼런스에 피팅한 연속 표면 모델이며 외피 자체의 구체관절 분할을 구현한 결과는 아니다.

## 보관 및 검증 범위

`snapshot/`은 이번 실행의 입력, 결과, 렌더, 스크립트와 원본 로그 사본이다. `inputs/anny-rest-rig.npz`에는 이번 단계 직전의 모델·리그가 들어 있다. 원본 ANNY 생성과 이전 피팅 단계 전체의 재실행은 이 리포트의 재현 범위 밖이다.

원래 실행에서 25프레임 좌표 검사와 GLB 재수입 5개 자세 검사를 통과했다. 리포트 보관 시 사본의 입력·스크립트로 목 보정을 재실행하여 모든 NPZ 배열이 원본 결과와 완전히 일치함을 확인했다(`verification/verification.json`). GPU 렌더 전체를 다시 실행하지는 않았다. 디자인 일치도, 극단 자세 충돌·접지는 검증하지 않았다.

## 재현

Python 3.12 + NumPy로 목 보정을 실행한다. 리그·렌더에는 별도의 Python 3.11 + bpy 4.5.3 + NumPy 1.26.4 및 CUDA 렌더 환경이 필요하다. ANNY 추론부터 다시 하지 않으므로 모델 가중치는 필요 없다. 라이선스는 `snapshot/ANNY-LICENSE.txt`에 보관했다. 제공 레퍼런스의 재배포 권리는 이 기록으로 부여되지 않는다.

`snapshot/`을 새 `.tmp/anny-neck-refinement/<한국시간>/`로 복사한 후 그 디렉터리에서 실행한다. 아래 python은 각 단계에 맞는 환경의 실행기를 사용한다. GPU 렌더는 샌드박스 밖에서 실행한다.

```bash
python reduce_circumference.py > reduce.log 2>&1
python run_stage.py build_preview.py > build.log 2>&1
python run_stage.py validate_roundtrip.py > roundtrip.log 2>&1
```

HTML은 생성된 `overlay-front.png`를 레퍼런스 위에 60% 불투명도로 표시한다. 정적 `overlay-result.png`는 동일 비율의 알파 합성 사본이다.

사본 무결성은 이 리포트 폴더에서 `sha256sum -c checksums.sha256`으로 확인한다. PDF는 생성하지 않았다.

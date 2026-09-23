# MoMask 리그 렌더 기준

현재 기준은 mannequin-walk/v6이다. 기존 MoMask 보행과 ANNY r3 리그를 재사용하고 수평 45°, 하향 16.9662°, 정사영 배율 2로 4방향 × 8프레임을 만든다. 모션 신규 추론은 수행하지 않는다.

```bash
.venv/bin/python generators/animation/render_momask_rig.py
```

CUDA가 필요한 실행은 샌드박스 밖에서 수행한다. 기본 리그 선택기는 default_walk_rig.yaml이며 등록 에셋의 해시를 검증한다. 고정 버전의 렌더 코드를 새 .tmp 폴더에 복사해 실행하므로 기존 에셋을 덮어쓰지 않는다. 완료 후 32프레임 검수 시트와 GIF가 생성된다. v5는 이전 버전으로 보존한다. 구형 자체 리그 렌더 경로는 폐기했으며 현재 진입점은 render_momask_rig.py이다. AnyPose 기본 참조 선택은 별도 설정이다.

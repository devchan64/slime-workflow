# Kimodo NF4 모션 생성기

관리 페이지: `/management/frame/kimodo-generator/?tool=kimodo-generator&category=animation-tool`.
GUI·`tools/manager.py command kimodo`는 공용 게이트웨이와 GPU 대기열을 사용한다.

- 모션: `nvidia/Kimodo-SOMA-RP-v1.2`, 원본 FP32.
- 텍스트: 커뮤니티 `matbee/kimodo-llm2vec-nf4`, NF4 저장·BF16 CUDA 연산. 공식 LLM2Vec의 양방향 attention·평균 풀링·supervised adapter를 사용한다.
- 인코딩을 마친 뒤 인코더를 해제하고 모션 모델을 CUDA로 로드한다. CPU 추론 대체는 없다.
- 기본값: 90프레임, 30fps, DDIM 100스텝, 텍스트 CFG 2, 초기 방향 0도, 시드 42, 후처리 해제. 2스텝은 실행 확인용이다.
- 30~300프레임을 입력받으며 모든 길이의 8GB 실행·품질을 보장하지 않는다. 초기 방향은 이후의 방향을 고정하지 않는다.
- 모션 생성 후 ANNY 중성형 v4 리그 적용과 CUDA 렌더를 자동 실행한다. 결과 MP4는 ANNY 512×512·30fps 정사영 영상이다. ZIP에는 PNG 프레임과 SOMA 원본 `motion.npz`, `skeleton.json`, 원본 관절 영상 `joint-preview.mp4`, 프롬프트·임베딩, ANNY `mannequin.glb`·`mannequin.blend`, 변환 검수 기록을 포함한다.
- SOMA77에서 이름으로 22개 몸통·사지 관절을 대응하고 공용 위치 기반 계산기로 ANNY에 전달한다. 기준 자세는 공식 SOMA 중립 골격이며 첫 프레임을 중립 자세로 취급하지 않는다. 좌표축·체형 배율을 변환하고 루트 이동을 유지한다. 목·머리는 `config/anny-rotation.yaml`의 대응에 따라 SOMA 전역 회전을 좌표 변환하고 ANNY 기준 본 축에 적용한다. 이후 목 시작점에서 머리까지의 체인 방향을 SOMA `Neck1 → Head`에 맞춘다. ANNY 체인 길이와 내부 로컬 자세를 유지하는 회전 정렬이며, 머리 전역 회전은 별도로 유지한다. 체형 차이 때문에 가슴 기준 머리 절대 위치까지 일치시키지는 않는다. 목 위치만으로 머리 회전을 추정하지 않는다. 손가락 세부 회전·발 접지·피부 충돌 보정은 적용하지 않는다. 출력 품질은 검수 대상이다.
- ANNY 단계가 실패하면 전체 작업을 실패로 기록한다. 관절 영상으로 조용히 대체하지 않는다. 기존 완료 이력은 덮어쓰지 않는다.

## 자료와 실행 환경 준비

모델 파일은 `.model/kimodo/`, 고정 공식 소스는 `.local/kimodo/upstream/`, 전용 환경은 `.venv-kimodo/`에 둔다. `config/assets.yaml`의 리비전과 LFS SHA-256을 확인한다. 기본 입력 원본은 추적 파일 `config/defaults.yaml`이다. 준비·설치는 GPU 접근이 가능한 샌드박스 밖에서 실행한다.

```bash
.venv/bin/python -m generators.kimodo.prepare
uv venv --python .venv/bin/python .venv-kimodo
uv pip install --python .venv-kimodo/bin/python --index-strategy unsafe-best-match --extra-index-url https://download.pytorch.org/whl/cu128 -r generators/kimodo/requirements.txt
PATH="$PWD/.venv-kimodo/bin:$PATH" uv pip install --python .venv-kimodo/bin/python --no-build-isolation .local/kimodo/upstream
```

ANNY 렌더에는 기존 `.local/blender-runtime/bin/python` 환경과 추적된 `assets/animation-models/anny-neutral-v4` 리그가 필요하다. `config/anny-render.yaml`·`anny-retarget.yaml`에 매핑과 렌더 기준값을 고정한다. 공용 리타게팅 코드의 `generators/momask` 경로는 과거 명칭이며 MoMask 모델을 실행하지 않는다.

공식 패키지 설치에는 C++ 컴파일러와 CMake가 필요하다. 준비 로그는 `.tmp/test/kimodo-prepare/`에 5초 heartbeat와 함께 저장된다. 고정 리비전 자료를 오프라인으로 읽으며 모델 선택 입력은 허용하지 않는다. 모델 상태의 ‘파일 준비 완료’는 가중치 크기·준비 기록 확인이며 CUDA 실행 성공을 뜻하지 않는다.

## 공용 CLI

`tools/manager.py command kimodo generate --payload-file /절대경로/request.json` 요청:

```json
{"action":"generate","prompt":"A person walks forward.","frames":90,"steps":100,"seed":42,"guidance_scale":2.0,"heading_degrees":0.0,"post_processing":false,"directions":["front_left"]}
```

`status`, `logs`, `history`, `active`, `model-status`, `resume`, `prioritize`, `cancel`, `history-delete`, `history-reset`은 공용 도움말을 따른다. 작업 기록은 `.tmp/test/kimodo/<생성 ID>/`에 누적한다. 재개는 새 실행 시도로 처음부터 생성한다. 선택 삭제·전체 초기화는 관리 작업의 입력·출력·로그를 실제 삭제하며 외부 원본과 모델은 보존한다.

요청 원문은 실행 요청에, 공식 정규화 후 실제 문장과 인코더 문자열의 단어 수·SHA-256은 실행별 `prompt.json`에 저장한다. 토큰 한도를 넘으면 잘라서 생성하지 않고 실패한다. VRAM은 공용 실행기가 자식 프로세스를 포함해 측정하며 샘플링 관측 피크와 PyTorch allocated 피크를 구분한다. ETA는 공용 단계·실측 이력 기반이며 표본 부족 시 계산 중으로 표시한다.

2026-10-29 검증: 8GB GPU에서 NF4 인코더와 FP32 모션으로 30프레임/2스텝 및 90프레임/100스텝 완료. 발 후처리 활성화와 최대 300프레임은 별도 검증 대상이다. 이는 실행 검증이며 동작 품질 승인을 의미하지 않는다.

출처: [공식 코드](https://github.com/nv-tlabs/kimodo), [SOMA 모델카드](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.2), [NF4 인코더](https://huggingface.co/matbee/kimodo-llm2vec-nf4). 모델별 라이선스는 내려받은 카드·LICENSE를 따른다.

## 입력 화면

동작 예시를 선택하고 `예시 불러오기`를 누르면 프롬프트와 프레임만 변경한다. 시드·고급 설정은 유지하며 생성은 별도 대기열 확인을 거친다. 예시 원본은 `config/prompt-examples.yaml`에서 관리한다. 프레임 입력 아래에 30fps 기준 길이를 표시하고, 접수한 생성 ID·진행 상태·최신 결과는 입력 아래에 표시한다. 프롬프트와 출력 방향은 HY-Motion처럼 같은 행에 배치하고 좁은 화면에서는 세로로 전환한다. 모델 준비 상태와 확인 버튼은 접힌 기술 설명 밖에 표시한다. 기존 작업은 하단 공용 생성 이력에서 조회한다. 출력 방향은 정면·좌우 측면·후면·대각 8개 중 복수 선택한다. 방향은 카메라에만 적용하며 모션을 다시 생성하거나 회전시키지 않는다.

출력 방향 키는 `front`, `front_left`, `left`, `back_left`, `back`, `back_right`, `right`, `front_right`이며 기준 각도·라벨은 `config/output-directions.yaml`에서 관리한다. 기존 CLI 요청에서 `directions`를 생략하면 전방 좌측을 사용한다. 빈 선택·중복·알 수 없는 방향은 거절한다. 단일 방향 미리보기는 512×512, 여러 방향 미리보기는 방향당 256px 타일의 2열 동기 비교 영상이다. ZIP의 `directions/<방향>/`에는 512×512 원본 PNG·MP4를 저장한다. 선택 수에 따라 렌더 시간과 저장 용량이 증가한다.

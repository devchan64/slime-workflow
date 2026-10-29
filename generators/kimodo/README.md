# Kimodo NF4 모션 생성기

관리 페이지: `/management/frame/kimodo-generator/?tool=kimodo-generator&category=animation-tool`.
GUI·`tools/manager.py command kimodo`는 공용 게이트웨이와 GPU 대기열을 사용한다.

- 모션: `nvidia/Kimodo-SOMA-RP-v1.2`, 원본 FP32.
- 텍스트: 커뮤니티 `matbee/kimodo-llm2vec-nf4`, NF4 저장·BF16 CUDA 연산. 공식 LLM2Vec의 양방향 attention·평균 풀링·supervised adapter를 사용한다.
- 인코딩을 마친 뒤 인코더를 해제하고 모션 모델을 CUDA로 로드한다. CPU 추론 대체는 없다.
- 기본값: 90프레임, 30fps, DDIM 100스텝, 텍스트 CFG 2, 초기 방향 0도, 시드 42, 후처리 해제. 2스텝은 실행 확인용이다.
- 30~300프레임을 입력받으며 모든 길이의 8GB 실행·품질을 보장하지 않는다. 초기 방향은 이후의 방향을 고정하지 않는다.

## 자료와 실행 환경 준비

모델 파일은 `.model/kimodo/`, 고정 공식 소스는 `.local/kimodo/upstream/`, 전용 환경은 `.venv-kimodo/`에 둔다. `config/assets.yaml`의 리비전과 LFS SHA-256을 확인한다. 기본 입력 원본은 추적 파일 `config/defaults.yaml`이다. 준비·설치는 GPU 접근이 가능한 샌드박스 밖에서 실행한다.

```bash
.venv/bin/python -m generators.kimodo.prepare
uv venv --python .venv/bin/python .venv-kimodo
uv pip install --python .venv-kimodo/bin/python --index-strategy unsafe-best-match --extra-index-url https://download.pytorch.org/whl/cu128 -r generators/kimodo/requirements.txt
PATH="$PWD/.venv-kimodo/bin:$PATH" uv pip install --python .venv-kimodo/bin/python --no-build-isolation .local/kimodo/upstream
```


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



## 결과

ANNY 리타게팅·Blender 렌더 기능은 폐기했다. 신규 작업은 SOMA 원본 관절 영상과 선택 방향별 BODY_18 몸 포즈를 비교 MP4로 제공한다. `preview.mp4`는 SOMA 정면·측면 원본이며 `comparison.mp4`는 동기 비교 영상이다. ZIP에는 원본 PNG·모션 NPZ·골격·프롬프트·임베딩·비교 영상·`soma-pose.json`을 포함한다. 포즈는 원본 SOMA 위치에서 직접 투영하고 얼굴·손 상세 점은 합성하지 않는다. 기존 이력과 공용 리그 에셋은 보존한다.

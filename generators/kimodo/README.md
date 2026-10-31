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

동작 예시를 선택하고 `예시 불러오기`를 누르면 일반 예시는 프롬프트와 프레임만 변경한다. 남성 모델 제자리 걷기 예시는 기준 작업 `2026-10-30_15-20-41-797e8f93`의 프롬프트·180프레임·100스텝·시드 42·CFG 2·초기 방향 0°·후처리 해제·front_left·수평 이동 제거를 함께 불러온다. 일반 예시의 시드·고급 설정은 유지하며 생성은 별도 대기열 확인을 거친다. 예시 원본은 `config/prompt-examples.yaml`에서 관리한다. 프레임 입력 아래에 30fps 기준 길이를 표시하고, 접수한 생성 ID·진행 상태·최신 결과는 입력 아래에 표시한다. 프롬프트와 출력 방향은 HY-Motion처럼 같은 행에 배치하고 좁은 화면에서는 세로로 전환한다. 모델 준비 상태와 확인 버튼은 접힌 기술 설명 밖에 표시한다. 기존 작업은 하단 공용 생성 이력에서 조회한다. 출력 방향은 정면·좌우 측면·후면·대각 8개 중 복수 선택한다. 방향은 카메라에만 적용하며 모션을 다시 생성하거나 회전시키지 않는다.

출력 방향 키는 `front`, `front_left`, `left`, `back_left`, `back`, `back_right`, `right`, `front_right`이며 기준 각도·라벨은 `config/output-directions.yaml`에서 관리한다. 기존 CLI 요청에서 `directions`를 생략하면 전방 좌측을 사용한다. 빈 선택·중복·알 수 없는 방향은 거절한다. 단일 방향 미리보기는 512×512, 여러 방향 미리보기는 방향당 256px 타일의 2열 동기 비교 영상이다. ZIP의 `directions/<방향>/`에는 512×512 원본 PNG·MP4를 저장한다. 선택 수에 따라 렌더 시간과 저장 용량이 증가한다.



## 결과

ANNY 리타게팅·Blender 렌더 기능은 폐기했다. 신규 작업은 SOMA 원본 관절 영상과 선택 방향별 BODY_18 몸 포즈를 비교 MP4로 제공한다. `preview.mp4`는 SOMA 정면·측면 원본이며 `comparison.mp4`는 동기 비교 영상이다. ZIP에는 원본 PNG·모션 NPZ·골격·프롬프트·임베딩·비교 영상·`soma-pose.json`을 포함한다. 포즈는 원본 SOMA 위치에서 직접 투영하고 얼굴·손 상세 점은 합성하지 않는다. 기존 이력과 공용 리그 에셋은 보존한다.

### 제자리 보행 보정
GUI의 `제자리 보행 보정 · 수평 이동 제거` 또는 생성 요청의
`remove_horizontal_motion: true`로 활성화한다. 기본값과 과거 요청은 false다.
추론 후 첫 프레임 Hips를 기준으로 X·Z 이동을 전체 관절과 루트 위치에서 빼고,
Y 높이와 회전은 유지한다. 보행 생성이나 발 접지 보정 기능은 아니다.
원본은 `motion.npz`, 보정본은 `motion-in-place.npz`로 ZIP에 함께 저장한다.
활성화 시 SOMA MP4·PNG와 오픈포즈 비교 영상은 보정본을 사용한다.

오픈포즈 v3는 14·15번에 실제 눈 관절을 투영한다. 코 0번·귀 16·17번은 대응 관절이 없어 좌표와 confidence를 0으로 기록하고 관련 선을 생략한다. v2의 Head→코 대리점은 폐기했다. 기존 v2 결과는 보존하며 새 출력에 v3를 기록한다.

포즈 색상 렌더링은 VideoX-Fun의 `comfyui/annotator/dwpose_utils/util.py` BODY18 규칙을 따른다. 선은 지정색의 0.6 밝기 타원형, 점은 관절 인덱스별 원색으로 마지막에 그린다. 귀가 누락되어도 뒤쪽 눈 연결선 색 인덱스는 당기지 않는다. `soma-pose.json`에 렌더 버전과 기준 URL을 기록하며 기존 결과는 자동 덮어쓰지 않는다.


### 선택 참조 이미지로 OpenPose 신체 비율 맞추기

GUI의 `OpenPose 신체 비율 참조 · 선택`을 켜고 같은 캐릭터의 이미지를 최대 8장 첨부한다. 기본값은 꺼짐이며 첨부해도 끄면 사용하지 않는다. CLI는 선택 필드 `proportion_images`에 RGB PNG base64 목록을 전달한다. 미전달·빈 목록은 기존 출력과 같다. 각 이미지 8MiB, 각 변 64~4096 제한이며 중복 파일은 거절한다.

CUDA ViTPose/YOLO로 BODY18을 추출하고, 어깨·골반 중심 간 몸통 길이에 대한 어깨 너비·골반 너비·위팔·아래팔·허벅지·종아리 길이를 추정한다. 관절 신뢰도 0.6 미만과 좌우 길이 비율 0.65 미만 관측을 제외하고 이미지별 비율의 신뢰도 가중 중앙값을 사용한다. 중앙값에서 20% 또는 3 MAD 중 큰 범위를 벗어나는 관측을 제외한다. 부위별 관측이 없으면 임의 값으로 대체하지 않고 오류로 중단한다.

정면 전신·단일 캐릭터를 권장한다. 측면·가림·원근의 단축은 2D 포즈만으로 완전히 구분할 수 없으며 실제 3D 체형 복원이 아니다. 보정은 SOMA에서 매핑한 출력 관절의 길이와 너비에 적용한 후 선택 방향으로 투영한다. 골반 경로·관절 방향·타이밍과 SOMA 모션 파일은 보존한다. 머리·손·발의 상세 체형은 추정하지 않는다. 캔버스 배율은 보정 결과가 들어오도록 클립 전체 기준으로 정한다.

ZIP의 `reference-proportions.json`에 입력별 포즈·신뢰도·채택 관측·최종 비율을 저장하고 `reference-pose-N.png`로 추출 포즈를 제공한다. `soma-pose.json`에도 보정 기록을 포함한다. 비교 MP4는 SOMA 원본과 비율 보정 OpenPose를 함께 표시한다. 참조 사본은 공용 작업 저장소에 보관하며 이력 복원·삭제 계약을 따른다.

전처리는 기존 `.local/wan22-animate/preprocess` 공식 검출 소스, `preprocess-deps` CUDA 12 ONNX Runtime과 `.model/wan22-animate-preprocess/process_checkpoint` 가중치를 공유한다. 옵션을 사용한 요청만 준비 상태를 검사하며 모델 추론은 별도 CUDA 자식 프로세스에서 수행한다.

참조 비율 v2는 시트 내 검출 점수 0.2 이상 모든 인물을 개별 추정한다. 관측 번호는 `observation_sources`의 이미지·인물·bbox에 대응한다. 부위별로 3개 이상 관측 시 두 번째 최장값의 1.35배를 넘는 단독 과대값을 제외한 뒤, 신뢰도 가중 80백분위 길이의 90% 이상 관측군에서 가중 중앙값을 구한다. 회전 투영의 단축 편향을 줄이는 휴리스틱이며 3D 길이 복원이나 수학적 최적값 보장은 아니다. 모든 방향에서 단축되거나 몸통 자체가 기울면 오차가 남는다. 기본 예제는 `body-baseline-8-directions.png`다.

ViTPose heatmap 최대값은 확률이 아니며 1을 넘을 수 있다. 원시 점수는 observation_sources에 보존하고 추정·렌더링용 점수만 [0,1]로 제한한다. 비유한 좌표·점수는 오류로 중단한다. 후면 검출 누락을 줄이기 위해 인물 후보 점수 기준을 0.2로 설정하며 관절별 0.6 기준은 유지한다.

Kimodo `generate`의 `openpose_scale_percent`는 OpenPose 출력 크기(10~100%, 기본 85%)입니다. `--payload-file` 요청에도 동일하게 적용합니다. 기존 여백 32px을 포함한 자동 맞춤 크기를 100%로 하여 지정 비율로 축소하며 SOMA와 신체 비율은 유지합니다. 요청·결과·포즈 JSON에 저장하고 이력에서 불러옵니다. 이 필드가 없는 과거 작업의 재개·입력 복원은 기존 크기인 100%를 유지합니다.

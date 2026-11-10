# Kimodo NF4 모션 생성기

관리 페이지: `/management/frame/kimodo-generator/?tool=kimodo-generator&category=animation-tool`.
GUI·`tools/manager.py command kimodo`는 공용 게이트웨이와 GPU 대기열을 사용한다.

- 모션: `nvidia/Kimodo-SOMA-RP-v1.2`, 원본 FP32.
- 텍스트: 커뮤니티 `matbee/kimodo-llm2vec-nf4`, NF4 저장·BF16 CUDA 연산. 공식 LLM2Vec의 양방향 attention·평균 풀링·supervised adapter를 사용한다.
- 인코딩을 마친 뒤 인코더를 해제하고 모션 모델을 CUDA로 로드한다. CPU 추론 대체는 없다.
- 기본값: 90프레임, 30fps, DDIM 100스텝, 텍스트 CFG 2, 초기 방향 0도, 시드 42, 후처리 해제. 2스텝은 실행 확인용이다.
- GUI 출력 방향 기본 선택은 전방 좌측 30도다. 동작 예제와 기존 이력을 불러오면 각각 저장된 방향이 적용된다.
- 30~300프레임을 입력받으며 모든 길이의 8GB 실행·품질을 보장하지 않는다. 초기 방향은 이후의 방향을 고정하지 않는다.
- GUI의 초기 방향 직접 편집은 폐기했다. 신규 입력은 기본값 0도를 사용하고, 기존 이력 불러오기와 기준 자세 선택은 기록된 초기 방향을 유지한다. CLI 요청·기록의 `heading_degrees` 계약은 호환을 위해 유지한다.

## 자료와 실행 환경 준비

모델 파일은 `.model/kimodo/`, 고정 공식 소스는 `.local/kimodo/upstream/`, 공용 환경은 `.venv`에 둔다. `config/assets.yaml`의 리비전과 LFS SHA-256을 확인한다. 기본 입력 원본은 추적 파일 `config/defaults.yaml`이다. 준비·설치는 GPU 접근이 가능한 샌드박스 밖에서 실행한다.

```bash
.venv/bin/python -m generators.kimodo.prepare
uv pip install --python .venv/bin/python --index-strategy unsafe-best-match --extra-index-url https://download.pytorch.org/whl/cu128 -r generators/kimodo/requirements.txt
PATH="$PWD/.venv/bin:$PATH" uv pip install --python .venv/bin/python --no-build-isolation .local/kimodo/upstream
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

동작 예시는 처음에 선택되지 않으며 선택 후 `예시 불러오기`를 눌러야 입력에 적용된다. 남성 모델 제자리 걷기 예시는 기준 작업 `2026-10-30_15-20-41-797e8f93`의 프롬프트·180프레임·100스텝·시드 42·CFG 2·초기 방향 0°·후처리 해제·front_right_30·수평 이동 제거와 8방향 신체 비율 참조를 함께 불러온다. 생성은 별도 대기열 확인을 거친다. 입력 하단의 현재 설정 요약에서 참조·키프레임·공식 후처리·수평 이동 제거를 확인한다. 예시 원본은 `config/prompt-examples.yaml`에서 관리한다. 프레임 입력 아래에 30fps 기준 길이를 표시하고, 접수한 생성 ID·진행 상태·최신 결과는 입력 아래에 표시한다. 프롬프트와 출력 방향은 같은 행에 배치하고 좁은 화면에서는 세로로 전환한다. 모델 준비 상태와 확인 버튼은 접힌 기술 설명 밖에 표시한다. 기존 작업은 하단 공용 생성 이력에서 조회한다. 출력 방향은 정면·좌우 측면·후면·대각과 전방 좌우 30도와 전방 우측 15도를 포함한 11개 중 복수 선택한다. 방향은 카메라에만 적용하며 모션을 다시 생성하거나 회전시키지 않는다.

출력 방향 키는 `front`, `front_left_30`, `front_left`, `left`, `back_left`, `back`, `back_right`, `right`, `front_right`, `front_right_30`, `front_right_15`이며 기준 각도·라벨은 `config/output-directions.yaml`에서 관리한다. 기존 CLI 요청에서 `directions`를 생략하면 전방 좌측을 사용한다. 빈 선택·중복·알 수 없는 방향은 거절한다. 단일 방향 미리보기는 512×512, 여러 방향 미리보기는 방향당 256px 타일의 2열 동기 비교 영상이다. ZIP의 `directions/<방향>/`에는 512×512 원본 PNG·MP4를 저장한다. 선택 수에 따라 렌더 시간과 저장 용량이 증가한다.

`카메라 고도`는 0°·+15°·+30° 중 하나를 선택한다. 양수는 카메라가 인물보다 위에서 내려다보는 각도다. CLI 생성 요청은 `camera_elevation_degrees`에 0·15·30 정수를 지정하며, 생략한 기존 요청과 이력은 0°다. 좌우 방향과 함께 SOMA 렌더 및 직접 포즈에 적용하고 DWPose 비율 계산도 같은 회전행렬을 사용한다. 카메라 설정은 저장된 원본 모션을 변경하지 않는다.



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

동작 예시 목록에는 각 예제를 불러올 때 적용되는 신체 비율 보정 켜짐·꺼짐이 표시된다. 참조가 등록된 예제는 해당 이미지를 불러와 보정을 켜고, 참조가 없는 예제는 보정을 끄고 참조 목록을 비운다.

GUI의 `OpenPose 신체 비율 참조 · 선택`을 켜고 같은 캐릭터의 이미지를 최대 8장 첨부한다. 기본값은 꺼짐이며 첨부해도 끄면 사용하지 않는다. CLI는 선택 필드 `proportion_images`에 RGB PNG base64 목록을 전달한다. 미전달·빈 목록은 기존 출력과 같다. 각 이미지 8MiB, 각 변 64~4096 제한이며 중복 파일은 거절한다.

CUDA ViTPose/YOLO로 BODY18을 추출하고, 어깨·골반 중심 간 몸통 길이에 대한 어깨 너비·골반 너비·위팔·아래팔·허벅지·종아리 길이를 추정한다. 관절 신뢰도 0.6 미만과 좌우 길이 비율 0.65 미만 관측을 제외하고, 과대 이상치를 제외한 긴 관측군의 신뢰도 가중 중앙값을 사용한다. 부위별 관측이 없으면 임의 값으로 대체하지 않고 오류로 중단한다.

참조 비율 v3는 코~어깨 중심과 어깨~골반 중심 거리의 비율도 추정한다. 신뢰 가능한 얼굴과 어깨 너비 채택 관측이 없으면 원인을 표시하고 중단한다. 포즈 출력에서 얼굴과 골반을 기준으로 어깨선을 몸통 축을 따라 이동하며, DWPose는 방향별 유효 프레임의 비율 중앙값으로 고정 배율을 정한다. 배율과 관측 수는 `dwpose-export.json`에 기록한다. 코 위치는 목뼈가 아닌 얼굴–어깨 거리의 대리 지표다. 2D 투영·고개 자세·가림에 영향을 받으므로 실제 목 길이와 3D 체형의 정확한 복원을 보장하지 않는다. 과거 v2 기록은 기존 방식으로 처리한다.

직접 포즈는 3D 보정 후에도 카메라 투영에 따라 얼굴과 어깨 거리 비율이 달라질 수 있으므로, 출력 방향마다 투영된 좌표의 얼굴·몸통 비율을 참조와 비교해 어깨와 팔을 함께 이동한다. 얼굴과 골반·다리 및 팔 관절 벡터는 유지하며 영상 전체에 같은 몸통 배율을 사용한다. 방향별 추가 배율은 `soma-direct-pose.json`의 `projected_body_axis_gains`에 기록한다. 기존 결과는 다시 쓰지 않는다.

정면 전신·단일 캐릭터를 권장한다. 측면·가림·원근의 단축은 2D 포즈만으로 완전히 구분할 수 없으며 실제 3D 체형 복원이 아니다. 보정은 SOMA에서 매핑한 출력 관절의 길이와 너비에 적용한 후 선택 방향으로 투영한다. 골반 경로·관절 방향·타이밍과 SOMA 모션 파일은 보존한다. 머리·손·발의 상세 체형은 추정하지 않는다. 캔버스 배율은 보정 결과가 들어오도록 클립 전체 기준으로 정한다.

ZIP의 `reference-proportions.json`에 입력별 포즈·신뢰도·채택 관측·최종 비율을 저장하고 `reference-pose-N.png`로 추출 포즈를 제공한다. `soma-pose.json`에도 보정 기록을 포함한다. 비교 MP4는 SOMA 원본과 비율 보정 OpenPose를 함께 표시한다. 참조 사본은 공용 작업 저장소에 보관하며 이력 복원·삭제 계약을 따른다.

전처리는 기존 `.local/wan22-animate/preprocess` 공식 검출 소스, `preprocess-deps` CUDA 12 ONNX Runtime과 `.model/wan22-animate-preprocess/process_checkpoint` 가중치를 공유한다. 옵션을 사용한 요청만 준비 상태를 검사하며 모델 추론은 별도 CUDA 자식 프로세스에서 수행한다.

참조 비율 v2는 시트 내 검출 점수 0.2 이상 모든 인물을 개별 추정한다. 관측 번호는 `observation_sources`의 이미지·인물·bbox에 대응한다. 부위별로 3개 이상 관측 시 두 번째 최장값의 1.35배를 넘는 단독 과대값을 제외한 뒤, 신뢰도 가중 80백분위 길이의 90% 이상 관측군에서 가중 중앙값을 구한다. 회전 투영의 단축 편향을 줄이는 휴리스틱이며 3D 길이 복원이나 수학적 최적값 보장은 아니다. 모든 방향에서 단축되거나 몸통 자체가 기울면 오차가 남는다. 기본 예제는 `body-baseline-8-directions.png`다.

ViTPose heatmap 최대값은 확률이 아니며 1을 넘을 수 있다. 원시 점수는 observation_sources에 보존하고 추정·렌더링용 점수만 [0,1]로 제한한다. 비유한 좌표·점수는 오류로 중단한다. 후면 검출 누락을 줄이기 위해 인물 후보 점수 기준을 0.2로 설정하며 관절별 0.6 기준은 유지한다.

Kimodo `generate`의 `openpose_scale_percent`는 OpenPose 출력 크기(10~100%, 기본 85%)입니다. `--payload-file` 요청에도 동일하게 적용합니다. 기존 여백 32px을 포함한 자동 맞춤 크기를 100%로 하여 지정 비율로 축소하며 SOMA와 신체 비율은 유지합니다. 요청·결과·포즈 JSON에 저장하고 이력에서 불러옵니다. 이 필드가 없는 과거 작업의 재개·입력 복원은 기존 크기인 100%를 유지합니다.

## SOMA 렌더 → DWPose → Fun Control

Kimodo는 공식 SOMASkin으로 방향별 SOMA 영상을 렌더한 뒤 VideoX-Fun DWPose 공식 검출·그리기를 CUDA에서 실행합니다. 신규 `dwpose-<direction>.mp4`는 832×480, 30fps이며 SOMA의 모든 원본 프레임을 사용합니다. Fun Control은 현재 16fps 입력을 요구하므로 입력 전에 별도 변환이 필요합니다. 기존 16fps 이력은 변경하지 않습니다. SOMA 메시 영상은 검수용으로 함께 보존합니다.

신체 비율 참조를 선택하면 SOMA 3D 관절을 출력 방향으로 투영해 부위별 단축을 추정하고, DWPose 검출의 몸통 대비 길이와 참조 비율을 비교해 방향별 고정 보정 배율을 계산합니다. 영상 전체에 같은 배율을 적용해 동작에 따른 투영 변화를 보존합니다. 손 상세는 보정된 손목으로 함께 이동하며 머리 이목구비는 이동·확대 외에 변형하지 않습니다. 필수 몸 관절 누락이나 과도한 보정 배율은 임의 복원하지 않고 실패합니다. 참조 비율은 2D 추정치이므로 실제 3D 체형의 정확한 복원은 아닙니다. 이전 생성 결과는 당시의 보정 방식과 영상을 유지합니다.

`openpose_scale_percent`는 검출 포즈의 영상 중심 기준 배율(기본 85%)에도 적용합니다. SOMA 렌더 자체의 여백과 별개입니다. `pose_include_hands`, `pose_include_face`는 기본 false입니다. CLI payload에도 같은 bool 필드를 사용합니다. 기존 직접 투영 비교물은 구형 비교 자료로 유지합니다.

ZIP에는 방향별 포즈 MP4, 원시·보정 검출 좌표, `dwpose-export.json`의 관절 배율·크기·FPS·상세 옵션이 포함됩니다. Fun Control은 처리된 MP4를 프레임으로 읽기만 하며 DWPose를 다시 실행하지 않습니다. 원본 NPZ와 SOMA 렌더에는 관절 길이 보정을 적용하지 않습니다.

### 직접 투영 검수

전신 키프레임 제약 입력은 폐기되었습니다. 신규 요청은 해당 필드를 받지 않으며 기존 제약 작업의 재개는 거절합니다. 기존 이력은 보존하고, 입력값 불러오기 후 새 생성은 제약 없이 수행합니다.

`direct_pose_export.export_direct_pose_video`는 기존 시도의 SOMA 카메라 기록과 모션에서 BODY18 포즈를 생성하는 검수용 Python 함수입니다. OpenCV가 있는 `.venv` 포즈 처리 환경에서 실행합니다. 출력은 832×480·30fps이며 모든 원본 프레임을 보존하고 기존 파일을 덮어쓰지 않습니다. 기록된 SOMA 카메라에 렌더 배율이 이미 포함되어 있으므로 직접 투영 단계에는 추가 배율을 적용하지 않습니다. 별도 배율 인자를 받지 않으며 출력 메타데이터에 추가 배율 100%를 기록합니다. `soma-render.json`의 `cameras`가 없는 과거 결과는 카메라 기록을 포함한 재렌더가 필요합니다. 생성 시 직접 포즈와 DWPose를 함께 출력하며 결과 조회에서 각각 확인합니다.

참조 이미지 처리기 `reference_extraction.py`가 만든 비율 파일을 `current_reference_ratio_path` 인자로 지정할 수 있습니다. 지정한 파일이 없으면 즉시 실패합니다. 인자를 생략하면 시도 폴더의 `reference-proportions.json`을 사용하며, 파일이 없으면 SOMA 원본 체형입니다. 참조 비율 파일이 있으면 기존 신체비율 보정을 3D 관절에 먼저 적용하고 같은 카메라로 투영합니다. 적용 비율·근거를 출력 메타데이터에 보존합니다. 원본 모션과 SOMA 메시를 수정하지 않습니다. 코·귀 대응점, 손·얼굴 상세와 가림 판정은 지원하지 않습니다. 목은 어깨 중점이며 존재 표시 1은 검출 신뢰도를 의미하지 않습니다. DWPose와의 좌표 차이는 골격 정의와 검출 오차를 함께 포함하므로 직접 투영의 절대 오차로 해석하지 않습니다.

### 포즈 결과 생성과 부분 오류

SOMA 렌더 뒤 참조 신체 비율을 적용한 직접 포즈 MP4를 먼저 생성하고 DWPose도 실행합니다. 직접 포즈 생성 오류는 작업 실패이며, DWPose 오류는 실행 로그와 `quality_warnings`, `dwpose-export.json`에 경고로 보존합니다. 이 경우 직접 포즈는 결과와 ZIP에 유지합니다. 직접 포즈의 코·귀는 `config/head-anchors.yaml`에 보존한 Head 로컬 오프셋과 전역 회전으로 계산합니다. 전방 좌측 81프레임에서 검증한 추정이며 다른 동작·방향 일반화는 미검증입니다.

### 공용 Python 환경

Kimodo 작업 실행기·참조 분석·직접 포즈·DWPose는 모두 `.venv/bin/python`을 사용합니다. GPU 메모리 해제를 위한 별도 프로세스는 유지합니다. 공식 소스의 Transformers 5.1.0 고정을 따르므로 공용 환경을 갱신할 때 이 요구를 함께 검증하세요. 관리 GUI도 동일한 `.venv`를 사용하며 의존성 변경 시 양쪽을 함께 검증합니다.

### Kimodo 순차 동작 생성

공식 가이드에 따라 한 구간은 1~2개 행동에 집중합니다. `prompt`에 줄마다 독립된 설명을 넣고 선택 필드 `segment_frames`에 각 구간 프레임 배열을 전달합니다. 예: 3줄과 `[90,120,90]`, 전체 `frames: 300`. GUI의 순차 생성 구간 프레임은 `90 120 90`으로 입력합니다. 비우면 기존 단일 프롬프트입니다. 공식 `multi_prompt=True`, 기본 전환 5프레임을 사용하며 저장한 키프레임을 순차 구간과 함께 사용할 수 있습니다. 임의 키프레임 JSON 업로드는 지원하지 않습니다. 공식 내부 연결용 제약은 사용됩니다. 설정 스텝은 구간마다 적용됩니다. 현재 전체 300프레임 제한은 유지합니다.

근거: https://research.nvidia.com/labs/sil/projects/kimodo/docs/key_concepts/limitations.html 및 공식 user_guide/cli.md.

## 등록된 자세와 키프레임 배치

기존 `relaxed-standing-v1`은 `편안한 서기 · 어깨너비 · v1` 키프레임으로 통합했다. `저장한 키프레임 배치`에서 선택하고 `선택 자세를 시작·종료에 배치`를 누르면 1프레임과 마지막 프레임에 추가한다. 이미 배치된 프레임은 덮어쓰지 않고 거절한다. 예전 생성 이력의 양 끝 자세는 입력 복원 시 동일한 두 키프레임으로 변환한다. 과거 실행과 재개를 위한 이전 자세 파일은 보존한다.

### 생성 이력 키프레임 저장과 배치

생성 이력에서 완료 작업을 선택하고 `선택 이력 프레임 불러오기`를 누른다. 원본 30fps 관절 재생기에서 프레임을 확인하고 `표시한 프레임 선택`을 누른 뒤 태그를 입력하여 저장한다. 원본 프레임 번호는 1부터 시작한다. 포즈·관절 미리보기·골격·출처·해시가 생성 이력과 별도로 보관되므로 이력 삭제로 자동 삭제되지 않는다. 저장 목록에서 태그를 선택해 같은 미리보기를 다시 볼 수 있다. 수평 이동 제거 결과는 화면에 표시된 보정 모션에서 저장한다.

`저장한 키프레임 배치`에서 목록을 새로고침하고 각 키프레임의 출력 프레임 번호를 추가한다. 1은 시작이고 전체 프레임 수는 종료다. 같은 프레임 번호 중복은 거절한다. 공식 후처리를 켜며 수평 이동 제거와 함께 사용할 수 없다. 순차 생성 구간과 함께 사용할 수 있다. 키프레임 하나 이상을 사용하면 생성 접수 시 원본 포즈 사본을 작업 폴더에 저장하고 재개 시에도 같은 사본을 사용한다. 77관절 자세는 공식 API로 30관절에 변환되며 결과 ZIP의 `keyframe-constraints.json`과 `keyframe-measurement.json`에 실제 제약·관절 위치 오차를 남긴다. 서로 다른 작업에서 가져온 포즈는 원본 좌표계가 다를 수 있다. 첫 키프레임의 평활 루트 XZ를 원점으로 하며 나머지의 상대 위치를 그대로 유지하므로 연결 결과를 검수해야 한다.

`복싱 원투` 예제는 `2026-11-09_15-00-04-73ccd4a0`의 텍스트·40프레임·시드 404·정면과 우측 15도·고도 +30도 설정을 사용한다. 키프레임과 손 상세는 끄며, 자세와 펀치 방향은 생성 후 검수한다. 해당 기준 작업의 DWPose는 인체 검출 실패로 출력되지 않았다. 기존 복싱 키프레임 사본은 `keyframe-examples/`에서 계속 관리한다.

통합 CLI 저장 요청 JSON 예: `{"job_id":"2026-11-06_14-22-05-11c6a312","attempt_id":"5d90b105ecac4ad3bffa15e2e465c06b","frame":1,"tag":"가드"}`. `python3 tools/manager.py command kimodo keyframe-save --payload-file request.json`으로 저장하고 `keyframe-list`로 ID를 조회한다. 생성 payload의 `keyframes`는 `[{"id":"<저장 ID>","frame":1},{"id":"<저장 ID>","frame":90}]`이며 `frames: 90`, `post_processing: true`가 필요하다. 지원하지 않는 임의 `pose_constraints`는 계속 거절한다.

이전 CLI 입력의 `endpoint_pose_id: relaxed-standing-v1`은 호환을 위해 동일한 시작·종료 키프레임으로 변환한다. 신규 입력은 `keyframes` 배열을 사용한다.

기준 자세 선택·공식 제약 변환의 연결 검증과 GPU 생성 품질 검수는 구분한다. 동일 3D 자세가 이미지 참조와 같은 픽셀 배치라는 뜻은 아니다. 생성 후 양 끝 3D 관절 오차, 30fps 포즈의 프레임 동기화와 Fun Control용 16fps 변환, 포즈 출력 카메라·배율까지 확인해야 한다.

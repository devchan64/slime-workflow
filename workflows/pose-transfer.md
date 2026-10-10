# VNCCS 포즈 변환 생성기

현재 포즈 변환은 **VNCCS PoseStudio V1.1 LoRA + 공식 QwenImage21Pipeline**을 사용한다. MoMask + AnyPose 경로는 폐기했으며 이 도구로 우회 복원하지 않는다. 메뉴의 Alpha Ver. 표기는 제거했지만 포즈 정밀도·전신 비례·프레임 일관성은 여전히 결과별 검수가 필요하다.

애니메이션 도구의 `?tool=pose-transfer-generator&category=animation-tool` 또는 공용 게이트웨이 `pose-transfer`에서 단일 장면을 변환한다. 모션 전체 자동 배치나 영상 생성 기능은 아니다. 모션·ANNY 포즈 준비는 [HY-Motion](hy-motion.md), 전체 검수 절차는 [캐릭터 애니메이션 제작](character-animation.md)을 따른다.

## 입력과 고정 설정

- 아이덴티티 이미지 1장과 포즈 이미지 1장이 필수다. GUI·CLI 입력과 파일 저장 순서는 **아이덴티티 → 포즈**이며, 실행기가 모델 입력만 **포즈 image1 → 아이덴티티 image2**로 바꾼다.
- 신규 출력은 512×512 고정, 스텝은 25·40 중 선택(기본 40), 기본 시드는 `1695791623`이다. 모델·LoRA·BF16 비양자화 정밀도는 코드에 고정하며 LoRA SHA-256을 검증한다.
- 참조는 RGB/RGBA PNG, 장당 3MB 이하이며 투명 영역은 공용 입력 처리로 흰 배경에 합성한다. 입력 참조의 원본 비율과 출력 해상도를 구분한다.
- 기본 프롬프트는 `generators/image/config/pose-transfer-prompt.txt`에서 Git으로 관리한다. 기본·사용자 보조 지시를 포함한 실제 모델 입력은 1~99단어이며 최종 원문·단어 수·해시를 기록한다. 100단어 미만은 저장소 운영 규칙이다.

```bash
python3 tools/manager.py help pose-transfer generate
python3 tools/manager.py command pose-transfer generate --reference /path/identity.png --reference /path/pose.png --resolution 512 --steps 40 --seed 1695791623 --detach
python3 tools/manager.py command pose-transfer history
python3 tools/manager.py command pose-transfer status GENERATION_ID
python3 tools/manager.py command pose-transfer logs GENERATION_ID
python3 tools/manager.py command pose-transfer cancel GENERATION_ID
python3 tools/manager.py command pose-transfer resume GENERATION_ID
```

CLI는 프롬프트 생략 시 추적된 기본 문구를 사용하고, `--prompt` 또는 `--prompt-file`로 대체한다. 프롬프트 안의 이미지 번호는 사용자 업로드 순서가 아닌 모델 전달 순서에 맞춰 작성한다. 과거의 외형 image1 → 포즈 image2 지시문을 신규 VNCCS 작업에 그대로 사용하지 않는다.

## 실행과 기록

GUI·CLI → 공용 게이트웨이 → 이미지 작업 서비스 → 독립 GPU 작업자·대기열을 사용한다. 게이트웨이는 GPU 접근이 가능한 샌드박스 밖에서 실행한다. 가중치는 CPU RAM에 대기시키되 모델 연산은 CUDA에서 수행한다. CUDA 부재·필수 파일 누락·해시 오류는 실패하며 CPU 추론으로 대체하지 않는다.

작업은 `.tmp/test/pose-transfer/<생성 ID>/`, 이력은 `.tmp/manager-current/pose-transfer/`에 저장한다. `request.json`의 `vnccs`에 실행 버전·모델 입력 순서·정밀도·LoRA 해시·안전 한계를 기록하고, 참조 두 장의 사본·해시를 보존한다. 상세 로그는 `vnccs-pipeline.log`, 자원 기록은 `vnccs-resources.json`, 결과·품질 경고는 `result.json`에서 확인한다.

감독 작업자는 5초마다 자식 상태·진행 로그·자원을 확인한다. 시스템 RAM 여유 12GiB 미만, 작업 RSS 42GiB 초과, 실행 20분 초과 시 실패로 중단한다. 이는 실행 안전 한계이며 생성 품질이나 최대 VRAM의 보장값이 아니다. 브라우저 연결 종료는 작업 종료나 이력 삭제를 의미하지 않는다.

## 과거 기록과 검수

`vnccs` 필드가 없는 과거 포즈 변환 작업의 재개는 당시 Qwen 경로·입력 순서·설정을 유지한다. 과거 입력을 불러와 새로 생성하면 현행 VNCCS 고정 설정을 사용한다. 이는 폐기된 AnyPose 작업의 재개를 허용하는 기능이 아니다.

ANNY 포즈와 결과를 같은 방향·프레임 번호로 비교하고 관절 연결·손발 위치·가림·외형을 확인한다. 공식 포즈도 일부만 따라가는 결과가 있으므로 완료를 품질 승인으로 간주하지 않는다. 프롬프트 변경 후 1프레임을 먼저 검수하며 생성 결과를 정식 에셋에 자동 등록하지 않는다.

세부 게이트웨이 계약은 [관리도구 클라이언트 가이드](management-clients.md#vnccs-포즈-변환--bf16-기준-경로)를 따른다.

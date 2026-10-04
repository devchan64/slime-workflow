# 애니메이션 분리 생성기

관리도구의 **애니메이션 도구 → 애니메이션 분리 생성기**에서 등록된 캐릭터 애니메이션을 Qwen Image 2.1로 머리·신체 후보로 생성한다. GUI와 통합 CLI 모두 공용 명령 게이트웨이의 `animation-separation` 서비스를 사용한다.

## 실행 순서

1. 원본 애니메이션과 샘플 프레임을 선택한다. 등록부의 이미지·재생 메타데이터 해시를 검증하고 원본을 참조 스냅샷으로 보존한다.
2. 512 또는 768 정사각형, 시드, 분리 프롬프트를 정하고 **1프레임 샘플 생성**을 실행한다. 기본 크기는 768, 스텝은 40이며 모델·버전은 코드에 고정한다.
3. **결과 검수** 탭에서 생성 ID를 조회한다. 원본·분리 후보·머리·신체·조합 화면을 동기 재생하거나 프레임을 이동한다. 머리 위치·배율은 검수용이며 저장 결과를 바꾸지 않는다.
4. 샘플 확인 후 해당 ID를 **검수한 샘플 ID**에 입력하고 범위를 생성한다. 같은 원본·프롬프트·크기·시드·모델 설정의 완료 샘플만 허용한다. 최대 64프레임이다.
5. 완료 결과를 ZIP으로 내려받는다. 원본과 게임 에셋을 자동으로 갱신하지 않는다.

기본 프롬프트는 `generators/image/config/animation_separation.yaml`에서 추적한다. 머리에는 얼굴·머리카락, 신체에는 옷깃 위로 드러나는 피부색 목 연결부·가슴 위쪽 피부·복장·팔다리·신발을 유지하도록 지시한다. 단순히 목 전체를 보존하라는 지시만으로는 목과 옷깃 안의 피부가 함께 지워질 수 있어, 노출된 피부와 목 연결부의 형태를 명시한다. 마네킹 바탕은 요구하지 않는다. 입력은 1~99단어이며 최종 원문·단어 수·해시를 기록한다.

## CLI

```bash
python3 tools/manager.py command animation-separation catalog
python3 tools/manager.py command animation-separation generate \
  --source-id 'asset:assets/characters/female/animations/idle-v1/down-left-8frames-v2/idle-v1.animation.json' \
  --start-frame 1 --end-frame 1 --size 768 --seed 10107 --detach
python3 tools/manager.py command animation-separation status --id <생성-ID>
python3 tools/manager.py command animation-separation generate \
  --source-id '<같은-원본-ID>' --start-frame 1 --end-frame 8 \
  --size 768 --seed 10107 --sample-id <검수한-샘플-ID> --detach
python3 tools/manager.py command animation-separation cancel --id <생성-ID>
python3 tools/manager.py command animation-separation resume --id <생성-ID> --detach
```

세부 인자는 `python3 tools/manager.py help animation-separation`로 확인한다. 사용자 프롬프트는 `--prompt-file`로 전달한다. HTTP 계약은 `POST /management/command`의 `{service, command, payload}`다. 생성 payload는 `action`, `source_id`, `start_frame`, `end_frame`, `width`, `height`, `steps`, `seed`, `prompt` 및 선택 `sample_id`, `tag`를 사용한다.

## 작업과 결과 보관

- 작업: `.tmp/test/animation-separation/<한국시각-생성ID>/`
- 공용 이력: `.tmp/manager-current/animation-separation/`
- 입력·로그·상태: `request.json`, 참조 스냅샷, 공용 실행 로그, `status.json`, `separation-progress.json`
- 결과: `result.png`, `source-sheet.png`, `head-sheet.png`, `body-sheet.png`, `manifest.json`, `separation.zip`
- 프레임별 완료 기록: `frame-NNN/complete.json`. 재개 시 입력·출력 해시가 일치하는 완료 프레임은 재사용하고 미완료 프레임부터 실행한다. 변조·규격 불일치는 즉시 실패한다.

GUI를 닫아도 작업은 공용 GPU 대기열에서 계속 실행된다. 재접속 후 같은 생성 ID를 조회한다. 취소·재개·이력 초기화는 공용 서비스의 명시적 명령으로만 실행하며, 다른 실행 작업을 취소하지 않는다. 상태·결과 조회는 수동이다. 예상 시간 근거가 없으면 추정 자료 수집 중으로 표시한다.

## 후보 품질 범위

Qwen 결과의 좌측 절반은 머리, 우측 절반은 신체 후보로 추출한다. RGB 흰 배경이며 자동 투명 레이어가 아니다. 원본 앵커·프레임 ID는 기록으로 남기지만 AI 결과의 위치·비율·외형 보존을 보장하지 않는다. 경계 침범, 목 연결, 머리 비율, 프레임 간 흔들림을 검수해야 한다.

조합 미리보기는 머리 이미지의 RGB 각 값이 245 이상인 픽셀을 임시 투명화한다. 밝은 머리·복장까지 제거할 수 있으므로 실제 알파 산출물로 사용하지 않는다. 최종 투명화·정렬·에셋 등록은 별도 채택 작업이다.

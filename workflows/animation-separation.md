# 신체 베이스·복장 독립 생성기

관리도구의 **애니메이션 도구 → 애니메이션 분리 생성기**는 같은 원본 프레임을 두 프롬프트로 각각 생성한다. 머리 분리·한 이미지의 좌우 절반 추출·검수 유형 전환은 폐기했다.

## 두 프롬프트

1. **신체 베이스:** 인물·머리·걷기 자세를 유지하고 겉옷을 불투명한 파란색 어깨끈 없는 짧은 상의와 허벅지 위쪽에서 끝나는 불투명한 밀착 반바지로 바꾼다. 신발은 제거하고 발목 위치·발 방향을 유지한 맨발로 생성한다. 신발은 복장 결과에만 포함한다. 상의는 가슴 전체를 덮되 원본 상의 밑단보다 위에서 끝나고, 반바지 허리선은 원본 바지 허리선보다 아래에 둔다. 원본에서 드러난 허리 영역을 유지하여 복장을 겹쳤을 때 베이스 의복이 틈으로 보이지 않도록 한다.
2. **복장:** 원본에서 사람·피부·머리·머리카락·노출된 발을 제거하고 원본에 보이는 상의·바지·신발을 남긴다. 입고 있던 자세·좌표·크기·주름·색과 신발 형태를 보존하도록 지시한다. 사람이 가렸던 영역과 목둘레·소매·허리·신발 입구의 빈 공간은 흰 배경으로 유지하며, 보이지 않던 등판·안감·천·발을 새로 그리지 않는다. 원본에 실제로 보이는 등쪽 옷 표면은 유지한다.

두 단계 모두 **같은 원본 참조 스냅샷**을 입력으로 사용한다. 베이스 결과를 복장 입력으로 사용하지 않는다. 모델은 Qwen Image 2.1, 각 단계 40스텝이며 기본 768 정사각형(512 선택 가능)이다. 한 프레임마다 두 번 추론하므로 기존 단일 생성보다 시간이 더 필요하다.

기본 문구는 `generators/image/config/animation_separation.yaml`에서 추적한다. 각 프롬프트는 1~99단어이며 각각의 원문·단어 수·SHA-256을 요청에 보존한다. GUI에는 실제 각 모델 입력의 단어 수를 표시한다.

## 실행과 검수

워크플로우의 등록 4방향 외형 레퍼런스도 원본 목록에서 선택할 수 있다. ID는 `workflow:character-default`와 `workflow:character-female`이며 프레임 순서는 `down_left`, `down_right`, `up_left`, `up_right`다. 캐릭터 애니메이션 설정의 원본 매핑을 재사용하고 manifest의 이미지 해시·크기를 검증한다. GUI·CLI 모두 같은 ID와 생성·검수 계약을 사용한다.

원본과 범위를 선택하고 먼저 **1프레임 샘플 생성**을 실행한다. 결과 검수에서는 원본·신체 베이스·복장·겹쳐보기를 같은 프레임으로 재생한다. 이미지의 좌우 절반이 아닌 각 독립 파일의 전체 프레임을 표시한다. 베이스·복장 시트는 각각 다운로드할 수 있다.

복장 위치·배율은 화면에서만 조절한다. 겹쳐보기는 복장의 RGB 각 값이 245 이상인 픽셀을 임시 투명화하므로 흰 옷도 지워질 수 있다. 결과 파일은 RGB 흰 배경이며 실제 투명화는 별도 작업이다. 원본 포즈·좌표·비율 일치, 피부·얼굴 잔상과 누락된 의상을 검수해야 한다. 실행 완료는 품질 통과가 아니다.

샘플 두 결과를 확인한 뒤 ID를 입력해 최대 64프레임 범위를 생성한다. 원본·두 프롬프트·크기·시드·모델이 모두 같은 완료 샘플만 허용한다. 원본·게임 에셋은 자동 변경하지 않는다.

## CLI와 HTTP

```bash
python3 tools/manager.py command animation-separation catalog
python3 tools/manager.py command animation-separation generate \
  --source-id 'asset:assets/characters/female/animations/walk-v1/down-left-12frames-v2/walk-v1.animation.json' \
  --start-frame 1 --end-frame 1 --size 768 --seed 10107 --detach
python3 tools/manager.py command animation-separation status <생성-ID>
python3 tools/manager.py command animation-separation generate \
  --source-id '<같은-원본-ID>' --start-frame 1 --end-frame 12 \
  --sample-id <검수한-샘플-ID> --size 768 --seed 10107 --detach
python3 tools/manager.py command animation-separation cancel <생성-ID>
python3 tools/manager.py command animation-separation resume <생성-ID> --detach
```

`--prompt-file`은 베이스, `--outfit-prompt-file`은 복장 프롬프트다. 생략하면 추적된 기본값을 사용한다. `python3 tools/manager.py help animation-separation` 또는 `generate --help`로 인자를 확인한다.

GUI와 CLI는 공용 HTTP 게이트웨이 `POST /management/command`의 `{service, command, payload}`를 사용한다. 서비스는 `animation-separation`이다. 생성 필수 필드는 `action`, `source_id`, `start_frame`, `end_frame`, `width`, `height`, `steps`, `seed`, `prompt`, `outfit_prompt`이며 선택 필드는 `sample_id`, `tag`다. 기존 단일 프롬프트 요청은 명시적 오류로 거절한다.

## 기록과 재개

- 작업: `.tmp/test/animation-separation/<한국시각-생성ID>/`
- 이력: `.tmp/manager-current/animation-separation/`
- 단계 결과: `frame-NNN/base/result.png`, `frame-NNN/outfit/result.png`
- 시트: `base-sheet.png`, `outfit-sheet.png`, `source-sheet.png`
- 기록: `request.json`, 원본 참조 스냅샷, `manifest.json`(schema 2), 단계별 `complete.json`·결과 기록, 공용 로그·상태·진행 파일
- ZIP: 두 시트·원본·프레임별 독립 결과와 메타데이터. `result.png`는 이력 호환용 베이스 썸네일이며 복장과 합친 생성물이 아니다.

브라우저를 닫아도 공용 GPU 작업은 계속된다. 중단 후 재개 시 완료 파츠의 입력·출력 해시를 확인해 재사용하고 미완료 파츠만 실행한다. 두 단계 완료 후 해당 프레임을 완료 집계한다. 상태·결과는 수동 조회하며 시간 근거가 없으면 추정 자료 수집 중으로 표시한다.

schema 1의 머리·좌우 분리 이력과 원본 파일은 삭제하지 않는다. 기존 ZIP 보관은 유지하되 새 검수 화면은 구형 결과임을 안내하고 렌더링하지 않는다. 구형 작업 재개와 샘플 재사용은 거절한다. 새 생성 ID로 다시 실행한다.

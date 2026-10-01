# 좌하 휴식 진입·해제 AnyPose 검수 리포트

정지 구간을 덜어내고 사용자가 확정한 범위를 기존 4배속 설정으로 생성한 결과다. 좌하 방향의 진입 13장과 해제 8장을 원본 해상도로 보존한다. 현재 `report/`의 경로·리포트 본문·요청 기록을 확인했으며, 교체할 기존 휴식 리포트는 없었다.

| 항목 | 휴식 진입 | 휴식 해제 |
|---|---|---|
| GIF | [진입 GIF](rest-entry-down-left-8fps.gif) | [해제 GIF](rest-exit-down-left-8fps.gif) |
| 전체 프레임 | [진입 프레임](rest-entry-contact.png) | [해제 프레임](rest-exit-contact.png) |
| 생성 ID | 2026-10-01_13-27-05-8340bb22 | 2026-10-01_13-27-16-e5b97afd |
| 요청 구간 | 1–49 | 129–159 |
| 실제 선택 | 1, 5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45, 49 | 129, 133, 137, 141, 145, 149, 153, 157 |
| 장수·재생 | 13장·8 FPS·약 1.63초 | 8장·8 FPS·1초 |
| 완료 시각 (KST) | 2026-10-01 13:56:29 | 2026-10-01 13:47:07 |
| 실행 기록 | [요청](rest-entry/request.json) · [결과](rest-entry/result.json) · [로그](rest-entry/worker.log) | [요청](rest-exit/request.json) · [결과](rest-exit/result.json) · [로그](rest-exit/worker.log) |

## 생성 조건

등록 모션 `resting-v3`의 MoMask 기반 ANNY 리그 렌더와 `character-default` 외형 레퍼런스를 사용했다. 모델은 Qwen Image Edit 2511, Lightning 4스텝, AnyPose base/helper 0.7/0.7이며 512×512 PNG로 생성했다. 배속 4는 원본 프레임을 4칸 간격으로 선택하는 기존 동작이다. GIF 검수에서 수동 선택했던 비균등 간격의 12장·8장 목록과 달리, 실제 생성에는 표의 균등 간격 목록을 사용했다.

최종 방향 프롬프트 원문·단어 수·SHA-256과 모션·캐릭터 매니페스트 해시는 각 요청 기록에 보존했다. 이 실행에서는 기존 휴식 프롬프트를 변경하지 않았다.

## 검수 결과

두 작업은 종료 코드 0으로 완료됐으며 PNG 21장이 존재한다. 전체 프레임을 펼쳐 비교한 결과는 다음과 같다.

- 진입: 서기에서 앉은 자세까지 이어지며 뒤쪽 자세 정돈 구간이 포함된다. 후반 손 위치와 상체 자세에 프레임 간 변동이 있다.
- 해제: 앉은 자세에서 일어서는 흐름이 있다. **원본 133번 프레임에서 한쪽 신발이 사라지는 오류**가 있다. [해당 원본](rest-exit/down_left/frame-0133/result.png).
- 진입 마지막과 해제 첫 프레임의 팔 자세가 다르므로 두 클립의 연결 품질은 별도 검수 대상이다. GIF의 반복은 검수 편의용이며 게임용 루프 승인이나 정식 에셋 채택을 의미하지 않는다.

GIF는 원본 순서·위치·크기를 유지하고 흰 배경으로 합성했다. 10ms 시간 단위 때문에 120/130ms를 번갈아 사용하여 실제 길이는 진입 1620ms, 해제 1000ms다. 전체 프레임 비교와 파일·프레임 수 검증을 수행했으며, 자연스러운 연속 재생 및 최종 품질 승인은 사용자 검수 대상이다.

## 보존·재현

각 클립 폴더에는 실행 요청·상태·결과·진행·로그와 프레임별 이미지·캐릭터 참조·포즈 참조·프롬프트·추론 기록을 보존했다. [manifest.yaml](manifest.yaml)에 사본의 출처·버전·SHA-256이 있고 [verification.log](verification.log)에 사본 무결성 및 GIF 프레임 수 검증을 기록했다. 원래 실행 경로는 출처 정보이며 리포트 사본의 이미지·GIF 조회에는 필요하지 않다.

재생성은 공용 게이트웨이가 실행된 상태에서 다음 명령으로 진행한다. 실행별 출력은 새로운 `.tmp/test/character-animation/<한국시간>/`에 저장하며 이 보관본을 덮어쓰지 않는다. 등록 모션·레퍼런스·모델·GPU 환경이 필요하며 재추론의 픽셀 단위 동일성은 보장하지 않는다.

```bash
python3 tools/manager.py command character-animation generate --motion resting-v3 --character character-default --source anny --directions down_left --start-frame 1 --end-frame 49 --speed 4 --target-fps 8 --resolution 512 --steps 4 --detach
python3 tools/manager.py command character-animation generate --motion resting-v3 --character character-default --source anny --directions down_left --start-frame 129 --end-frame 159 --speed 4 --target-fps 8 --resolution 512 --steps 4 --detach
```

GIF 재현 시 각 `result.json`의 좌하 프레임 순서로 PNG를 읽고, 흰 배경 합성 후 120/130ms 교대·무한 반복·disposal 2로 저장한다. 기존 생성 이력과 정식 에셋은 유지한다.

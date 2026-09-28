# 4방향 걷기 AnyPose 30스텝 통합 리포트

## 대상과 상태

**이미지젠 보정 전 AnyPose 원본 24장**을 보존한 검수 리포트다. 우상 기존 30스텝 작업과 이후 생성한 좌하·우하·좌상 작업을 통합했다. 이미지젠 시트 리포트와 별개이며, 최종 에셋 채택·체형 정규화·게임 등록은 수행하지 않았다.

- [4방향 동기 재생 GIF](four-directions-4fps.gif): 위 좌상·우상, 아래 좌하·우하.
- [출처·실행 설정·파일 해시](manifest.yaml)

| 방향 | 원본 결과 | ANNY 리그 비교 | 실제 입력 프롬프트 |
|---|---|---|---|
| 좌하 | [GIF](down_left/result-4fps.gif) | [비교 GIF](down_left/anny-comparison-4fps.gif) | [원문](down_left/prompt.txt) |
| 우하 | [GIF](down_right/result-4fps.gif) | [비교 GIF](down_right/anny-comparison-4fps.gif) | [원문](down_right/prompt.txt) |
| 좌상 | [GIF](up_left/result-4fps.gif) | [비교 GIF](up_left/anny-comparison-4fps.gif) | [원문](up_left/prompt.txt) |
| 우상 | [GIF](up_right/result-4fps.gif) | [비교 GIF](up_right/anny-comparison-4fps.gif) | [원문](up_right/prompt.txt) |

비교 GIF는 왼쪽 ANNY 리그, 오른쪽 AnyPose 결과다. 네 방향의 같은 원본 번호를 동시에 재생하며 방향별 모션 투영을 비교할 수 있다.

## 공통 실행 조건

| 항목 | 값 |
|---|---|
| 등록 모션 | walking-v13 |
| 캐릭터 | character-default · 흰 셔츠 v2 |
| 포즈 입력 | ANNY |
| 요청 범위·샘플 | 1~22번 · 1·5·9·13·17·21번 |
| 생성 배속 / 타겟 FPS | 4배 / 4 FPS |
| 결과 | 방향당 6장, 총 24장 · 각 512×512px |
| 모델 | Qwen Image Edit 2511 |
| AnyPose base / helper | 0.7 / 0.7 |
| 스텝 / Lightning | 30 / 해제 |
| true CFG / 시드 | 4.0 / 10107 |
| GIF 재생 | 프레임당 250ms · 1.5초 반복 |

모든 프레임의 완료 상태·30스텝·Lightning 해제·AnyPose 강도를 결과 기록으로 확인했다. 출력 PNG는 원본 사본이며 이미지젠 편집·384px 패킹·비율 보정을 적용하지 않았다.

## 출처와 보존 자료

- 우상: `2026-09-28_15-06-32-ce084d85`.
- 좌하·우하·좌상: `2026-09-28_16-53-27-97523f7d`.
- 각 방향의 `frame-NNNN/`에 결과 PNG, 실제 ANNY 입력, 캐릭터 입력, 프레임별 result.json을 보존했다.
- `job-request.json`, `job-result.json`, `job-status.json`은 해당 원본 작업 기록의 사본이다. 3방향 작업 사본에는 원래 작업의 세 방향 전체 목록이 포함되며, 이 리포트의 상대 파일 배치는 최상위 manifest를 따른다.
- 방향별 prompt.txt는 현재 설정을 재계산한 값이 아니라 실행 당시 request.json의 최종 입력이다.

## 검수 범위와 유의점

이번 통합에서는 파일 무결성·실행 기록·이미지 크기·GIF 프레임 수와 시간 간격을 확인했다. 신규 전체 영상 품질 판정을 수행한 것은 아니다. 기존 우상 검수에서는 정지 자세에 가까운 구간과 리그보다 약한 발 들림·무릎 굽힘이 지적됐다. 이 판정을 다른 세 방향까지 검증 없이 확대하지 않는다.

검수 시 베이스라인 대비 체형 비율, 리그의 팔·다리 포즈 재현, 발 접지·들림, 프레임별 크기·지면 위치, 마지막→첫 프레임 접합을 확인한다. 6프레임 추출만으로 완전한 보행 주기가 보장되지는 않는다. 최종 품질 승인은 사용자에게 있다.

원본 생성 기록과 기존 리포트는 유지하며, 이번 리포트의 커밋은 별도 지시 전까지 수행하지 않는다.

# 4방향 걷기 ImageGen 스프라이트 통합 리포트

## 보존 범위와 판정

기존 우상 리포트와 최신 좌하·우하·좌상 비율 보강 재생성 결과를 한 리포트에 보존한다. **네 방향 모두 검수 후보이며, 베이스라인 비율 일치나 자연스러운 루프가 승인된 결과는 아니다.** 기존 리포트와 실험 원본은 유지한다.

우상은 기존 v1 이미지젠 결과이며, 나머지 세 방향은 베이스라인 체형 비율을 강화한 v2 프롬프트로 재생성했다. 따라서 네 방향을 동일 프롬프트 조건의 비교 결과로 해석하면 안 된다. 이번 통합 과정에서 우상 이미지를 재생성하지 않았다.

## 방향별 결과

| 방향 | 프롬프트 | PNG | GIF | 참조 비교 GIF | 원문 |
|---|---|---|---|---|---|
| 좌하 | v2 | [시트](down_left/sprite-sheet-6x384.png) | [재생](down_left/preview-4fps.gif) | [베이스라인 비교](down_left/baseline-comparison-4fps.gif) | [프롬프트](down_left/prompt.txt) |
| 우하 | v2 | [시트](down_right/sprite-sheet-6x384.png) | [재생](down_right/preview-4fps.gif) | [베이스라인 비교](down_right/baseline-comparison-4fps.gif) | [프롬프트](down_right/prompt.txt) |
| 좌상 | v2 | [시트](up_left/sprite-sheet-6x384.png) | [재생](up_left/preview-4fps.gif) | [베이스라인 비교](up_left/baseline-comparison-4fps.gif) | [프롬프트](up_left/prompt.txt) |
| 우상 | v1 | [시트](up_right/walking-up-right-sheet-6x384.png) | [재생](up_right/walking-up-right-sheet-preview.gif) | [베이스라인 비교](up_right/baseline-comparison-4fps.gif) | [프롬프트](up_right/prompt.txt) |

참조 비교 GIF는 왼쪽에 해당 방향 베이스라인을 고정하고, 오른쪽에 결과를 재생한다. 우상 비교 GIF는 통합 시 추가 제작했으며 나머지 세 비교 GIF는 최신 검수 자료의 사본이다.

## 공통 규격

- 모션: walking-v13, 원본 프레임 1·5·9·13·17·21 순서.
- 방향당 6열 × 1행, 셀 384×384px, 시트 2304×384px, PNG RGBA.
- GIF: 4 FPS, 프레임당 250ms, 1.5초 반복. GIF 배경은 검수용 흰색.
- **384px는 셀 크기다. 캐릭터 실높이는 약 352px 이하이며 실높이 384px 규격으로 승인된 것이 아니다.**
- 포즈 원본은 ANNY 입력·AnyPose 0.7/0.7·30스텝·Lightning 해제·512px 결과다. 이를 방향별 캐릭터 참조와 함께 내장 image_gen 도구에 입력했다.

## 참조와 보정 방식

각 방향 폴더에 `identity-reference.png`, `source-six-frames.png`, `imagegen-original.png`, `prompt.txt`, `result.json`, `execution.log`를 보존했다. v2는 베이스라인만 체형·의상·아이덴티티 기준으로 사용하고 입력 스트립은 관절 포즈만 전달하도록 지시했다. 머리·몸통·팔다리 비율과 동일 배율을 유지하며, 무릎 굽힘으로 생긴 높이 차이를 개별 확대해 보정하지 않도록 명시했다.

시트 패킹은 방향별 공통 배율로 축소하고 각 셀 가로 중앙·하단 기준선에 배치했다. 방향 사이에 동일한 해부학적 실측 배율을 확정한 것은 아니다. 베이스라인 비교에서는 흰 여백을 제외한 참조 바운딩박스를 균일 축소해 최대352px로 표시했고, 생성 시트 셀은 그대로 사용했다. 이 표시 정규화는 관절 길이 측정이나 체형 일치 증명이 아니다.

## 남은 검수 항목

1. 베이스라인 대비 머리/몸통 비율, 어깨 너비, 다리 길이·두께, 손·신발 크기.
2. 같은 방향의 프레임 간 체형 유지와 네 방향 사이의 체형 일관성.
3. 발 들림·무릎 굽힘·지지발 전환, 정지 자세 인상, 마지막→첫 프레임 연결.
4. 투명 경계의 색 잔여물과 노이즈, 신체 잘림, 지면 앵커 변화.

시트 치수·RGBA 모드, 각 GIF의 6프레임·250ms 간격과 보존 사본 해시를 확인했다. 최종 품질 승인과 정식 에셋 등록은 별도다.

## 출처

- 우상 원본 리포트: `report/walking-up-right-imagegen-sheet-20260928-165303/`.
- 세 방향 최신 실험: `.tmp/test/walking-imagegen-proportion-regeneration/2026-09-28_22-41-41/`.
- 세 방향 베이스라인 비교: `.tmp/test/walking-baseline-comparison/2026-09-28_22-42-43/`.
- [통합 manifest와 파일 해시](manifest.yaml).

각 방향의 원본 result/manifest에는 당시 출처 경로가 그대로 남아 있다. 통합 사본의 실제 경로는 이 README와 최상위 manifest를 따른다. 필요한 참조·시트·프롬프트·GIF는 이 리포트 안에 복사되어 있어 검수 열람에 실험 폴더가 필요하지 않다.

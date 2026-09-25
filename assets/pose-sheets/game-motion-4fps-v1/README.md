# 게임용 포즈 시트 · 4fps

승인된 OpenPose COCO18 신체 프레임(얼굴 제외)을 원본 픽셀 그대로 배치했다. HumanML3D 관절 시트나 ANNY 외형 시트가 아니다. 리사이즈·프레임 생략·모션 재생성 없이 512×512 셀, 왼쪽→오른쪽→다음 행 순서를 사용한다. **4열 한 행 = 1초**, 프레임당 **250ms**이다.

|모션|프레임|재생 시간|방향별 시트|
|---|---:|---:|---|
|스탠딩 v3|16|4초|4열×4행 1장|
|걷기 v8|32|8초|4열×8행 1장|
|스트레칭 v1|120|30초|4열×8행 3장 + 4열×6행 1장|

스트레칭 페이지는 1~32, 33~64, 65~96, 97~120프레임이다. 페이지 경계에서도 250ms 간격으로 다음 프레임을 재생한다. 마지막 페이지 뒤 처음으로 돌아갈지는 게임 동작 정책에서 결정하며, 이 시트가 닫힌 루프를 보장하지 않는다.

원본 모션의 20fps를 4fps로 다운샘플링한 것이 아니라, 등록 에셋의 4fps 재생 기준으로 모든 프레임을 유지했다. 기존 걷기 v8 시트 및 기본 설정은 보존했다.

## 파일

### standing-v3

- down_left: [시트 1](standing-v3/down_left/page-01.png)
- down_right: [시트 1](standing-v3/down_right/page-01.png)
- up_left: [시트 1](standing-v3/up_left/page-01.png)
- up_right: [시트 1](standing-v3/up_right/page-01.png)

### walking-v8

- down_left: [시트 1](walking-v8/down_left/page-01.png)
- down_right: [시트 1](walking-v8/down_right/page-01.png)
- up_left: [시트 1](walking-v8/up_left/page-01.png)
- up_right: [시트 1](walking-v8/up_right/page-01.png)

### stretch-v1

- down_left: [시트 1](stretch-v1/down_left/page-01.png), [시트 2](stretch-v1/down_left/page-02.png), [시트 3](stretch-v1/down_left/page-03.png), [시트 4](stretch-v1/down_left/page-04.png)
- down_right: [시트 1](stretch-v1/down_right/page-01.png), [시트 2](stretch-v1/down_right/page-02.png), [시트 3](stretch-v1/down_right/page-03.png), [시트 4](stretch-v1/down_right/page-04.png)
- up_left: [시트 1](stretch-v1/up_left/page-01.png), [시트 2](stretch-v1/up_left/page-02.png), [시트 3](stretch-v1/up_left/page-03.png), [시트 4](stretch-v1/up_left/page-04.png)
- up_right: [시트 1](stretch-v1/up_right/page-01.png), [시트 2](stretch-v1/up_right/page-02.png), [시트 3](stretch-v1/up_right/page-03.png), [시트 4](stretch-v1/up_right/page-04.png)

## 재사용

선택 설정: `generators/animation/config/default_game_pose_sheets.yaml`. 상세 프레임 순서·페이지별 시작 시간·원본 및 결과 해시는 `manifest.yaml`에 보존한다. 게임 런타임으로 복사·등록한 상태는 아니다.

생성기: `generators/animation/build_game_pose_sheets.py`. 기존 경로를 덮어쓰지 않으며 변경 시 새 시트 버전으로 생성한다.

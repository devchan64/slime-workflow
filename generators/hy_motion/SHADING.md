# VNCCS 기본 셰이딩

HY-Motion의 ANNY 정사영·원근투영 및 제약 비교 렌더는
`official_shading.py`의 `vnccs-white-ambient-rim-cycles-v1`을 공통 적용한다.
기존 면광원 2개와 AgX 대신 다음 공식 설정을 Cycles 재질로 구현한다.

- 출처: `AHEKOT/ComfyUI_VNCCS_Utils`, revision
  `eedaed79a7c42d2570d832cc5d2e0a2da5ab022d`,
  `web/vnccs_pose_studio_core.js`의 Phong 재질과 윤곽 암부.
- 공식 QI2.1 워크플로우의 `keepOriginalLighting=true`, 흰색 캐릭터,
  흰색 환경광 강도 1, 텍스처 없음. 직접광이 없어 specular 항은 0이다.
- 환경광 확산 반사 `1/π`를 sRGB로 변환한 뒤
  `1 - (1 - abs(camera_normal.z))^3 * 0.4`를 곱한다.
- 출력 색을 선형 값으로 역변환해 Emission에 넣고 Standard/sRGB로 저장한다.
  추가 조명·노출·AgX·접촉 그림자를 섞지 않는다.

이는 공식 설정의 **Blender 이식 구현**이며 공식 WebGL 엔진 자체가 아니다.
보간 노멀의 정규화와 경계 안티앨리어싱 때문에 픽셀 동일성을 보장하지 않는다.
프로필·출처 revision·계산 계수·구현 차이를 `render-manifest.json`의
`shading`에 기록한다. 기존 카메라·모션·리타게팅·OpenPose는 바꾸지 않는다.
RGBA 출력과 포즈 참조의 흰색 배경 합성 계약도 유지한다.

새로 렌더하는 결과부터 적용하며 기존 생성 결과와 등록된 걷기 v1은 덮어쓰지
않는다. 별도 브라우저 런타임이나 서비스는 추가하지 않는다.

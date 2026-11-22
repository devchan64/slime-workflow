# 3D 생성 후보 벤치마크 검토

확인일 2026-11-22. 목표는 캐릭터의 자동 리깅과 전투 모션이며, 아래 공개 벤치마크는 주로 정적 형상을 평가하므로 리깅 성공률을 보장하지 않는다.

## 공개 사람 선호도 비교

[Rapidata Image-to-3D](https://huggingface.co/datasets/Rapidata/image-to-3d-single-object-human-feedback-benchmark/blob/main/README.md)는 단일 이미지 357개, 비교 70,011건, 367,873표를 보고한다. 동일 입력의 회전 렌더를 두 개씩 비교하고 회색 재질 형상 점수를 Bradley–Terry/Elo 척도로 산출했다. Tripo H3.1 1254(4위), TRELLIS.2 1095(7위), Pixal3D 745(11위), TRELLIS 1 702(13위). 점수는 성공률이 아니고 수치·순위는 갱신된다. TripoSR과 TripoSG는 이 표에 없어 같은 점수로 비교 불가. Tripo H3.1은 유료 이용 조건을, TRELLIS.2·Pixal3D는 제3자 의존성을 확인해야 한다.

## 합성 정답 형상 비교

[Sprint3D 연구진 공개 표](https://alaya-lab.github.io/sprint3d/)의 Toys4K 테스트 2,653개에서 입력 시점 실루엣 IoU는 Pixal3D 96.97%, TRELLIS.2 79.55%, TripoSG 59.87%; Chamfer 거리 ×10⁻³은 각 26.61, 28.01, 58.62(낮을수록 좋음). 프레임 정렬 없이 평가한 수치이고 특정 데이터셋 및 측정 방식이다. 자체 연구의 Pixal3D 기반 최적화와 비교한 기술 보고서다. 단일시점 실루엣은 뒤쪽 형상·손과 몸의 연결·리깅 결과를 검증하지 못한다. TripoSG 내부 FlashVDM 지역 조건은 별도 라이선스 검토에서 보류했다.

## TripoSR 단서

[notjustchairs.ai 비교](https://notjustchairs.ai/benchmark)의 자체 5점 종합은 TRELLIS 1 4.8, TripoSR 2.9로 보고된다. 소수의 사물 중심 비교 및 평가자의 판단이므로 캐릭터나 리깅 품질로 일반화할 수 없다. [TripoSR 공식 저장소](https://github.com/VAST-AI-Research/TripoSR)는 MIT 코드·가중치 및 기본 정점색 출력을 명시한다. TripoSR이 Rapidata 또는 위 Toys4K 표에 없으므로 점수를 결합해 순위를 만들지 않는다.

결론: Pixal3D는 형상 성능을 시험할 가치가 높으나 코드·가중치 MIT 표기만으로 전체 의존성의 상업적 승인은 불가하다. TRELLIS.2도 동일. Tripo 유료 콘텐츠는 게임 상업 이용을 약관에서 허용하나 비용·입력 권리·비공개 설정 확인이 필요하다. TripoSR은 모델 자체의 라이선스는 단순하지만 위 사물 비교에서 품질 우세가 입증되지 않았다. 실제 선택은 라이선스 통과 경로에 한해 동일 캐릭터의 손·몸 분리, 자기 교차, 자동 리깅 및 팔 변형 성공률을 측정해야 한다. [라이선스 상세](3d-model-alternative-license-review.md).

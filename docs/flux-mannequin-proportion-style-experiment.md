# FLUX 마네킨 피부·기본복 비율과 화풍 비교안

## 관찰과 목표

2026-11-16 얼굴 합성 마네킨에 피부와 기본복을 적용한 결과는 4방향 배치를 유지했지만, 허벅지·종아리와 몸통·골반 윤곽이 달라졌고 원본보다 입체적·사실적인 표현으로 바뀌었다. 얼굴은 다시 그려졌다. 이 결과는 공용 화풍 v1.5.0 원문을 넣지 않은 단일 시험이므로 화풍 문구 유무나 특정 원인을 단정하지 않는다.

이번 비교의 목적은 기준 전신의 신체 비율과 얼굴을 최대한 보존하면서 공용 화풍 v1.5.0에 가까운 피부·기본복을 얻는 것이다. 기존 기준과 후보는 자동 교체하지 않는다.

## 고정 조건

- 첫 참조는 얼굴 합성 시험 결과 `.tmp/test/flux3-mannequin-face/2026-11-16_1205-image/result.png`다. 실행 전 파일 SHA-256을 계산하고 각 작업 기록에 남긴다. 임시 후보이므로 유실되면 같은 이름의 다른 이미지로 대체하지 않는다.
- FLUX 3 Image Klein revision `09561231f44e41381c461caf53d5452005a60ac9`, 768×1152, 16스텝, BF16, VAE FP32, 1장 출력. 모델 단위 CPU 오프로드와 GPU 대기열을 사용한다. 마스크 국소보정과 VAE 타일 인코딩·디코딩은 사용하지 않는다.
- 기본복은 신체 윤곽과 팔다리가 잘 보이도록 몸에 밀착되는 회색 민소매 크롭 상의와 짙은 회색 짧은 반바지로 통일한다. 상의는 허리선 위까지, 하의는 허벅지 위쪽까지만 덮고 속옷처럼 해석되지 않는 단순한 운동복 형태로 한다. 네 방향 모두 같은 복장과 길이를 유지한다.
- 세 조건은 동일한 새 무작위 시드를 공유한다. 비교를 위한 시드 고정이며, FLUX에서 다른 시드로 재현되는지는 별도 반복 실험이다. 모델·참조·해상도·스텝·시드·출력·원문·단어 수·실제 최종 프롬프트·해시·시간·메모리 피크를 기록한다.
- 공용 화풍은 `prompts/common/art-style-v1.5.0.yaml`의 영문 `prompt` 원문을 수정 없이 **각 조건의 최종 문장 뒤에 그대로 한 번** 붙인다. 버전은 `1.5.0`, 원문 SHA-256은 `ca366d541fda72a98d6746a0cbf8d01c008398b15f8dcc0226a49cc3231000c7`이다. 실행 직전 원문 해시를 검증한다.
- 아래는 완성형 장면 캡션이므로 확장기가 원문을 다시 쓰지 않도록 확장 단계를 생략하고 정확한 최종 캡션을 모델에 전달한다. 이 선택은 공식 확장기 경로와 다른 실험 조건이며 품질 저하 가능성을 결과에 기록한다. 마네킨 원본의 프로필은 이미지 기준 오른쪽을 향한다.

## 조건

**A — 화풍 원문을 추가한 기준.** 첫 참조 1장. 아래 문장 뒤에 공용 화풍 v1.5.0 원문을 붙인다.

> A 2-by-2 four-view character sheet on a plain white background. Edit the first image: replace the articulated mannequin material and joints with smooth natural skin, and dress all four figures in a close-fitting gray sleeveless cropped athletic top ending above the waist and dark close-fitting short athletic shorts ending high on the thighs. Preserve the reference's head-to-body proportions, body silhouette, limb thickness, faces, poses, view directions, scale and layout.

**B — 비율과 2D 재질 지시 강화.** 첫 참조 1장. 아래 문장 뒤에 같은 화풍 원문을 붙인다. A와 달라지는 요인은 캡션이며, 표현 강화가 개선으로 이어질지는 미검증이다.

> A flat 2D four-view character turnaround on a plain white background, in exactly the same 2-by-2 arrangement as the first image. Transform the articulated mannequin into a skin-covered figure wearing a close-fitting gray sleeveless cropped athletic top ending above the waist and dark close-fitting short athletic shorts ending high on the thighs. Keep the same short athletic garments in all four views. In every view preserve the existing head size relative to the full body, broad rounded thighs and calves, shoulder width, hip width, waist shape, torso length, limb lengths, hand and foot size, stance and facial features. Keep the exact original front, three-quarter, right-facing profile and back views. Use clear fine warm brown contour lines and softly grouped cel-shaded shapes for the skin and clothes; the top and shorts closely follow the same body outline.

**C — 기존 2D 피부·기본복 이미지를 화풍 참조로 추가.** B와 완전히 같은 최종 캡션과 첫 참조를 사용하고, `baseline/mannequin/neutral-body-skin-clothes-four-directions.png`를 두 번째 참조로 추가한다. B의 첫 문장 앞에 다음 한 문장만 추가한다. 두 번째 이미지가 형태까지 영향을 줄 수 있으므로 화풍 전용으로 작동한다고 가정하지 않는다. 둘째 참조의 해시도 기록한다.

> Use the second image only as a reference for flat 2D linework, shading and material rendering; use the first image for the figures' anatomy, face, poses and placement.

## 검수 및 판정

기준·A·B·C를 동일 배율로 나란히 표시한다. 각 방향에서 머리 대비 전체 높이, 어깨·허리·골반 폭, 허벅지와 종아리의 최대 폭, 팔다리 길이·손발 크기와 관절 위치를 비교한다. 옷에 가려진 부위는 추정하지 않고 판정 불가로 표시한다. 정면·사선·측면의 얼굴 특징과 뒷머리, 4방향 배치도 확인한다.

복장은 상·하의가 몸에 밀착되고 짧은지, 허리와 허벅지의 윤곽이 드러나는지, 네 방향에서 길이와 형태가 일치하는지 확인한다. 화풍은 따뜻한 갈색 윤곽선, 단순한 형태, 셀 음영과 절제된 하이라이트를 확인한다. 특히 피부의 사진풍 질감, 입체 렌더링 같은 명암 및 옷 주름이 원본보다 과도한지 기록한다. 실제 기준 이미지를 육안 검토하고 원본과 차이가 없다고 과장하지 않는다.

가장 적합한 조건이 있어도 동일 설정의 새 시드 최소 2회로 비율과 화풍을 반복 확인한 뒤 후보로 제시한다. 반복 결과 중 비율이 달라지면 그 범위와 실패 사례를 함께 보존한다. 한 번의 결과만으로 일반적인 우열이나 채택을 결론내리지 않는다.

## 2026-11-16 1차 결과

- 세 조건 모두 완료. 공통 시드는 `1770797539`, 첫 참조 SHA-256은 `2da3cc936b6acd9a8bb9d45eac054e73bf247b9358b44badc3da6a930d910e90`다. 결과와 같은 배율 비교는 `.tmp/test/flux3-proportion-style/2026-11-16/`에 있다. 동일 시드 한 번씩의 관찰이다.
- A: 최종 110단어, SHA-256 `0964af0285b94269e561b06a4dd2e1f1867a914bd32479161325927627742bf3`, GPU 관측 피크 32604 MiB. 네 방향과 얼굴은 유지됐으나 반바지는 허벅지 중간까지 내려오고 무릎에 옅은 관절 흔적이 남았다.
- B: 최종 177단어, SHA-256 `d8141b5da6714ed482c5a9313fecdb7ef71608b366ec600fddb5c08deb0c1536`, GPU 관측 피크 32811 MiB. A와 비슷하게 짧아야 할 하의가 길고 관절 흔적이 남았다.
- C: 최종 205단어, SHA-256 `9395feae8a7a01360798b95795fbc75239aa006147fca0c73c52d15752ade76a`, GPU 관측 피크 51679 MiB. 짧고 밀착된 복장에는 가장 가깝지만 무릎과 팔에 옅은 원형 관절 자국이 남고 첫 참조에 비해 팔다리와 몸통 윤곽이 달라졌다. 두 참조와 추가 지시문이 함께 바뀌었으므로 참조 추가만의 효과로 단정할 수 없다.
- 세 결과는 직전 사진풍 피부 시험보다 2D 윤곽과 셀 음영에 가깝지만, 원문만의 효과는 동일 입력·동일 시드의 무화풍 대조가 없어 단정하지 않는다. 실측 없이 신체 비율이 완전히 유지됐다고 판정하지 않는다. C가 복장 조건에 가장 가깝지만 관절 잔상과 비율 변화가 있으므로 채택하지 않으며, 새 시드 반복 시험도 아직 수행하지 않았다.

## C 수정 샘플 — 관절 흔적 제거

사용자는 C의 신체 비율을 적합하다고 판단했다. 기존 C와 같은 두 참조·시드·설정을 사용하고, 공용 화풍 v1.5.0 원문 바로 앞에 다음 지시만 추가해 피부를 연속적으로 표현하는지 비교한다. 마스크와 VAE 타일링은 사용하지 않는다. 피부 지시가 C의 비율이나 복장을 바꾸지 않는지도 확인한다.

> Render continuous smooth skin at the shoulders, elbows, wrists, hips, knees and ankles in every view. Replace all visible circular mechanical joint outlines and seam marks with natural uninterrupted skin and shading while preserving the same body shape and proportions.

### C 수정 샘플 결과

- 결과: `.tmp/test/flux3-proportion-style/2026-11-16/D/result.png`, 비교: `.tmp/test/flux3-proportion-style/2026-11-16/D/comparison.png` (입력 마네킨·C·D 순서).
- 같은 두 참조, 시드 1770797539, 16단계와 768×1152 설정으로 실행했으며 수정 프롬프트는 245단어다. 공용 화풍 v1.5.0 원문을 유지했다.
- 육안으로 D의 체형과 짧고 밀착된 복장은 C와 매우 비슷하다. 다만 정면과 사선의 무릎에 원형 관절 흔적이 여전히 뚜렷하게 남아 있어, 추가 지시만으로 제거에 성공했다고 보기 어렵다. 피부 명암과 선에도 작은 차이는 있지만 화풍 개선을 확인하기 어렵다.
- 결과는 고정 시드 한 번의 비교이므로 반복 재현성이나 다른 시드에서의 효과를 판단할 수 없다. 베이스라인은 교체하지 않았다.

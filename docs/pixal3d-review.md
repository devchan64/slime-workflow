# Pixal3D 검토

검토일: 2026-11-22. 현재 사용한 TRELLIS 1의 A포즈 결과와 비교할 후보. 이 문서는 공개 소스 조사이며 실제 다운로드·추론·라이선스 전수 감사는 하지 않았다.

## 모델과 품질

[공식 저장소](https://github.com/TencentARC/Pixal3D)는 TRELLIS.2 기반 최신 코드와 별도 paper 브랜치, 단일 시점 및 별도 다중 시점 가중치·추론을 설명한다. [모델 카드](https://huggingface.co/TencentARC/Pixal3D)는 MIT로 표시되며 공식 [NOTICE](https://huggingface.co/TencentARC/Pixal3D/blob/main/NOTICE)는 공개된 코드·파라미터·가중치가 MIT임을 밝히되 제3자 조건 적용을 명시한다.

[Sprint3D의 Toys4K 2,653개 결과](https://alaya-lab.github.io/sprint3d/)에서는 Pixal3D 실루엣 IoU 96.97%, TRELLIS.2 79.55%; Chamfer 거리 ×10⁻³ 각각 26.61과 28.01이다. 카메라 좌표 정렬을 수행하지 않은 입력 시점 기반 지표다. [Rapidata 사람 평가](https://huggingface.co/datasets/Rapidata/image-to-3d-single-object-human-feedback-benchmark/blob/main/README.md)의 형상 선호도는 Pixal3D 745, TRELLIS.2 1095다. 데이터셋·지표가 다른 결과이며 점수는 리깅 성공률이 아니다. 어느 쪽도 현재 캐릭터의 손 분리나 스키닝을 검증하지 않는다.

## 상업 이용 경로

공식 다중 시점 [설정](https://huggingface.co/TencentARC/Pixal3D/blob/main/pipeline_mv.json)은 `facebook/dinov3-vitl16-pretrain-lvd1689m`과 `briaai/RMBG-2.0`을 지정한다. [DINOv3](https://github.com/facebookresearch/dinov3/blob/main/LICENSE.md)는 MIT가 아닌 별도 라이선스이며 사용 제한과 재배포 조건을 확인해야 한다. BRIA [RMBG-2.0](https://huggingface.co/briaai/RMBG-2.0) 공개 가중치는 비상업용이며 상업용 자체 호스팅에는 별도 계약이 필요하다. 이미 마스킹한 RGBA를 쓰면 전처리 호출을 피할 가능성이 있지만 로더 초기화·다운로드·실행 여부까지 확인해야 한다.

공식 [inference_mv.py](https://github.com/TencentARC/Pixal3D/blob/master/inference_mv.py)는 `o_voxel.postprocess.to_glb`를 호출하며 TRELLIS.2의 [해당 구현](https://github.com/microsoft/TRELLIS.2/blob/main/o-voxel/o_voxel/postprocess.py)은 nvdiffrast를 사용한다. 공식 설치가 지정하는 [nvdiffrast v0.4.0](https://github.com/NVlabs/nvdiffrast/blob/v0.4.0/LICENSE.txt)은 비상업용 사용 조건이다. 형상만 별도 저장하고 외부 정점 색상 투영을 적용하는 방안을 검토하되, 실제로 비상업 구성요소를 불러오거나 실행하지 않는지와 다른 의존성의 조건을 검증하기 전 상업 이용을 승인하지 않는다.

## 다중 시점과 AMD

[공식 다중 시점 설명](https://github.com/TencentARC/Pixal3D#multi-view-inference)은 각 이미지의 4×4 카메라 변환 행렬과 수평 시야각이 담긴 `transforms.json`을 요구한다. 현재 AI 생성 8방향 그림은 실제 카메라 행렬과 정확한 각도·자세 일치가 검증되지 않았다. 45도 균등 각도는 실험 가정으로만 기록해야 하며 정답으로 가정하지 않는다. 정면 단일 입력 대조와 다중 입력을 구분해 검사한다.

공식 설치는 TRELLIS.2와 CUDA 중심 NATTEN을 전제로 하므로 AMD ROCm에서 공식 구현 실행은 미검증이다. 제3자 [AssetFurnace](https://github.com/Bingeljell/image-to-3dlab)는 별도 C++/GGML Pixal3D 경로를 Linux ROCm의 Ryzen AI Max+ 395/gfx1151에서 시험했다고 주장한다. 이는 우리 장비 및 우리 ROCm 10.0 환경에서의 독립 재현이 아니며, 동일 모델·정밀도·다중 시점 지원·의존성 라이선스를 확인하지 않았다. 해당 경로에 DINOv3 조건도 표시돼 있다. GPU 대기열, 환경 격리 및 라이선스 원문 확인이 선행되어야 한다.

## 판정

품질 비교 가치가 있으나 상업용 결과물로 승인할 근거는 아직 부족하다. 우선 고정 버전별 가중치·제3자 고지와 실제 실행 경로를 확인하고, 상업용 허용 전처리·형상/정점색 출력으로 격리 시험한다. 이후 생성 성공과 비유한값·파편·자기 교차·손/몸 연결을 기록하고 자동 리깅·스키닝·무기 부착 및 변형을 별도로 검증한다. 최종 2D 영상 생성 도구와 참조 이미지 권리도 별도다.

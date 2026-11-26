# MiniMax H3 Image LCM 실험 준비

LCM을 새 요청의 기본값으로 사용한다. lcm_experiment.py의 후보는 독립 생성 화면과 통합 CLI에서 선택할 수 있고, 대화 접수폼의 새 작업에도 적용된다. 과거 샘플러 기록이 없는 작업은 Euler로 해석한다.

ComfyUI의 LCM은 모델의 denoised 추정에 매 단계 새 노이즈를 섞는다. MiniMax의 flow 노이즈 혼합과 현행 velocity 부호를 이용한 후보 계산을 준비했다. 커뮤니티에서 제안한 시작 1.10, 종료 0.90의 선형 노이즈 배율은 실험 조건이며 공식 권장이나 품질 보증이 아니다. [ComfyUI LCM 구현](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy/k_diffusion/sampling.py), [실험 보고](https://pixlstash.dev/minimax-h3-image.html).

## 추가 검증 과제

- ComfyUI의 MiniMax flow noise_scaling, 모델 출력 부호·정밀도, sigma 배열 및 배율 보간 인덱스를 고정 버전의 구현과 수치 비교한다. 현재 후보의 동등성은 미확인이다.
- 독립 CPU 난수 생성기와 시드·상태·샘플링 방법을 작업별로 기록하고, 같은 시드 반복·다른 시드 분리·마지막 sigma 0에서 무노이즈를 검증한다. 참조 이미지 잠재값과 초기 노이즈는 기존 경로와 같아야 한다.
- 각 단계와 최종 결과의 비유한 값을 실패 처리하고, 별도 프로세스를 포함한 VRAM·시간·환경과 모든 입력·참조 해시·sigma·배율·샘플러 버전을 보존한다.
- 6스텝 Euler와 후보 LCM을 같은 참조·시드·프롬프트·크기에서 비교하고 여러 시드 및 실제 GPU 결과를 시각 검수한다. 이미지 품질과 일관성 개선을 사전 가정하지 않는다.
- GUI·CLI 계약과 이력 복원, 실제 화면 및 실제 GPU 작업의 선택 경로를 검증한다. 실험 기본값을 기존 작업에 소급 적용하지 않는다.

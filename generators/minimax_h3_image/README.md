# MiniMax H3 이미지 생성

텍스트 프롬프트로 한 장을 생성하는 실험 기능입니다. INT8 ConvRot 이미지 변환기와 기존 INT8 텍스트 인코더, 이미지 전용 VAE를 사용합니다. 기본 크기는 1024×1024이며 6스텝입니다. 참조 이미지와 편집은 아직 지원하지 않습니다.

비상주 스트리밍 실행을 목표로 합니다. 전체 모델의 GPU 상주는 사용하지 않습니다. 스트리밍 배치와 호스트·GPU 메모리 및 ROCm 수치 검증이 완료될 때까지 생성 요청은 차단됩니다. 첫 시험은 메모리 계획 단계에서 실패했으며 생성된 이미지는 없습니다. 기본 SDPA에서 유한한 출력도 잘못될 수 있습니다.

통합 CLI: `python3 tools/manager.py command minimax-h3-image generate --prompt 'A small red house in a meadow' --seed 42 --detach`. 생성 ID로 `status`, `logs`, `cancel`, `prioritize`, `history-delete`를 사용합니다. 게이트웨이가 이전 코드로 실행 중이면 새 서비스를 인식하지 못하므로 기존 작업을 확인한 후 정식 절차로 재시작해야 합니다.

모델은 MiniMax-H3-Image Community License와 해당 지역의 별도 사용 허가 조건을 따릅니다. 이미지 모델의 허가는 영상 모델과 별개입니다.

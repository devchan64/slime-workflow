# AnimationGPT 추론 준비

이 디렉터리는 생성기 서비스가 아니라 데이터셋 없이 모델을 불러오는 실험용 추론 구성이다. 관리 게이트웨이, GPU 대기열, GUI, 생성 이력, 영상 또는 무기 트랙 출력은 연결되지 않았다. 현행 Kimodo 서비스를 변경하지 않는다.

공식 MotionGPT 소스 `001aaca8d0ee218fc17f8265d11ac124044fe42f`를 `.local/animationgpt/upstream`에 준비하고 모델 관리의 AnimationGPT 파일을 사용한다. 모델은 제3자 FP16 변환본이다. 입력과 출력 임베딩은 다른 가중치이므로 Transformers 5에서 원본 FLAN-T5의 `tie_word_embeddings=false`를 명시적으로 복원한다. 모델이 모션 경계를 누락하면 공식 코드의 `[0]` 대체 출력을 받아들이지 않고 실패한다.

2026-11-22 CPU 시험: 전체 CombatMotion 데이터셋 없이 `a man holding a katana and swinging his sword diagonally downward.`와 시드 42에서 26개 모션 토큰, 20fps 104프레임, 프레임당 22개 관절의 유한 좌표를 반환했다. 원본 웹 UI의 정규화 통계를 사용했으며 CMP 학습 분포에 적합한지 검증하지 않았다. 재생·시각 품질·검술 정확도·ROCm·GPU 대기열은 검증하지 않았다. 결과에는 무기 형상과 무기 궤적이 없으므로 영상 생성의 무기 유지 문제를 해결했다고 볼 수 없다.

모델 파일의 출처·라이선스와 다운로드는 모델 관리 설명을 따른다. 실행 전 모델 해시, 공식 소스 리비전·변경 여부 검증과 격리된 작업 프로세스가 필요하다.

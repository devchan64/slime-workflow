# 3D 모델 대체 후보 라이선스 검토

검토일: 2026-11-22. 목적은 생성 메시와 그 모션 영상·스프라이트의 상업적 이용 가능 여부다. 모델의 라이선스, 실제 사용하는 전처리·추론·후처리 도구의 조건, 참조 이미지의 권리를 구분한다. 아래는 공식 공개 자료 검토이며 실행 경로 전수 감사나 법률 자문은 아니다.

| 후보 | 공식 고지 | 현재 판정 |
|---|---|---|
| TripoSR | [코드와 가중치 MIT](https://github.com/VAST-AI-Research/TripoSR), [가중치 카드](https://huggingface.co/stabilityai/TripoSR). 기본 출력은 정점 색상. | 모델 자체에 비상업 제한은 보이지 않는다. 실제 전처리·메시 추출 의존성, 입력 권리, ROCm 실행 미검증. 비교 후보로 추가 조사. |
| Pixal3D | [코드](https://github.com/TencentARC/Pixal3D) 및 [가중치 카드](https://huggingface.co/TencentARC/Pixal3D) MIT 표시. [NOTICE](https://github.com/TencentARC/Pixal3D/blob/master/NOTICE)에서 제3자 조건 별도. 기본 설정은 TRELLIS.2 계열. | DINOv3·BRIA·NVIDIA 등 실제 버전별 사용 경로를 확인하고 필요 시 교체해야 한다. 전체 상업용 승인 전. |
| TripoSG | [최상위 코드](https://github.com/VAST-AI-Research/TripoSG/blob/main/LICENSE)와 [가중치 카드](https://huggingface.co/VAST-AI/TripoSG)는 MIT이나 [NOTICE](https://github.com/VAST-AI-Research/TripoSG/blob/main/NOTICE)는 FlashVDM 파생 코드를 명시. 내부 [triposg/LICENSE](https://github.com/VAST-AI-Research/TripoSG/blob/main/triposg/LICENSE)는 허용 지역에서 대한민국을 제외하고 출력의 지역 외 사용도 제한. 기본 추론은 [RMBG-1.4](https://huggingface.co/briaai/RMBG-1.4) 비상업용 가중치를 다운로드·실행. | 적용 범위와 권리자 추가 허락이 확인되기 전 한국 상업 프로젝트 비교군에서 보류. 최상위 MIT 표기만으로 승인 불가. |
| Tripo H3.1 서비스 | [약관 5.2.2](https://www.tripo3d.ai/terms)는 유료 콘텐츠 상업 사용·수정·배포를 명시. 유료 상태는 만료 후 유지된다고 명시. | 유료 비공개 경로는 이용 조건과 입력 권리를 충족하면 게임 제작 비교 가능. 무료 결과물은 요금 페이지·도움말과 약관의 고지가 충돌해 제외. 유료 실험은 계정·비용 필요. |
| Stable Fast 3D | [공식 모델 카드](https://huggingface.co/stabilityai/stable-fast-3d)는 연 매출 100만 달러 이상인 조직 등의 상업적 이용·출력에 별도 기업 라이선스 요구. | 매출 조건이나 추가 계약이 있어 사용자 요청의 제한 없는 기준에 부적합. |
| Hunyuan3D 2.0/2.1 | [2.0](https://github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/main/LICENSE), [2.1](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/LICENSE) 기본 라이선스의 허용 지역에서 대한민국 제외. | 해당 기본 라이선스 그대로는 제외. |

TripoSG 내부 라이선스의 실제 적용 파일·가중치 범위는 권리자 확인 없이는 단정하지 않는다. TripoSR과 Pixal3D는 모델 자체가 MIT라는 것만 확인했으며, 전체 파이프라인의 상업적 이용이나 입력 이미지 권리를 보증하지 않는다. 각 모델의 ROCm 동작, 자동 리깅 성공률과 캐릭터 품질은 별도 검증이 필요하다.

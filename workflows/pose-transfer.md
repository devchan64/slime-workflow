# 포즈 변환 생성기

애니메이션 도구의 `?tool=pose-transfer-generator&category=animation-tool`에서 Qwen Image 2.1로 단일 장면의 포즈를 변환한다.

- 아이덴티티 이미지 1장, 포즈 이미지 1장이 필수다. 순서는 외형 → 포즈로 고정한다. 외형 이미지에서 얼굴·헤어·복장·신체 비율·화풍을, 포즈 이미지에서 자세·방향·관절 배치를 가져온다.
- 해상도는 512×512·768×768 중 선택하며 기본은 768이다. 스텝은 20·30·40·50 중 선택하며 기본은 40이다.
- 기본 프롬프트는 `generators/image/config/pose-transfer-prompt.txt`에서 관리한다. 입력 프롬프트는 1~99단어이며 원문·단어 수·해시를 기록한다.
- GUI와 CLI는 공용 게이트웨이의 `pose-transfer` 서비스를 사용한다. 생성·상태·로그·취소·재개·이력 조회·삭제·초기화를 공유한다. 결과는 자동으로 정식 에셋에 등록하지 않는다.
- 기록은 `.tmp/test/pose-transfer/<생성 ID>/`에 보관한다. 참조 이미지 두 장은 번호 순서로 스냅샷·해시를 저장한다. 기존 Qwen 이미지 생성 이력과 분리한다.

```bash
python3 tools/manager.py command pose-transfer generate --reference identity.png --reference pose.png --resolution 768 --steps 40 --seed 10107 --detach
python3 tools/manager.py command pose-transfer history
python3 tools/manager.py command pose-transfer status --id 생성ID
```

`--prompt` 또는 `--prompt-file`로 기본 문구를 대체할 수 있다. 이미지 입력은 RGB/RGBA PNG, 장당 3MB 이하이며 투명 영역은 Qwen 공통 입력 처리로 흰 배경에 합성된다. 모델은 코드에 고정하며 사용자가 선택하지 않는다. GPU 실행은 기존 독립 작업자와 대기열을 사용한다.

## 기본 프롬프트의 참조 역할

두 번째 이미지의 자세로 교체하고 첫 이미지의 캐릭터를 유지하도록 짧게 지시한다. 사용자 실험 `2026-10-05_20-54-52-3ffae086`에서 개선을 확인한 문구를 기본값으로 사용한다. 해당 실험과 동일한 `<image 1>`, `<image 2>` 표기를 유지한다. 공식 재작성 지침의 `<image1>` 표기와는 구분하며, 태그 공백의 효과는 검증하지 않았다. 신체 비율 보존 문구를 추가한 실험 `2026-10-05_21-02-33-ab5acca1`에서는 서 있는 자세로 되돌아가 해당 추가 문구를 제거했다. 이는 해당 실험의 검수 결과이며 모든 입력에 대한 품질 보장을 의미하지 않는다. 기존 실행 기록은 변경하지 않는다.

근거: [Qwen Image 2.1 공식 편집 프롬프트 지침](https://github.com/QwenLM/Qwen-Image-2.1/blob/main/prompt_rewrite/prompts/system_prompt_edit.txt). 100단어 미만 제한은 이 저장소의 운영 규칙이며 공식 모델 제한이 아니다.

포즈 변환 화면의 `고정 프롬프트 사용`은 기본 ON이다. ON이면 기본 문구를 표시하고 편집을 잠그며, OFF이면 직접 편집한다. OFF에서 작성한 문구는 ON/OFF 전환 시 보존한다. ON으로 전환할 때 추적된 기본 파일을 다시 읽으며, 화면에 표시된 문구를 그대로 공용 게이트웨이에 전달해 실행 기록에 저장한다. 전환은 생성을 실행하지 않는다. 이력 입력 복원은 OFF로 전환하여 당시 프롬프트를 그대로 복원한다. CLI에서는 프롬프트 생략 시 기본값, `--prompt` 또는 `--prompt-file` 지정 시 직접 입력을 사용한다.

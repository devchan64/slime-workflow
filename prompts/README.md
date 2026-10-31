# 에셋 제작 프롬프트

사용자가 지정한 제작 프롬프트의 관리 원본을 워크플로우로 이전했다. 백엔드의 이전 사본은 삭제한다. 이 디렉터리는 Git 추적 대상이며 명시적으로 이전한 제작 프롬프트의 보관 예외다. 게임 기획·설계 문서를 추가로 옮기는 근거로 사용하지 않는다.

## 버전 관리 공통 프롬프트

[공통 관리 문서](common/README.md)에서 화풍과 캐릭터 외관을 분리 관리한다.

| 기준 문서 | 버전 원문 | 상태 |
| --- | --- | --- |
| [화풍 관리](common/art-style.md) | [1.0.0](common/art-style-v1.yaml) | 생성 검증 전 |
| [캐릭터 외관 기준](common/character-appearance.md) | [1.0.0](common/character-appearance-v1.yaml) | 생성 검증 전 |

[변경 이력](common/CHANGELOG.md)을 누적하며 기존 생성기에 자동 연결하지 않는다.

## 프롬프트 색인

2026-10-31 기준. 이 폴더의 YAML 6개를 모두 포함한다. 상태는 제작 기록이며 생성기 자동 연결이나 현재 결과의 품질 보장을 뜻하지 않는다.

| 파일 | 선택할 원문 키 | 용도·입력 | 상태 |
| --- | --- | --- | --- |
| [art-style.yaml](art-style.yaml) | `common`, `categories`, `outputs`, `subject_template`, `negative` | 공통 화풍·대상·출력별 조합. 캐릭터 5등신 기준 포함 | 제작 기준 정의 |
| [building-orthographic-v1.yaml](building-orthographic-v1.yaml) | `prompt` + `required_inputs` | 실제 바닥 그리드·점유 밑면·출입구를 참조하는 단일 건물 | 채택 기준 v1 |
| [character-default-standing-v4.yaml](character-default-standing-v4.yaml) | `prompt_template` + `directions.<방향>.direction_instruction` | 전체 2×2 참조 → 방향별 4×1 호흡 시트 4장 | 기록상 채택된 스탠딩 버전 |
| [character-default-standing-v3.yaml](character-default-standing-v3.yaml) | `prompt` | 전체 2×2 참조 → 4×4 스탠딩 시트 | 과거 기록. YAML은 adopted이나 대응 에셋은 폐기 기록; 신규 기본값으로 사용하지 않음 |
| [character-default-rest-v2.yaml](character-default-rest-v2.yaml) | `prompt` | 전체 2×2 참조 → 휴식 2×2 시트 | 준비 완료·생성 미실행 기록 |
| [monster-standing-v2.yaml](monster-standing-v2.yaml) | `monsters.<ID>.prompt` | 종별 참조 → 4×4 스탠딩 시트 | 과거 프롬프트 통합 기록 |

몬스터 ID: `slime`, `beast`, `giant`, `field-rabbit`, `stone-crab`, `ridge-boar`, `lantern-moth`, `reed-crawler`, `ash-fox`, `crystal-lizard`.

### 공통 화풍 선택

- `common`: 넓은 색면, 부드러운 3단계 명암, 단순한 형태, 좌상단 확산광.
- `categories`: `monster`, `character`, `terrain`, `ui` 중 용도 선택.
- `outputs`: `sprite`, `portrait`, `ground_texture`, `terrain_object`, `ui_asset`, `ui_concept`. 허용 조합은 `allowed_outputs`를 따른다.
- 조합 순서는 `common → category → output → subject → negative`. 완성형 전용 프롬프트에 중복 결합하지 않는다.
- 캐릭터의 5등신은 목표 조건이다. 문구 포함만으로 실제 이미지가 충족했다고 판단하지 않는다.

## 이미지와 함께 관리하는 프롬프트

에셋별 원문은 이미지 옆에서 관리하고 여기에는 링크만 둔다. 원문을 복제하거나 실행 결과를 새로운 기준으로 자동 승격하지 않는다.

| 원본 | 용도·내용 | 상태 |
| --- | --- | --- |
| [기본 캐릭터 프롬프트](../assets/character-baselines/character-default/generation-prompts.yaml) | `base-prompt`, 대기·휴식 전환, `walking-identity-generation-prompt`, 프레임별 걷기 보조문 | 용도별 선택; base-prompt 자동 추가 금지 |
| [남성 B 참고 프롬프트](../assets/character-baselines/character-male-b/baseline-v1/prompt.txt) | 남성 B 제작 참고 원문 | 과거 원문; 최신 이미지의 실제 입력이라고 추정하지 않음 |
| [Kimodo 동작 예제](../generators/kimodo/config/prompt-examples.yaml) | 모션 생성 예제와 설정 | 생성기 소유 원본 |

### 여성 A · 8방향 실험 색인

이미지와 YAML은 [baseline-v1 폴더](../assets/character-baselines/character-female-a/baseline-v1/)에 함께 둔다. 아래 실험은 승인된 5등신 기준이 아니다.

| 프롬프트·이미지 기록 | 변경 사항 | 검수 상태 |
| --- | --- | --- |
| [v3](../assets/character-baselines/character-female-a/baseline-v1/character-female-eight-directions-fitted-v3.yaml) | v2 이미지 참조 재작화 | 비율 미검증 |
| [v4](../assets/character-baselines/character-female-a/baseline-v1/character-female-eight-directions-fitted-v4.yaml) | 이미지 참조 없이 생성 | 비율 미검증 |
| [v5](../assets/character-baselines/character-female-a/baseline-v1/character-female-eight-directions-fitted-v5.yaml) | 짧은 크롭 티셔츠·숏팬츠 | 5등신 이탈 지적 |
| [v6](../assets/character-baselines/character-female-a/baseline-v1/character-female-eight-directions-fitted-v6.yaml) | 머리·몸통·다리 비율 명시 | 정확한 5등신 미검증 |
| [v7](../assets/character-baselines/character-female-a/baseline-v1/character-female-eight-directions-fitted-v7-prompt.yaml) | 캐릭터·화풍 유지, 287→131단어 압축 | 긴 체형으로 생성 |
| [v8](../assets/character-baselines/character-female-a/baseline-v1/character-female-eight-directions-fitted-v8.yaml) | 비율 우선 배치·큰 머리·짧은 팔다리 강조 | 과보정 |
| [v9](../assets/character-baselines/character-female-a/baseline-v1/character-female-eight-directions-fitted-v9.yaml) | 과장 표현 제거 | 긴 체형 재발; 비율 검수 미달 |

## 등록·수정 규칙

1. 공통 재사용 프롬프트는 이 폴더, 생성기 예제는 해당 생성기, 이미지별 실제 생성 프롬프트는 이미지와 같은 폴더에 저장한다. 이 README에 색인을 추가한다.
2. 기본 데이터와 채택 프롬프트는 Git 추적 경로에 보관한다. `.tmp`에는 실행별 사본·로그·후보 결과를 둘 수 있지만 재사용 원본을 그곳에만 두지 않는다.
3. 이미지와 같은 버전 이름의 YAML에 `image`, `prompt`, 생성 도구, 참조 이미지 여부·역할, 상태를 기록한다. 템플릿 실행은 변수 치환 후 실제 전달한 원문·단어 수·해시를 보존한다.
4. 이미 생성에 사용한 원문은 덮어쓰지 않는다. 프롬프트 수정은 새 버전으로 저장하고 생성 전/생성 완료/검수 후보/채택/미달을 구분한다.
5. 이미지 참조 없이 생성한 경우 `reference_images: []`를 명시한다. 기존 이미지와 닮았다는 이유로 실제 입력으로 기록하지 않는다.
6. 원문 키·경로·상태가 바뀌면 이 색인을 함께 수정한다. 링크와 파일 존재를 확인하고, 삭제된 기준이나 다른 저장소 경로를 자동 대체하지 않는다.

## 실행 계약

건물은 [직교투영 베이스라인 v1](building-orthographic-v1.yaml)을 따른다. `prompt` 원문 뒤에 필수 건물 입력을 붙이고, 점유 밑면과 출입구를 표시한 실제 바닥 그리드를 투영 기준으로 제공한다. 공통 화풍의 다른 카메라 문구를 자동 결합하지 않는다. 버전·최종 입력·참조 해시를 기록하고 건물 1종의 실제 맵 검수 후 교체 범위를 확대한다. 이 기록은 제작 기준 고정이며 생성기 자동 연결이나 기존 건물 교체 완료를 뜻하지 않는다.

과거 기록은 2×2 베이스라인 생성을 전제로 한다. 이전에 연결했던 `workflows/character-baseline-sheet.md`는 현재 없으므로 실행 가이드로 안내하지 않는다. 신규 생성은 사용자가 지정한 방향 수·배치·참조 조건을 따른다. 재사용할 프롬프트 원본은 추적 경로에 보존하고, 실행별 사본은 `.tmp`에 준비한다. 사용자 지정 8방향·무참조 실험은 그 실행의 명시적 조건을 따른다. 폐기한 베이스라인 v1 프롬프트는 복원하지 않는다.

1. 선택한 YAML의 버전과 대상 ID를 확인한다. 내장 `image_gen`만 사용하며 사용자가 입력한 모델로 바꾸지 않는다.
2. 스탠딩 v4는 `prompt_template`에 선택한 방향의 `direction_instruction`을 치환하고, 과거 스탠딩 v3와 휴식은 `prompt`, 몬스터는 `monsters[대상 ID].prompt`를 실행 원문으로 사용한다. 몬스터 ID는 카탈로그의 10개 키만 허용하고 잘못된 ID에 대체 프롬프트를 적용하지 않는다.
3. 참조 파일을 준비한 뒤 존재·해시·이미지 역할을 확인한다. 몬스터의 `reference: null`은 원래 참조를 확인하지 못했다는 뜻이다. 실행 시 해당 종의 명시적인 참조를 지정하고 기록하기 전에는 생성하지 않는다. 현재 결과를 원래 입력이라고 추정하지 않는다.
4. `.tmp/YYYY-MM-DD_HH-mm-ss/`에 YAML 버전·해시, 실제 선택 원문, 참조 사본·해시, 실행 로그와 결과를 보관한다. 도구 호출 전에 참조 이미지를 확인한다.
5. 도구에는 선택 원문과 참조 이미지를 전달한다. 실행 후 실제 크기와 해시를 기록하고 사용자 승인 후 별도 에셋 전달 절차를 따른다. 다른 저장소에 직접 쓰지 않는다. 이 YAML 이동 자체는 이미지 재생성이나 런타임 변경이 아니다.

## 공통 스타일 적용 범위

공통 스타일 YAML은 기존 내용을 보존했으며 과거 5등신·배율·카메라 표현도 포함한다. 기준 시트와 휴식의 원형 보존 실험에는 공통 스타일을 자동 결합하지 않는다. 두 전용 프롬프트는 첨부 원형의 외형·렌더링 스타일을 직접 참조한다. 몬스터와 기존 스탠딩 이력의 완성된 프롬프트에도 공통 블록을 중복 결합하지 않는다. 새로운 공통 스타일 조합 실험은 별도 버전으로 검수한다.

## 휴식과 몬스터의 주의점

- 휴식 입력 기준 시트는 좌상부터 `up_left`, `up_right`, `down_left`, `down_right`다. 출력 휴식 시트는 기존 배치인 `down_right`, `down_left`, `up_right`, `up_left`를 유지한다. 입력 배치와 출력 배치를 혼동하지 않는다.
- 휴식 v2는 단일 `down_right.png` 참조를 제거했고 신체 비율·균등 배율을 추가하지 않았다. 기존 rest-v1이 새 프롬프트의 결과라고 기록하지 않는다.
- 몬스터 `beast`의 충돌은 실제 카탈로그가 사용하는 `beast-idle-v2`에 맞춰 확장판의 개과형 정의로 해결했다. 이전 멧돼지형 정의는 제외했고 나머지 9종의 프롬프트는 원문을 유지했다.
- `v1`이라는 이름만으로 모든 기록을 폐기하지 않는다. 현재 사용하는 프롬프트와 대체·폐기된 기록을 구분한다. 요청으로 폐기한 이전 단일 캐릭터·4방향 정지·걷기 프롬프트는 새 기본값으로 복원하지 않는다.

YAML 소비 코드를 추가할 때 필수·알 수 없는 필드·자료형·허용 값·중복 키를 검증하고 오류 시 즉시 실패시킨다. 제작 이력 이동은 프론트엔드 및 AWS 배포·비용에 영향을 주지 않는다.

## 비율 참고 이미지

[프롬프트 참고용 마네킨](references/mannequin/README.md)에서 남녀 신체·헤드의 4방향 시트와 생성 원문을 관리한다. 신체 비율과 얼굴 이목구비 기준을 구분하여 사용한다.

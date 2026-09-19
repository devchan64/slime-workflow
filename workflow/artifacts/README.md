# 로컬 에셋 팩 내보내기

이미 등록하고 검수한 에셋을 명시적으로 선택하여 로컬 ZIP을 만든다. 외부 업로드는 수행하지 않는다. 조회·검수·팩 생성은 Python 표준 라이브러리만 사용하며, YAML 계약 등록에는 `requirements-artifacts.txt`의 PyYAML이 필요하다.

```bash
python3 -m workflow.artifacts.pack_cli \
  --registry /work/private/registry.sqlite \
  --pack-id terrain.release --version 1 \
  --asset terrain.grass 1.0.0 \
  --asset terrain.path 2.0.0 \
  --release-root /work/private/releases \
  --log /work/private/logs/terrain-pack.log
```

`--asset ID VERSION`을 반복한다. 빈 목록·중복 ID/버전은 오류다. 목록은 ID/버전 순으로 정렬하며, 동일 입력은 동일 ZIP 바이트를 만든다. 각 항목은 최신 검수의 승인과 CC BY 4.0 수정·재배포 허용이 필요하다. 하나라도 검증에 실패하면 완성 릴리스를 만들지 않는다.

ZIP의 `manifest.json`에는 `packId`, `version`, `compatibleSchemaVersion`, `assets`가 있다. 각 에셋 항목은 기존 단일 에셋 manifest와 같은 공개 필드를 사용한다. 동일 파일 해시·확장자는 ZIP에서 한 번만 저장하지만 모든 에셋 항목과 고지는 남긴다. 제작 입력인 `sourceArtifacts`는 검증만 하며 자동 포함하지 않는다.

로그·릴리스 경로는 모든 선택 에셋의 원본 루트 밖에 둔다. 완성 릴리스 디렉터리에는 내용 해시 파일명의 ZIP과 `private-release.json`이 생긴다. **배포할 파일은 ZIP뿐이다.** 비공개 기록에는 각 에셋의 검수 ID와 메타데이터 해시가 포함된다. 팩 목록의 별도 카탈로그 등록·편집 프로젝트 수집·타입별 렌더 데이터 생성은 이 명령의 기능이 아니다.

기존 `workflow.artifacts.review_cli ... export` 명령과 `export_asset()`은 단일 에셋 manifest를 유지한다. Python 호출에서는 `export_pack(registry, pack_id, version, [(artifact_id, version), ...], release_root)`를 사용한다.

```bash
python3 -m unittest discover -s workflow/artifacts/tests -v
```


## YAML 계약 등록

산출물을 등록하기 전에 `contractRefs`가 가리키는 계약을 같은 registry에 등록한다. 계약 원본은 `.yaml`이며 다음 필드를 정확히 요구한다.

```yaml
managementId: contract.terrain.v1
schemaVersion: 1
contractId: terrain
version: '1'
artifactTypes: [TERRAIN_TILE]
description: 지형 타일의 타입 호환성을 선언하는 계약 설명자
```

```bash
python3 -m pip install -r requirements-artifacts.txt
python3 -m workflow.artifacts.contract_cli \
  --registry /work/private/registry.sqlite \
  --contract /work/private/contracts/terrain.yaml \
  --log /work/private/logs/contract.log
```

등록은 계약 내용의 스냅샷과 해시를 보존한다. 같은 ID/버전의 다른 내용과 중복 관리 ID는 거절한다. 원본 YAML 수정·삭제로 등록 계약이 바뀌지 않으며 변경은 새로운 버전·관리 ID로 등록한다. SQLite의 UPDATE/DELETE도 차단하지만 DB 관리자에 대한 보안 경계나 WORM 보관소는 아니다.

registry v3는 기존 v1/v2의 에셋·검수 기록을 보존하면서 `contracts` 테이블을 추가한다. 이전 에셋의 계약은 자동 생성하지 않는다. 참조 계약을 명시적으로 등록하기 전에는 해당 에셋 조회·검수·내보내기가 실패한다. 이전 CLI는 v3를 지원하지 않으므로 관련 도구를 함께 갱신한다. 등록 전 백업한 registry는 별도로 보존하며 v3 파일을 이전 도구에 전달하지 않는다.

이 설명자는 계약의 존재·불변 버전·허용 에셋 타입을 검사한다. description의 자연어 조건을 자동 실행하거나 이미지의 프레임·anchor·방향을 검증하지 않는다. 실제 시각/렌더 계약에 필요한 타입별 검증기는 별도다. 산출물 등록 없이 파일/sidecar만 검사하는 명령은 registry 존재를 증명하지 않는다.

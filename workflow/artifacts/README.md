# 로컬 에셋 팩 내보내기

이미 등록하고 검수한 에셋을 명시적으로 선택하여 로컬 ZIP을 만든다. 외부 업로드는 수행하지 않는다. Python 표준 라이브러리만 사용한다.

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

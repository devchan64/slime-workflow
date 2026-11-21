# 카드 갤러리 프런트엔드

`frontend/`는 Gradio 6.31.0의 공식 Gallery 템플릿에서 생성한 소스다. `shared/Gallery.svelte`의 기본 이미지 그리드와 선택 이벤트를 유지하면서 캡션을 여러 정보 행으로 표시하고 화면 폭에 따라 열을 줄인다. 원본 라이선스는 `LICENSE`에 보존한다.

운영 서버는 `tools/management/common/card_gallery_templates/`의 빌드 결과를 Gradio 커스텀 컴포넌트 경로로 제공한다. 소스 변경 후 동일 버전 Gradio에서 `gradio cc create CardGallery --template Gallery --no-install --no-configure-metadata`로 빌드용 프로젝트를 만들고 이 디렉터리의 `frontend/`와 잠금 파일을 복사한다. 프런트엔드에서 `npm ci`로 의존성을 준비한 뒤 생성 프로젝트의 `backend/`를 `PYTHONPATH`에 추가하고 `gradio cc build --no-generate-docs --python-path <프로젝트 .venv의 python>`으로 빌드한다. 생성된 `backend/gradio_cardgallery/templates/`를 운영 경로에 반영한다. `node_modules/`와 임시 프로젝트는 Git에 포함하지 않는다.

카드의 키에는 페이지 위치와 이미지 경로뿐 아니라 캡션도 포함한다. 이미지가 같아도 작업 정보가 바뀌면 카드를 다시 만들어 이미지의 접근성 설명이 이전 기록에 머물지 않도록 한다. 잠금 파일과 로컬 npm 캐시로 프런트엔드를 재빌드하여 배포 번들에 반영했다. Python 패키지 생성은 별도 `build` 모듈이 필요하며 프런트엔드 산출물 생성과는 별개다.

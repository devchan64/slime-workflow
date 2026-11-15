# 카드 갤러리 프런트엔드

`frontend/`는 Gradio 6.31.0의 공식 Gallery 템플릿에서 생성한 소스다. `shared/Gallery.svelte`의 기본 이미지 그리드와 선택 이벤트를 유지하면서 캡션을 여러 정보 행으로 표시하고 화면 폭에 따라 열을 줄인다. 원본 라이선스는 `LICENSE`에 보존한다.

운영 서버는 `tools/review/common/card_gallery_templates/`의 빌드 결과를 Gradio 커스텀 컴포넌트 경로로 제공한다. 소스 변경 후 동일 버전 Gradio에서 `gradio cc create CardGallery --template Gallery --no-install --no-configure-metadata`로 빌드용 프로젝트를 만들고 이 디렉터리의 `frontend/`와 잠금 파일을 복사한다. 프런트엔드에서 `npm ci`로 의존성을 준비한 뒤 생성 프로젝트의 `backend/`를 `PYTHONPATH`에 추가하고 `gradio cc build --no-generate-docs --python-path <프로젝트 .venv의 python>`으로 빌드한다. 생성된 `backend/gradio_cardgallery/templates/`를 운영 경로에 반영한다. `node_modules/`와 임시 프로젝트는 Git에 포함하지 않는다.

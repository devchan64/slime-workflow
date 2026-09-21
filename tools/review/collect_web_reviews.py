"""기존 웹 검수 페이지와 허용 파일을 관리도구 스냅샷에 통합한다."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import json
try:
    from .link_review_file import link_or_copy_review_file
except ImportError:
    from link_review_file import link_or_copy_review_file

REVIEW_PUBLIC_SUFFIXES = {'.html', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.json', '.js', '.css', '.mp4'}
REVIEW_COLLECTION_ROOTS = ('.tmp', '.result', 'assets')
REVIEW_FEATURE_LABELS = (('Depth', 'Depth'), ('OpenPose', 'OpenPose'), ('rig-', '리그'), ('리그', '리그'), ('overlay', '오버레이'), ('앵커', '앵커'), ('걷기', '걷기 비교'))


class ReviewTitleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside_title_element = False
        self.page_title_parts = []

    def handle_starttag(self, current_tag_name, current_attribute_pairs):
        if current_tag_name == 'title':
            self.inside_title_element = True

    def handle_endtag(self, current_tag_name):
        if current_tag_name == 'title':
            self.inside_title_element = False

    def handle_data(self, current_text_value):
        if self.inside_title_element:
            self.page_title_parts.append(current_text_value)


def collect_web_reviews(workflow_repo_root, output_review_directory, emit_review_trace):
    discovered_page_records = []
    copied_directory_lookup = {}
    for review_root_name in REVIEW_COLLECTION_ROOTS:
        source_collection_root = workflow_repo_root/review_root_name
        # .tmp/.result는 실행 폴더 단위, assets는 자산/버전 하위 페이지까지 찾는다.
        source_page_iterator = source_collection_root.rglob('*.html') if review_root_name == 'assets' else source_collection_root.glob('*/*.html')
        for source_page_path in sorted(source_page_iterator, reverse=True):
            source_directory_path = source_page_path.parent
            if source_directory_path == source_collection_root or source_page_path.is_symlink() or not source_page_path.resolve().is_relative_to(source_collection_root.resolve()):
                continue
            source_parent_paths = (source_directory_path, *source_directory_path.parents)
            if any((current_parent_path/'manager-source.json').is_file() or current_parent_path == output_review_directory for current_parent_path in source_parent_paths if current_parent_path.is_relative_to(source_collection_root)):
                continue
            if any(current_path_part.startswith('.') for current_path_part in source_page_path.relative_to(source_collection_root).parts):
                continue
            source_page_text = source_page_path.read_text()
            title_parser_value = ReviewTitleParser()
            title_parser_value.feed(source_page_text)
            page_title_text = ''.join(title_parser_value.page_title_parts).strip() or source_page_path.stem
            source_relative_path = source_page_path.relative_to(workflow_repo_root).as_posix()
            directory_identifier_text = 'web-'+hashlib.sha256(str(source_directory_path.relative_to(workflow_repo_root)).encode()).hexdigest()[:16]
            if source_directory_path not in copied_directory_lookup:
                destination_root_path = output_review_directory/directory_identifier_text
                destination_root_path.mkdir()
                copied_file_count = 0
                for source_asset_path in sorted(source_directory_path.rglob('*')):
                    relative_asset_path = source_asset_path.relative_to(source_directory_path)
                    if source_asset_path.is_symlink() or any(current_path_part.startswith('.') for current_path_part in relative_asset_path.parts):
                        continue
                    if not source_asset_path.is_file() or source_asset_path.suffix.lower() not in REVIEW_PUBLIC_SUFFIXES:
                        continue
                    if not source_asset_path.resolve().is_relative_to(source_directory_path.resolve()):
                        raise ValueError(f'검수 폴더 밖 파일: {source_asset_path}')
                    destination_asset_path = destination_root_path/relative_asset_path
                    destination_asset_path.parent.mkdir(parents=True, exist_ok=True)
                    link_or_copy_review_file(source_asset_path, destination_asset_path)
                    copied_file_count += 1
                copied_directory_lookup[source_directory_path] = directory_identifier_text
                emit_review_trace('web-copy', f'{source_directory_path.relative_to(workflow_repo_root)} files={copied_file_count}')
            # 알려진 검수 계약은 현재 공통 UI로 갱신하고 입력 좌표는 그대로 보존한다.
            if 'const reviewFrameRecords=' in source_page_text and 'const reviewSourceMetadata=' in source_page_text:
                current_template_text = (workflow_repo_root/'generators/animation/review_standing_anchors.html').read_text()
                for embedded_constant_name, template_marker_text in (('reviewFrameRecords', '__FRAME_RECORDS__'), ('reviewSourceMetadata', '__SOURCE_METADATA__')):
                    source_json_value, unused_parse_offset = json.JSONDecoder().raw_decode(source_page_text.split('const '+embedded_constant_name+'=', 1)[1].lstrip())
                    current_template_text = current_template_text.replace(template_marker_text, json.dumps(source_json_value, ensure_ascii=False).replace('<', '\\u003c'))
                shared_review_styles = (workflow_repo_root/'tools/review/review-ui.css').read_text()
                (output_review_directory/directory_identifier_text/source_page_path.name).write_text(current_template_text.replace('</style>', '</style><style>'+shared_review_styles+'</style>', 1))
            page_identifier_text = directory_identifier_text+'-'+hashlib.sha256(source_page_path.name.encode()).hexdigest()[:8]
            page_feature_labels = sorted({feature_display_label for feature_search_text, feature_display_label in REVIEW_FEATURE_LABELS if feature_search_text.casefold() in source_page_text.casefold()})
            discovered_page_records.append({'id': page_identifier_text, 'label': page_title_text+' · '+source_directory_path.name, 'path': directory_identifier_text+'/'+source_page_path.name, 'category': 'web-review', 'anchorEditor': 'id="reviewCanvas"' in source_page_text, 'description': source_relative_path+' · '+' / '.join(page_feature_labels)})
            emit_review_trace('web-page', source_relative_path)
    return discovered_page_records

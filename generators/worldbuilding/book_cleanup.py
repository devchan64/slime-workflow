"""문서 순서와 원문 증거를 보존하는 Markdown 검수본 출력."""
from collections import Counter
import hashlib
import os
from pathlib import Path
import posixpath
import re
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from markdown_it import MarkdownIt

from .bookbinding import collect_book_sources
from .documents import save_yaml_document, write_atomic_document
from .reorganization import inspect_markdown_links

MARKDOWN_DESTINATION_START = re.compile(r'\]\(\s*|^ {0,3}\[(?:\\.|[^\]\\\n])+\]:\s*', re.MULTILINE)
MARKDOWN_CODE_SPAN = re.compile(r'(`+)(?!`)([\s\S]*?)(?<!`)\1(?!`)')


def rewrite_chapter_links(current_source_text, current_link_mapping):
    """파서가 확인한 링크 목적지만 바꾸며 코드 예시는 그대로 둔다."""
    current_markdown_parser = MarkdownIt('commonmark', {'html': False}).enable('table')
    current_parsed_tokens = current_markdown_parser.parse(current_source_text)
    current_source_lines = current_source_text.splitlines(keepends=True)
    current_line_offsets = [0]
    for current_source_line in current_source_lines:
        current_line_offsets.append(current_line_offsets[-1] + len(current_source_line))
    current_protected_ranges = []
    for current_parser_token in current_parsed_tokens:
        if current_parser_token.type in {'fence', 'code_block'}:
            current_protected_ranges.append((current_line_offsets[current_parser_token.map[0]], current_line_offsets[current_parser_token.map[1]]))
    current_masked_characters = list(current_source_text)
    for current_start_offset, current_end_offset in current_protected_ranges:
        current_masked_characters[current_start_offset:current_end_offset] = ' ' * (current_end_offset-current_start_offset)
    current_search_text = ''.join(current_masked_characters)
    current_protected_ranges.extend(current_match_value.span() for current_match_value in MARKDOWN_CODE_SPAN.finditer(current_search_text))
    current_original_tokens = current_markdown_parser.parse(current_source_text)
    current_replacement_entries = []
    for current_match_value in MARKDOWN_DESTINATION_START.finditer(current_source_text):
        if any(current_start_offset <= current_match_value.start() < current_end_offset for current_start_offset, current_end_offset in current_protected_ranges):
            continue
        current_start_offset = current_match_value.end()
        current_destination_value = current_markdown_parser.helpers.parseLinkDestination(current_source_text, current_start_offset, len(current_source_text))
        if not current_destination_value.ok:
            continue
        current_normalized_link = current_markdown_parser.normalizeLink(current_destination_value.str)
        if current_normalized_link in current_link_mapping:
            current_replacement_entries.append((current_start_offset, current_destination_value.pos, '<'+current_link_mapping[current_normalized_link]+'>'))
    for current_start_offset, current_end_offset, current_replacement_text in reversed(current_replacement_entries):
        current_source_text = current_source_text[:current_start_offset]+current_replacement_text+current_source_text[current_end_offset:]
    def collect_visible_content(current_parser_tokens):
        current_content_entries = []
        for current_parser_token in current_parser_tokens:
            # inline의 원시 content에는 목적지 URL이 포함되므로 자식 토큰으로 검사한다.
            current_content_entries.append((current_parser_token.type, current_parser_token.tag, current_parser_token.content if not current_parser_token.children else '', current_parser_token.info))
            if current_parser_token.children:
                current_content_entries.extend(collect_visible_content(current_parser_token.children))
        return current_content_entries
    if collect_visible_content(current_original_tokens)!=collect_visible_content(current_markdown_parser.parse(current_source_text)):
        raise ValueError('링크 정리 중 본문 또는 코드 예시가 변경되었습니다.')
    return current_source_text


def format_chapter_markdown(current_source_path, current_source_text):
    current_markdown_parser = MarkdownIt('commonmark', {'html': False}).enable('table')
    if not current_source_path.endswith('.md'):
        current_chapter_title = Path(current_source_path).stem
        current_fence_marker = '`' * max(3, 1+max((len(current_match_value.group()) for current_match_value in re.finditer(r'`+', current_source_text)), default=0))
        return current_chapter_title, '# '+current_chapter_title+'\n\n'+current_fence_marker+'yaml\n'+current_source_text+('' if current_source_text.endswith('\n') else '\n')+current_fence_marker+'\n', 0
    current_source_tokens = current_markdown_parser.parse(current_source_text)
    current_heading_tokens = [(current_parser_token, current_source_tokens[current_token_index+1].content) for current_token_index, current_parser_token in enumerate(current_source_tokens) if current_parser_token.type=='heading_open' and current_parser_token.level==0 and current_parser_token.tag=='h1']
    current_chapter_title = current_heading_tokens[0][1] if current_heading_tokens else Path(current_source_path).stem
    current_source_lines = current_source_text.splitlines(keepends=True)
    current_keep_first = bool(current_heading_tokens) and not ''.join(current_source_lines[:current_heading_tokens[0][0].map[0]]).strip()
    for current_heading_number, (current_heading_token, current_heading_title) in reversed(list(enumerate(current_heading_tokens))):
        if current_heading_number==0 and current_keep_first:
            continue
        current_start_line, current_end_line = current_heading_token.map
        # ATX와 Setext 제목 모두 본문 위치를 유지하며 하위 제목으로 만든다.
        if current_source_lines[current_start_line].lstrip().startswith('#'):
            current_source_lines[current_start_line] = re.sub(r'^( {0,3})#', r'\1##', current_source_lines[current_start_line], count=1)
        else:
            current_source_lines[current_end_line-1] = re.sub(r'=+', '---', current_source_lines[current_end_line-1])
    current_chapter_text = ''.join(current_source_lines)
    if not current_keep_first:
        current_chapter_text = '# '+current_chapter_title+'\n\n'+current_chapter_text
    current_paragraph_count = sum(current_parser_token.type=='paragraph_open' for current_parser_token in current_source_tokens)
    return current_chapter_title, current_chapter_text, current_paragraph_count


def export_cleaned_book(current_config_values, current_run_root, current_request_values, current_plan_values, current_source_entries):
    current_paragraph_entries = current_plan_values['paragraph_entries']
    current_identifier_counts = Counter(current_paragraph_entry['paragraph_id'] for current_paragraph_entry in current_paragraph_entries)
    if any(current_identifier_count != 1 for current_identifier_count in current_identifier_counts.values()):
        raise ValueError('문서 정리 검수에서 문단 ID 중복을 발견했습니다.')
    current_grouped_paragraphs = {current_source_path: [] for current_source_path in current_source_entries}
    for current_paragraph_entry in current_paragraph_entries:
        if current_paragraph_entry['source_document_path'] not in current_grouped_paragraphs:
            raise ValueError('문서 정리 검수에서 원본 경로 불일치를 발견했습니다.')
        current_grouped_paragraphs[current_paragraph_entry['source_document_path']].append(current_paragraph_entry)
    for current_source_path, current_source_blocks in current_grouped_paragraphs.items():
        current_source_blocks.sort(key=lambda current_paragraph_entry: current_paragraph_entry['source_start_line'])
        if not current_source_blocks or ''.join(current_source_block['paragraph_text'] for current_source_block in current_source_blocks)!=current_source_entries[current_source_path]['source_document_body']:
            raise ValueError('원문 문단 누락 또는 내용 변경: '+current_source_path)
        for current_source_block in current_source_blocks:
            if current_source_block['source_content_hash']!=current_source_entries[current_source_path]['source_content_hash'] or current_source_block['paragraph_hash']!=hashlib.sha256(current_source_block['paragraph_text'].encode()).hexdigest():
                raise ValueError('원문 문단 해시 불일치: '+current_source_path)
    current_completed_root = current_run_root/'completed-book'
    if current_completed_root.exists():
        raise ValueError('기존 도서 결과를 덮어쓸 수 없습니다.')
    current_ordered_paths = sorted(current_source_entries, key=lambda current_source_path: (not current_source_path.endswith('.md'), Path(current_source_path).name!='README.md', current_source_path))
    current_topic_directories = {}
    current_chapter_paths = {}
    for current_source_path in current_ordered_paths:
        current_topic_title = current_grouped_paragraphs[current_source_path][0]['chapter_title']
        if current_topic_title not in current_topic_directories:
            current_topic_number = len(current_topic_directories)+1
            current_topic_slug = re.sub(r'[^0-9A-Za-z가-힣]+','-',current_topic_title).strip('-').lower() or 'uncategorized'
            current_topic_directories[current_topic_title] = f'{current_topic_number:02d}-{current_topic_slug}'
        current_file_stem = re.sub(r'[^0-9A-Za-z가-힣]+','-',Path(current_source_path).stem).strip('-').lower() or 'document'
        current_output_path = f'chapters/{current_topic_directories[current_topic_title]}/{current_file_stem}.md'
        if current_output_path in current_chapter_paths.values():
            current_path_digest = hashlib.sha256(current_source_path.encode()).hexdigest()[:12]
            current_output_path = f'chapters/{current_topic_directories[current_topic_title]}/{current_file_stem}-{current_path_digest}.md'
        if current_output_path in current_chapter_paths.values():
            raise ValueError('도서 파일 경로가 중복됩니다: '+current_source_path)
        current_chapter_paths[current_source_path] = current_output_path
    current_source_anchors = {current_source_path: inspect_markdown_links(current_source_path, current_source_entry['source_document_body'])[1] for current_source_path, current_source_entry in current_source_entries.items() if current_source_path.endswith('.md')}
    current_chapter_entries = []
    current_warning_entries = []
    current_internal_count = 0
    current_external_count = 0
    current_broken_count = 0
    current_chapter_outputs = {}
    for current_source_path in current_ordered_paths:
        current_source_text = current_source_entries[current_source_path]['source_document_body']
        current_chapter_title, current_chapter_text, current_paragraph_count = format_chapter_markdown(current_source_path, current_source_text)
        current_link_mapping = {}
        current_expected_links = []
        if current_source_path.endswith('.md'):
            current_markdown_parser = MarkdownIt('commonmark', {'html': False}).enable('table')
            for current_parser_token in current_markdown_parser.parse(current_source_text):
                for current_child_token in current_parser_token.children or []:
                    if current_child_token.type not in {'link_open', 'image'}:
                        continue
                    current_link_text = current_child_token.attrGet('href' if current_child_token.type=='link_open' else 'src') or ''
                    current_parsed_url = urlsplit(current_link_text)
                    if current_parsed_url.scheme or current_parsed_url.netloc:
                        continue
                    current_target_path = posixpath.normpath(posixpath.join(posixpath.dirname(current_source_path), unquote(current_parsed_url.path))) if current_parsed_url.path else current_source_path
                    if current_target_path in current_chapter_paths:
                        current_output_target = posixpath.relpath(current_chapter_paths[current_target_path], posixpath.dirname(current_chapter_paths[current_source_path]))
                        current_internal_count += 1
                        if current_parsed_url.fragment and unquote(current_parsed_url.fragment) not in current_source_anchors.get(current_target_path, set()):
                            current_broken_count += 1
                            current_warning_entries.append('WARN 원본에 없는 절: '+current_source_path+' → '+current_link_text)
                    else:
                        current_target_file = Path(current_config_values['source_document_root'])/current_target_path
                        current_output_target = os.path.relpath(current_target_file, (current_completed_root/current_chapter_paths[current_source_path]).parent)
                        current_external_count += 1
                        current_warning_entries.append('WARN 도서 밖 원본 참조(원본 작업 공간 필요): '+current_source_path+' → '+current_link_text)
                        if not current_target_file.is_file():
                            current_broken_count += 1
                            current_warning_entries.append('WARN 원본 참조 파일 없음: '+current_source_path+' → '+current_link_text)
                    current_rewritten_link = urlunsplit(('', '', quote(current_output_target, safe='/.-_'), current_parsed_url.query, current_parsed_url.fragment))
                    current_link_mapping[current_link_text] = current_rewritten_link
                    current_expected_links.append(current_rewritten_link)
            current_chapter_text = rewrite_chapter_links(current_chapter_text, current_link_mapping)
            current_actual_links = []
            for current_parser_token in current_markdown_parser.parse(current_chapter_text):
                for current_child_token in current_parser_token.children or []:
                    if current_child_token.type in {'link_open', 'image'}:
                        current_link_text = current_child_token.attrGet('href' if current_child_token.type=='link_open' else 'src') or ''
                        if not urlsplit(current_link_text).scheme and not urlsplit(current_link_text).netloc:
                            current_actual_links.append(current_link_text)
            if Counter(current_actual_links)!=Counter(current_expected_links):
                raise ValueError('Markdown 링크 재연결 검증 실패: '+current_source_path)
        current_chapter_outputs[current_chapter_paths[current_source_path]] = current_chapter_text
        current_chapter_entries.append({'chapter_number': len(current_chapter_entries)+1, 'chapter_title': current_chapter_title, 'file_path': current_chapter_paths[current_source_path], 'paragraph_count': current_paragraph_count, 'block_count': len(current_grouped_paragraphs[current_source_path]), 'source_document_paths': [current_source_path], 'source_format': Path(current_source_path).suffix.lstrip('.')})
    current_source_hashes = {current_source_path: current_source_entry['source_content_hash'] for current_source_path, current_source_entry in current_source_entries.items()}
    current_latest_sources = collect_book_sources(current_config_values, current_request_values['source_directory_paths'])
    if current_source_hashes!={current_source_path: current_source_entry['source_content_hash'] for current_source_path, current_source_entry in current_latest_sources.items()}:
        raise ValueError('도서 편집 중 원문이 변경되었습니다.')
    current_cleanup_values = {'source_document_count': len(current_source_entries), 'paragraph_count': sum(current_chapter_entry['paragraph_count'] for current_chapter_entry in current_chapter_entries), 'block_count': len(current_paragraph_entries), 'yaml_document_count': sum(not current_source_path.endswith('.md') for current_source_path in current_source_entries), 'duplicate_paragraph_count': 0, 'invalid_source_paths': [], 'source_hashes': current_source_hashes, 'original_change_required_flag': False, 'internal_link_count': current_internal_count, 'outside_reference_count': current_external_count, 'broken_reference_count': current_broken_count, 'quality_warnings': list(dict.fromkeys(current_warning_entries))}
    current_completed_root.mkdir(parents=True, exist_ok=False)
    for current_output_path, current_output_text in current_chapter_outputs.items():
        write_atomic_document(current_completed_root/current_output_path, current_output_text)
    save_yaml_document(current_completed_root/'paragraphs.yaml', {'paragraph_entries': [current_source_block for current_source_path in current_ordered_paths for current_source_block in current_grouped_paragraphs[current_source_path]]})
    save_yaml_document(current_completed_root/'manifest.yaml', {'book_schema_version': 2, 'collection_id': current_request_values['collection_id'], 'chapter_entries': current_chapter_entries, 'source_hashes': current_source_hashes, 'quality_checks': current_cleanup_values})
    current_readme_text = '# '+current_request_values['book_title_text']+'\n\n원문 순서를 보존한 검수본입니다. 제목 단계·링크·YAML 표시만 정리했으며 원본은 변경하지 않았습니다.\n\n'
    for current_chapter_entry in current_chapter_entries:
        current_count_label = 'YAML 자료' if current_chapter_entry['source_format']!='md' else str(current_chapter_entry['paragraph_count'])+'개 본문 문단'
        current_readme_text += f"- [{current_chapter_entry['chapter_title']}]({current_chapter_entry['file_path']}) · {current_count_label}\n"
    current_readme_text += '\n본문 문단 수와 원문 블록 수(제목·표·목록·코드 포함)는 별도로 집계합니다. YAML 자료는 본문 문단 수에 포함하지 않습니다.\n'
    if current_warning_entries:
        current_readme_text += '\n## 참조 검수\n\n도서 밖 링크는 기존 원본 작업 공간을 참조합니다. 판본만 옮기면 해당 링크는 사용할 수 없습니다. 세부 경고는 manifest.yaml에 기록했습니다.\n'
    write_atomic_document(current_completed_root/'README.md', current_readme_text)
    save_yaml_document(current_run_root/'book-result.yaml', {'collection_id': current_request_values['collection_id'], 'book_edit_stage_name': 'document-cleanup', 'cleanup_values': current_cleanup_values, 'completed_book_directory': str(current_completed_root)})
    return current_cleanup_values

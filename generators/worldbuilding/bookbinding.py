"""비공개 문서를 원문과 출처를 보존하는 검색 가능한 웹 도서로 편집한다."""
from datetime import datetime
from html import escape
import hashlib
from pathlib import Path, PurePosixPath
import posixpath
import re
import threading
import traceback
from urllib.parse import unquote, urlsplit
import uuid
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator
from .documents import (scan_source_documents, save_yaml_document, load_yaml_document,
    lock_document_workspace, resolve_document_path)

BOOK_REQUEST_SCHEMA={'type':'object','additionalProperties':False,'required':['book_title_text','source_directory_paths'],'properties':{'book_title_text':{'type':'string','minLength':1,'maxLength':120,'pattern':r'\S'},'source_directory_paths':{'type':'array','minItems':1,'maxItems':50,'uniqueItems':True,'items':{'type':'string','minLength':1,'maxLength':300}}}}
BOOK_PLACEMENT_SCHEMA={'type':'object','additionalProperties':False,'required':['paragraph_id','chapter_title'],'properties':{'paragraph_id':{'type':'string','minLength':1},'chapter_title':{'type':'string','minLength':1,'maxLength':160,'pattern':r'\S'}}}
BOOK_PLACEMENT_SCHEMA['properties']['index_terms']={'type':'array','maxItems':5,'uniqueItems':True,'items':{'type':'string','minLength':2,'maxLength':40}}
BOOK_REQUEST_SCHEMA['properties']['paragraph_placements']={'type':'array','minItems':1,'maxItems':15000,'items':BOOK_PLACEMENT_SCHEMA}
BOOK_REQUEST_SCHEMA['properties']['collection_id']={'enum':['world','system-design']}
BOOK_IDENTIFIER_PATTERN=r'[0-9]{8}-[0-9]{6}-[a-f0-9]{8}'
BOOK_INDEX_STOP_WORDS={'있다','없다','한다','하는','하지','위한','따라','통해','대한','에서','으로','또는','그리고','다만','아직','이후','현재','기존','신규','제안','상태','문서','설정','범위','추가','사용','경우','같은','아래','확인','포함','제외','반영','별도','기준'}
BOOK_TOTAL_BYTES_LIMIT=20_000_000
BOOK_SOURCE_COUNT_LIMIT=2000
BOOK_TOPIC_KEYWORDS={'세계와 장소':('세계','지역','도시','마을','지형','환경','기후','world','city'),'인물과 조직':('인물','주민','조직','길드','직책','관계','character','npc'),'생활과 경제':('경제','시장','거래','점포','브랜드','상품','상점','생활','식사','shop','economy'),'규칙과 시스템':('전투','성장','스킬','장비','보상','제작','규칙','시스템','플레이','combat','system'),'이야기와 역사':('역사','이야기','사건','연대','스토리','퀘스트','history','story'),'기준과 승인':('승인','확정','관리','정책','작업','기준','approval','management')}
BOOK_TEMPLATE_PATH=Path(__file__).with_name('book-reader.html')


def scan_book_documents(current_config_values):
    current_source_entries=scan_source_documents(current_config_values)
    for current_source_path,current_source_entry in current_source_entries.items():
        current_source_bytes=resolve_document_path(Path(current_config_values['source_document_root']),current_source_path).read_bytes()
        current_source_entry['source_document_body']=current_source_bytes.decode('utf-8')
        current_source_entry['source_content_hash']=hashlib.sha256(current_source_bytes).hexdigest()
    return current_source_entries


def collect_book_sources(current_config_values,current_directory_paths):
    current_source_root=Path(current_config_values['source_document_root'])
    current_private_root=Path(current_config_values['private_state_root'])
    for current_directory_path in current_directory_paths:
        current_resolved_path=current_source_root if current_directory_path=='.' else resolve_document_path(current_source_root,current_directory_path)
        if not current_resolved_path.is_dir() or current_resolved_path.resolve().is_relative_to(current_private_root) or any(current_path_part.startswith('.') for current_path_part in Path(current_directory_path).parts):
            raise ValueError('선택할 수 없는 문서 폴더: '+current_directory_path)
    current_source_entries=scan_book_documents(current_config_values)
    selected_source_entries={current_source_path:current_source_entry for current_source_path,current_source_entry in current_source_entries.items() if any(current_directory_path=='.' or current_source_path.startswith(current_directory_path.rstrip('/')+'/') for current_directory_path in current_directory_paths)}
    if not selected_source_entries:
        raise ValueError('선택한 폴더에 Markdown 또는 YAML 문서가 없습니다.')
    if len(selected_source_entries)>BOOK_SOURCE_COUNT_LIMIT or sum(len(current_source_entry['source_document_body'].encode()) for current_source_entry in selected_source_entries.values())>BOOK_TOTAL_BYTES_LIMIT:
        raise ValueError('도서 크기 제한 초과: 폴더를 나누어 선택하세요.')
    return selected_source_entries


def plan_document_book(current_config_values,current_request_values):
    """문서 단위로 주제를 정하고 내부 블록의 원문 순서를 보존한다."""
    from markdown_it import MarkdownIt
    Draft202012Validator(BOOK_REQUEST_SCHEMA).validate(current_request_values)
    if 'collection_id' in current_request_values:
        from .book_collections import resolve_collection_request
        resolve_collection_request(current_config_values,current_request_values)
    current_source_entries=collect_book_sources(current_config_values,current_request_values['source_directory_paths'])
    current_paragraph_entries=[]
    current_markdown_parser=MarkdownIt('commonmark',{'html':False}).enable('table')
    for current_source_path,current_source_entry in current_source_entries.items():
        current_source_text=current_source_entry['source_document_body']
        current_source_lines=current_source_text.splitlines(keepends=True)
        current_parsed_tokens=current_markdown_parser.parse(current_source_text) if current_source_path.endswith('.md') else []
        current_block_starts={0}
        current_heading_lookup={}
        for current_token_index,current_parser_token in enumerate(current_parsed_tokens):
            if current_parser_token.level==0 and current_parser_token.map:
                current_block_starts.add(current_parser_token.map[0])
            if current_parser_token.type=='heading_open':
                current_heading_lookup[current_parser_token.map[0]]=(int(current_parser_token.tag[1:]),current_parsed_tokens[current_token_index+1].content)
        current_document_title=next((current_heading_title for current_heading_level,current_heading_title in current_heading_lookup.values() if current_heading_level==1),PurePosixPath(current_source_path).stem)
        current_topic_context=(current_document_title+' '+PurePosixPath(current_source_path).stem).lower()
        current_topic_scores={current_topic_label:sum(current_topic_context.count(current_topic_keyword) for current_topic_keyword in current_topic_keywords) for current_topic_label,current_topic_keywords in BOOK_TOPIC_KEYWORDS.items()}
        current_topic_title=max(current_topic_scores,key=current_topic_scores.get) if max(current_topic_scores.values()) else '기타 설정'
        current_block_starts=sorted(current_block_starts)
        current_heading_trail={}
        for current_block_index,current_start_line in enumerate(current_block_starts):
            current_end_line=current_block_starts[current_block_index+1] if current_block_index+1<len(current_block_starts) else len(current_source_lines)
            if current_start_line in current_heading_lookup:
                current_heading_level,current_heading_title=current_heading_lookup[current_start_line]
                current_heading_trail={current_trail_level:current_trail_title for current_trail_level,current_trail_title in current_heading_trail.items() if current_trail_level<current_heading_level}
                current_heading_trail[current_heading_level]=current_heading_title
            current_paragraph_text=''.join(current_source_lines[current_start_line:current_end_line])
            current_paragraph_id='paragraph-'+hashlib.sha256((current_source_path+':'+current_source_entry['source_content_hash']+':'+str(current_start_line)).encode()).hexdigest()[:24]
            current_paragraph_entries.append({'paragraph_id':current_paragraph_id,'source_document_path':current_source_path,'source_content_hash':current_source_entry['source_content_hash'],'source_start_line':current_start_line+1,'source_end_line':current_end_line,'paragraph_text':current_paragraph_text,'paragraph_hash':hashlib.sha256(current_paragraph_text.encode()).hexdigest(),'heading_trail':list(current_heading_trail.values()),'is_heading_flag':current_start_line in current_heading_lookup,'chapter_title':current_topic_title})
    current_chapter_order=list(dict.fromkeys(current_paragraph_entry['chapter_title'] for current_paragraph_entry in current_paragraph_entries))
    current_paragraph_entries.sort(key=lambda current_paragraph_entry:current_chapter_order.index(current_paragraph_entry['chapter_title']))
    return {'paragraph_entries':current_paragraph_entries,'source_count':len(current_source_entries),'paragraph_placements':[{'paragraph_id':current_paragraph_entry['paragraph_id'],'chapter_title':current_paragraph_entry['chapter_title']} for current_paragraph_entry in current_paragraph_entries]}


def validate_book_placements(current_plan_values,current_request_values):
    current_paragraph_lookup={current_paragraph_entry['paragraph_id']:current_paragraph_entry for current_paragraph_entry in current_plan_values['paragraph_entries']}
    current_placement_entries=current_request_values.get('paragraph_placements',current_plan_values['paragraph_placements'])
    current_placement_ids=[current_placement_entry['paragraph_id'] for current_placement_entry in current_placement_entries]
    if len(current_placement_ids)!=len(set(current_placement_ids)) or set(current_placement_ids)!=set(current_paragraph_lookup):
        raise ValueError('문단 누락·중복 또는 원문 변경이 발견되었습니다. 배치안을 다시 불러오세요.')
    for current_placement_entry in current_placement_entries:
        if any(current_index_term not in current_paragraph_lookup[current_placement_entry['paragraph_id']]['paragraph_text'] for current_index_term in current_placement_entry.get('index_terms',[])):
            raise ValueError('색인어는 해당 문단 원문에 있어야 합니다.')
    return [{**current_paragraph_lookup[current_placement_entry['paragraph_id']],**current_placement_entry,'chapter_title':current_placement_entry['chapter_title'].strip()} for current_placement_entry in current_placement_entries]


def normalize_heading_anchor(current_heading_text):
    return re.sub(r'[^\w\- ]','',current_heading_text.lower()).replace(' ','-')


def build_document_book(current_config_values,current_request_values):
    Draft202012Validator(BOOK_REQUEST_SCHEMA).validate(current_request_values)
    current_book_id=datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y%m%d-%H%M%S-')+uuid.uuid4().hex[:8]
    current_books_root=Path(current_config_values['private_state_root'])/'books'
    current_books_root.mkdir(exist_ok=True)
    current_book_root=current_books_root/current_book_id
    current_book_root.mkdir(mode=0o700)
    current_log_lock=threading.Lock()
    current_stop_event=threading.Event()
    def record_book_trace(current_stage_name,current_message_text):
        current_log_line=f'{datetime.now(ZoneInfo("Asia/Seoul")).isoformat()}/bookbinding/{current_stage_name} {current_message_text}'
        with current_log_lock, (current_book_root/'execution.log').open('a') as current_log_stream:
            current_log_stream.write(current_log_line+'\n')
        print(current_log_line,flush=True)
    def emit_book_heartbeat():
        while not current_stop_event.wait(4):
            record_book_trace('heartbeat','원문 수집·도서 편집 진행 중')
    current_heartbeat_thread=threading.Thread(target=emit_book_heartbeat,daemon=True)
    current_heartbeat_thread.start()
    try:
        with lock_document_workspace(Path(current_config_values['private_state_root'])):
            record_book_trace('start','선택 폴더: '+', '.join(current_request_values['source_directory_paths']))
            current_source_entries=collect_book_sources(current_config_values,current_request_values['source_directory_paths'])
            current_plan_values=plan_document_book(current_config_values,current_request_values)
            current_paragraph_entries=validate_book_placements(current_plan_values,current_request_values)
            # 렌더링 결과가 아닌 보존한 원문을 순서대로 복원하여 동일성을 확인한다.
            for current_source_path,current_source_entry in current_source_entries.items():
                ordered_source_paragraphs=sorted((current_paragraph_entry for current_paragraph_entry in current_paragraph_entries if current_paragraph_entry['source_document_path']==current_source_path),key=lambda current_paragraph_entry:current_paragraph_entry['source_start_line'])
                if ''.join(current_paragraph_entry['paragraph_text'] for current_paragraph_entry in ordered_source_paragraphs)!=current_source_entry['source_document_body']:
                    raise ValueError('원문 문단 무결성 검증 실패: '+current_source_path)
            from markdown_it import MarkdownIt
            current_markdown_parser=MarkdownIt('commonmark',{'html':False}).enable('table')
            current_book_title=current_request_values['book_title_text'].strip()
            current_timestamp_text=datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
            current_body_parts=[]
            current_toc_parts=[]
            current_warning_entries=[]
            current_markdown_parts=['# '+current_book_title,'원문을 보존한 편집본 · '+current_timestamp_text]
            current_chapter_titles=list(dict.fromkeys(current_paragraph_entry['chapter_title'] for current_paragraph_entry in current_paragraph_entries))
            current_reference_environments={}
            for current_source_path,current_source_entry in current_source_entries.items():
                current_reference_environments[current_source_path]={}
                current_markdown_parser.parse(current_source_entry['source_document_body'],current_reference_environments[current_source_path])
            current_source_anchors={current_source_path:next(current_paragraph_entry['paragraph_id'] for current_paragraph_entry in current_paragraph_entries if current_paragraph_entry['source_document_path']==current_source_path) for current_source_path in current_source_entries}
            current_heading_anchors={}
            current_heading_counts={}
            for current_paragraph_entry in sorted(current_paragraph_entries,key=lambda current_paragraph_entry:(current_paragraph_entry['source_document_path'],current_paragraph_entry['source_start_line'])):
                current_paragraph_tokens=current_markdown_parser.parse(current_paragraph_entry['paragraph_text']) if current_paragraph_entry['source_document_path'].endswith('.md') else []
                for current_token_index,current_parser_token in enumerate(current_paragraph_tokens):
                    if current_parser_token.type=='heading_open':
                        current_heading_slug=normalize_heading_anchor(current_paragraph_tokens[current_token_index+1].content)
                        current_heading_key=(current_paragraph_entry['source_document_path'],current_heading_slug)
                        current_heading_count=current_heading_counts.get(current_heading_key,0)
                        current_heading_counts[current_heading_key]=current_heading_count+1
                        current_heading_slug+=('-'+str(current_heading_count)) if current_heading_count else ''
                        current_heading_anchors[(current_paragraph_entry['source_document_path'],current_heading_slug)]=current_paragraph_entry['paragraph_id']
            current_term_lookup={}
            for current_chapter_number,current_chapter_title in enumerate(current_chapter_titles,1):
                current_chapter_id='chapter-'+str(current_chapter_number)
                current_section_links=''.join('<li><a href="#'+current_paragraph_entry['paragraph_id']+'">'+escape(current_paragraph_entry['heading_trail'][-1])+'</a></li>' for current_paragraph_entry in current_paragraph_entries if current_paragraph_entry['chapter_title']==current_chapter_title and current_paragraph_entry['is_heading_flag'])
                current_toc_parts.append('<li><a href="#'+current_chapter_id+'">'+str(current_chapter_number)+'. '+escape(current_chapter_title)+'</a><details><summary>절 목차</summary><ul>'+current_section_links+'</ul></details></li>')
                current_body_parts.append('<article id="'+current_chapter_id+'"><header><p class="eyebrow">'+str(current_chapter_number)+'장</p><h2>'+escape(current_chapter_title)+'</h2></header>')
                current_markdown_parts.extend(['\n---\n','## '+str(current_chapter_number)+'. '+current_chapter_title])
                for current_paragraph_entry in current_paragraph_entries:
                    if current_paragraph_entry['chapter_title']!=current_chapter_title:
                        continue
                    current_source_path=current_paragraph_entry['source_document_path']
                    current_source_text=current_paragraph_entry['paragraph_text']
                    current_paragraph_tokens=current_markdown_parser.parse(current_source_text,current_reference_environments[current_source_path]) if current_source_path.endswith('.md') else []
                    for current_parser_token in current_paragraph_tokens:
                        for current_child_token in current_parser_token.children or []:
                            if current_child_token.type=='image':
                                current_child_token.type='text'
                                current_child_token.content='[이미지: '+current_child_token.content+']'
                                current_child_token.children=None
                                current_warning_entries.append(current_source_path+': 이미지 원본은 원문에서 확인')
                            if current_child_token.type!='link_open':
                                continue
                            current_link_target=current_child_token.attrGet('href') or ''
                            current_parsed_url=urlsplit(current_link_target)
                            if current_parsed_url.scheme in {'https','http'}:
                                current_child_token.attrSet('rel','noreferrer noopener')
                                continue
                            current_target_path=posixpath.normpath(posixpath.join(str(PurePosixPath(current_source_path).parent),unquote(current_parsed_url.path))) if current_parsed_url.path else current_source_path
                            current_target_anchor=current_heading_anchors.get((current_target_path,unquote(current_parsed_url.fragment))) if current_parsed_url.fragment else current_source_anchors.get(current_target_path)
                            if current_target_anchor and not current_parsed_url.scheme and not current_parsed_url.netloc and not current_parsed_url.query:
                                current_child_token.attrSet('href','#'+current_target_anchor)
                            else:
                                current_child_token.attrs.pop('href',None)
                                current_child_token.attrSet('title','도서 밖 참조: '+current_link_target)
                                current_warning_entries.append(current_source_path+': 도서 밖 참조 '+current_link_target)
                    current_body_html=current_markdown_parser.renderer.render(current_paragraph_tokens,current_markdown_parser.options,current_reference_environments[current_source_path]) if current_source_path.endswith('.md') else '<pre><code>'+escape(current_source_text)+'</code></pre>'
                    current_source_label=current_source_path+':'+str(current_paragraph_entry['source_start_line'])+'-'+str(current_paragraph_entry['source_end_line'])
                    current_body_parts.append('<section class="paragraph" id="'+current_paragraph_entry['paragraph_id']+'"><p class="source">'+escape(current_source_label)+' · '+escape(' › '.join(current_paragraph_entry['heading_trail']))+'</p><div class="prose">'+current_body_html+'</div><details><summary>보존 원문 · 출처</summary><p>'+escape(current_paragraph_entry['paragraph_hash'])+'</p><pre>'+escape(current_source_text)+'</pre></details></section>')
                    current_markdown_parts.extend(['<!-- 출처: '+current_source_label+' -->',current_source_text])
                    for current_term_text in set(current_paragraph_entry['index_terms'] if 'index_terms' in current_paragraph_entry else re.findall(r'[가-힣A-Za-z][가-힣A-Za-z0-9_-]{1,30}',current_source_text)):
                        if current_term_text not in BOOK_INDEX_STOP_WORDS:
                            current_term_lookup.setdefault(current_term_text,[]).append(current_paragraph_entry['paragraph_id'])
                    record_book_trace('paragraph',current_source_label)
                current_body_parts.append('</article>')
            current_index_parts=[]
            for current_term_text in sorted(current_term_lookup,key=lambda current_term_text:(-len(current_term_lookup[current_term_text]),current_term_text))[:300]:
                current_index_parts.append('<details><summary>'+escape(current_term_text)+' · '+str(len(current_term_lookup[current_term_text]))+'</summary>'+''.join('<a href="#'+current_paragraph_id+'">'+str(current_index_number)+' </a>' for current_index_number,current_paragraph_id in enumerate(current_term_lookup[current_term_text],1))+'</details>')
            current_warning_entries=list(dict.fromkeys(current_warning_entries))
            current_manifest_values={'book_schema_version':1,'book_id':current_book_id,'book_title_text':current_book_title,'created_timestamp_text':current_timestamp_text,'source_directory_paths':current_request_values['source_directory_paths'],'source_hash_mapping':{current_source_path:current_source_entry['source_content_hash'] for current_source_path,current_source_entry in current_source_entries.items()},'chapter_count':len(current_chapter_titles),'paragraph_count':len(current_paragraph_entries),'quality_warnings':current_warning_entries,'paragraph_placements':[{'paragraph_id':current_paragraph_entry['paragraph_id'],'chapter_title':current_paragraph_entry['chapter_title']} for current_paragraph_entry in current_paragraph_entries]}
            if 'collection_id' in current_request_values:
                current_manifest_values['collection_id']=current_request_values['collection_id']
            save_yaml_document(current_book_root/'paragraphs.yaml',{'paragraph_entries':current_paragraph_entries})
            current_template_text=BOOK_TEMPLATE_PATH.read_text()
            current_replacements={'@@TITLE@@':escape(current_book_title),'@@TIME@@':escape(current_timestamp_text),'@@COUNT@@':str(len(current_chapter_titles)),'@@INDEX@@':''.join(current_index_parts),'@@TOC@@':''.join(current_toc_parts),'@@BODY@@':''.join(current_body_parts),'@@WARNINGS@@':escape('\n'.join(current_warning_entries) or '포함된 문서의 링크를 연결했습니다.')}
            current_rendered_text=re.sub(r'@@[A-Z]+@@',lambda current_match_value:current_replacements[current_match_value.group()],current_template_text)
            latest_source_entries=collect_book_sources(current_config_values,current_request_values['source_directory_paths'])
            if {current_source_path:current_source_entry['source_content_hash'] for current_source_path,current_source_entry in latest_source_entries.items()}!=current_manifest_values['source_hash_mapping']:
                raise ValueError('도서 편집 중 원문이 변경되었습니다. 다시 생성하세요.')
            (current_book_root/'book.html').write_text(current_rendered_text)
            (current_book_root/'book.md').write_text('\n\n'.join(current_markdown_parts)+'\n')
            save_yaml_document(current_book_root/'manifest.yaml',current_manifest_values)
            record_book_trace('complete',f'문서 {len(current_source_entries)}개 · 문단 {len(current_paragraph_entries)}개 · 참조 안내 {len(current_warning_entries)}개')
            return current_manifest_values
    except Exception:
        record_book_trace('failure',traceback.format_exc())
        print('\n'.join((current_book_root/'execution.log').read_text().splitlines()[-20:]),flush=True)
        raise
    finally:
        current_stop_event.set()
        current_heartbeat_thread.join(timeout=1)


def list_document_books(current_config_values):
    current_source_entries=scan_book_documents(current_config_values)
    current_directory_paths={'.'}
    for current_source_path in current_source_entries:
        current_directory_paths.update(str(current_parent_path) for current_parent_path in PurePosixPath(current_source_path).parents)
    current_book_entries=[]
    for current_manifest_path in sorted((Path(current_config_values['private_state_root'])/'books').glob('*/manifest.yaml'),reverse=True)[:50]:
        current_manifest_values=load_yaml_document(current_manifest_path)
        selected_source_hashes={current_source_path:current_source_entry['source_content_hash'] for current_source_path,current_source_entry in current_source_entries.items() if any(current_directory_path=='.' or current_source_path.startswith(current_directory_path.rstrip('/')+'/') for current_directory_path in current_manifest_values['source_directory_paths'])}
        current_manifest_values['source_changed_flag']=selected_source_hashes!=current_manifest_values['source_hash_mapping']
        del current_manifest_values['source_hash_mapping']
        current_book_entries.append(current_manifest_values)
    from .book_collections import load_document_collections, DEFAULT_COLLECTION_ROOTS
    current_collection_entries=load_document_collections(current_config_values)
    for current_book_entry in current_book_entries:
        if 'collection_id' not in current_book_entry:
            current_book_entry['collection_id']=next((current_collection_entry['collection_id'] for current_collection_entry in current_collection_entries if set(current_collection_entry['source_directory_paths'])==set(current_book_entry['source_directory_paths']) or set(DEFAULT_COLLECTION_ROOTS[current_collection_entry['collection_id']])==set(current_book_entry['source_directory_paths'])),None)
        current_assigned_collection=next((current_collection_entry for current_collection_entry in current_collection_entries if current_collection_entry['collection_id']==current_book_entry.get('collection_id')),None)
        current_book_entry['collection_roots_changed_flag']=current_assigned_collection is not None and set(current_assigned_collection['source_directory_paths'])!=set(current_book_entry['source_directory_paths'])
    return {'source_directory_paths':sorted(current_directory_paths),'book_entries':current_book_entries,'collection_entries':current_collection_entries}


def read_book_artifact(current_config_values,current_book_id,current_artifact_name):
    if not re.fullmatch(BOOK_IDENTIFIER_PATTERN,current_book_id) or current_artifact_name not in {'book.html','book.md'}:
        raise ValueError('올바르지 않은 도서 경로입니다.')
    current_books_root=Path(current_config_values['private_state_root'])/'books'
    current_artifact_path=resolve_document_path(current_books_root,current_book_id+'/'+current_artifact_name)
    if not (current_artifact_path.parent/'manifest.yaml').is_file():
        raise ValueError('완료된 도서를 찾을 수 없습니다.')
    return current_artifact_path.read_bytes()

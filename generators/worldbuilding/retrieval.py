"""원본에서 재생성 가능한 문서 지도와 제한된 에이전트 탐색 계약."""
from collections import Counter
import copy
import math
from pathlib import Path
import posixpath
import re
from urllib.parse import unquote, urlsplit

DOCUMENT_MAP_VERSION = 1
MAXIMUM_SECTION_CHARACTERS = 2200
MAXIMUM_SEARCH_RESULTS = 10
MAXIMUM_DISCOVERY_ROUNDS = 7
MAXIMUM_READING_CHARACTERS = 11500
DISCOVERY_DECISION_SCHEMA = {'type':'object','additionalProperties':False,'required':['action_name','search_query_text','source_reference_ids','resolved_target_path','decision_reason_text'], 'properties':{'action_name':{'enum':['read','finish','search','abort']},'search_query_text':{'type':'string','maxLength':300},'source_reference_ids':{'type':'array','maxItems':4,'uniqueItems':True,'items':{'type':'string'}},'resolved_target_path':{'type':'string'},'decision_reason_text':{'type':'string','minLength':1,'maxLength':500}}}


def extract_document_terms(current_source_text):
    current_token_values=re.findall(r'[가-힣a-z0-9_-]{2,}',current_source_text.lower())
    return [re.sub(r'(들을|들은|에서|으로|에게|에는|의|은|는|을|를|에|과|와)$','',current_token_text) for current_token_text in current_token_values]


def build_document_record(current_source_entry):
    current_document_path=current_source_entry['source_document_path']
    current_document_lines=current_source_entry['source_document_body'].splitlines(keepends=True)
    current_section_entries=[]
    current_heading_text=''
    current_start_number=1
    current_chunk_lines=[]
    def append_document_section(current_end_number):
        current_excerpt_text=''.join(current_chunk_lines)
        current_section_entries.append({'source_reference_id':f'{current_document_path}:{current_start_number}-{current_end_number}', 'source_document_path':current_document_path,'source_start_line':current_start_number,'source_end_line':current_end_number,'section_heading_text':current_heading_text,'section_preview_text':current_excerpt_text[:180], 'section_term_counts':dict(Counter(extract_document_terms(current_excerpt_text)))})
    for current_line_number,current_line_text in enumerate(current_document_lines,1):
        current_heading_match=re.match(r'^#{1,6} +(.+)',current_line_text)
        if current_chunk_lines and (current_heading_match or sum(map(len,current_chunk_lines))+len(current_line_text)>MAXIMUM_SECTION_CHARACTERS):
            append_document_section(current_line_number-1)
            current_chunk_lines=[]
            current_start_number=current_line_number
        if current_heading_match:
            current_heading_text=current_heading_match.group(1)
        current_chunk_lines.append(current_line_text)
    if current_chunk_lines:
        append_document_section(len(current_document_lines))
    current_link_entries=[]
    for current_link_label,current_link_url in re.findall(r'(?<!!)\[([^]\n]+)\]\(([^\s)]+)\)',current_source_entry['source_document_body']):
        current_url_parts=urlsplit(current_link_url)
        if current_url_parts.scheme or current_url_parts.netloc or not current_url_parts.path:
            continue
        current_link_path=posixpath.normpath(posixpath.join(posixpath.dirname(current_document_path),unquote(current_url_parts.path)))
        if current_link_path.startswith(('../','/')):
            continue
        current_link_entries.append({'link_label_text':current_link_label,'linked_document_path':current_link_path})
    current_heading_values=re.findall(r'^#{1,6} +(.+)$',current_source_entry['source_document_body'],re.M)
    current_named_values=re.findall(r'\*\*([^*\n]{2,80})\*\*|`([^`\n]{2,80})`|(?:name|title|이름|명칭|별칭):\s*([^\n]{2,80})',current_source_entry['source_document_body'])
    current_mention_values=sorted({current_named_text.strip() for current_named_group in current_named_values for current_named_text in current_named_group if current_named_text})
    return {'source_document_path':current_document_path,'source_content_hash':current_source_entry['source_content_hash'],'document_title_text':current_heading_values[0] if current_heading_values else current_document_path,'document_heading_values':current_heading_values,'document_mention_values':current_mention_values,'document_link_entries':current_link_entries,'document_section_entries':current_section_entries}



def validate_document_map(current_document_map):
    from jsonschema import Draft202012Validator
    def build_strict_object(current_property_fields):
        return {'type':'object','additionalProperties':False,'required':list(current_property_fields),'properties':current_property_fields}
    current_string_schema={'type':'string'}
    current_link_schema=build_strict_object({'link_label_text':current_string_schema,'linked_document_path':current_string_schema})
    current_section_schema=build_strict_object({'source_reference_id':current_string_schema,'source_document_path':current_string_schema,'source_start_line':{'type':'integer','minimum':1},'source_end_line':{'type':'integer','minimum':1},'section_heading_text':current_string_schema,'section_preview_text':current_string_schema,'section_term_counts':{'type':'object','additionalProperties':{'type':'integer','minimum':1}}})
    current_record_schema=build_strict_object({'source_document_path':current_string_schema,'source_content_hash':current_string_schema,'document_title_text':current_string_schema,'document_heading_values':{'type':'array','items':current_string_schema},'document_mention_values':{'type':'array','items':current_string_schema},'document_link_entries':{'type':'array','items':current_link_schema},'document_section_entries':{'type':'array','items':current_section_schema}})
    Draft202012Validator(build_strict_object({'document_map_version':{'const':DOCUMENT_MAP_VERSION},'document_records':{'type':'object','additionalProperties':current_record_schema}})).validate(current_document_map)
    for current_document_path,current_document_record in current_document_map['document_records'].items():
        if current_document_record['source_document_path']!=current_document_path:
            raise ValueError('문서 지도 키와 경로가 다릅니다.')
        for current_section_entry in current_document_record['document_section_entries']:
            expected_reference_text=f"{current_document_path}:{current_section_entry['source_start_line']}-{current_section_entry['source_end_line']}"
            if current_section_entry['source_document_path']!=current_document_path or current_section_entry['source_reference_id']!=expected_reference_text or current_section_entry['source_end_line']<current_section_entry['source_start_line']:
                raise ValueError('문서 지도 원문 구간이 올바르지 않습니다.')


def refresh_document_map(source_document_entries,previous_document_map=None):
    previous_document_map=previous_document_map or {'document_map_version':DOCUMENT_MAP_VERSION,'document_records':{}}
    if set(previous_document_map)!={'document_map_version','document_records'} or previous_document_map['document_map_version']!=DOCUMENT_MAP_VERSION or not isinstance(previous_document_map['document_records'],dict):
        raise ValueError('문서 지도 형식 또는 버전이 올바르지 않습니다.')
    validate_document_map(previous_document_map)
    current_document_records={}
    changed_document_paths=[]
    for current_document_path,current_source_entry in source_document_entries.items():
        previous_document_record=previous_document_map['document_records'].get(current_document_path)
        if previous_document_record and previous_document_record['source_content_hash']==current_source_entry['source_content_hash']:
            current_document_records[current_document_path]=previous_document_record
        else:
            current_document_records[current_document_path]=build_document_record(current_source_entry)
            changed_document_paths.append(current_document_path)
    return {'document_map_version':DOCUMENT_MAP_VERSION,'document_records':current_document_records}, {'changed_document_paths':changed_document_paths,'removed_document_paths':sorted(set(previous_document_map['document_records'])-set(current_document_records))}


def search_document_map(current_document_map,current_query_text,preferred_document_paths=(),primary_document_roots=()):
    current_search_terms=set(extract_document_terms(current_query_text)) - {'설정','추가해줘','찾아','새로운','기존','참고하여','작성해줘','문서','대한'}
    current_document_records=current_document_map['document_records']
    current_section_entries=[current_section_entry for current_document_record in current_document_records.values() for current_section_entry in current_document_record['document_section_entries']]
    current_term_frequencies={current_search_term:sum(any(current_search_term in current_index_term for current_index_term in current_section_entry['section_term_counts']) for current_section_entry in current_section_entries) for current_search_term in current_search_terms}
    current_incoming_labels={current_document_path:[] for current_document_path in current_document_records}
    for current_document_record in current_document_records.values():
        for current_link_entry in current_document_record['document_link_entries']:
            if current_link_entry['linked_document_path'] in current_incoming_labels:
                current_incoming_labels[current_link_entry['linked_document_path']].append(current_link_entry['link_label_text'])
    current_ranked_entries=[]
    for current_section_entry in current_section_entries:
        if all(not current_line_text.strip() or current_line_text.lstrip().startswith('#') for current_line_text in current_section_entry['section_preview_text'].splitlines()):
            continue
        current_document_path=current_section_entry['source_document_path']
        current_document_record=current_document_records[current_document_path]
        current_metadata_text=' '.join([current_document_path,current_document_record['document_title_text'],current_section_entry['section_heading_text'],*current_document_record['document_mention_values'],*current_incoming_labels[current_document_path]]).lower()
        current_match_score=100.0 if current_query_text.strip().lower()==current_document_path.lower() else 0.0
        for current_search_term in current_search_terms:
            if not current_search_term:
                continue
            current_occurrence_count=sum(current_term_count for current_index_term,current_term_count in current_section_entry['section_term_counts'].items() if current_search_term in current_index_term)
            current_match_score+=(min(current_occurrence_count,4)+5*(current_search_term in current_metadata_text))*math.log(2+len(current_section_entries)/(1+current_term_frequencies[current_search_term]))
        if current_document_path in preferred_document_paths:
            current_match_score+=12
        if current_match_score<=0:
            continue
        if any(current_document_path.startswith(current_primary_root.rstrip('/')+'/') for current_primary_root in primary_document_roots):
            current_match_score+=15
        if current_document_path.startswith('history/'):
            current_match_score-=20
        current_ranked_entries.append({'source_reference_id':current_section_entry['source_reference_id'],'source_document_path':current_document_path,'document_title_text':current_document_record['document_title_text'],'section_heading_text':current_section_entry['section_heading_text'],'section_preview_text':current_section_entry['section_preview_text'],'related_document_paths':sorted({current_link_entry['linked_document_path'] for current_link_entry in current_document_record['document_link_entries'] if current_link_entry['linked_document_path'] in current_document_records})[:8],'search_match_score':round(current_match_score,3)})
    selected_candidate_entries=[]
    selected_document_counts=Counter()
    for current_candidate_entry in sorted(current_ranked_entries,key=lambda current_section_entry:(-current_section_entry['search_match_score'],current_section_entry['source_reference_id'])):
        if selected_document_counts[current_candidate_entry['source_document_path']]>=2:
            continue
        selected_candidate_entries.append(current_candidate_entry)
        selected_document_counts[current_candidate_entry['source_document_path']]+=1
        if len(selected_candidate_entries)>=MAXIMUM_SEARCH_RESULTS:
            break
    return selected_candidate_entries


def read_document_sections(current_document_map,source_document_entries,requested_reference_ids):
    current_section_lookup={current_section_entry['source_reference_id']:current_section_entry for current_document_record in current_document_map['document_records'].values() for current_section_entry in current_document_record['document_section_entries']}
    current_read_entries=[]
    for current_reference_id in requested_reference_ids:
        if current_reference_id not in current_section_lookup:
            raise ValueError(f'문서 지도에 없는 원문 구간: {current_reference_id}')
        current_section_entry=current_section_lookup[current_reference_id]
        current_document_path=current_section_entry['source_document_path']
        current_source_entry=source_document_entries[current_document_path]
        if current_source_entry['source_content_hash']!=current_document_map['document_records'][current_document_path]['source_content_hash']:
            raise ValueError(f'오래된 문서 지도: {current_document_path}')
        current_source_lines=current_source_entry['source_document_body'].splitlines(keepends=True)
        current_read_entries.append({'source_reference_id':current_reference_id,'source_document_path':current_document_path,'source_content_hash':current_source_entry['source_content_hash'],'source_excerpt_text':''.join(current_source_lines[current_section_entry['source_start_line']-1:current_section_entry['source_end_line']]),'source_approval_state':'historical' if current_document_path.startswith('history/') else 'mixed_or_unresolved','source_required_flag':False})
    return current_read_entries


def validate_discovery_decision(current_decision_values,candidate_reference_ids,read_reference_ids):
    current_action_name=current_decision_values['action_name']
    current_selected_references=current_decision_values['source_reference_ids']
    if current_action_name=='search':
        if not current_decision_values['search_query_text'].strip() or current_selected_references or current_decision_values['resolved_target_path']:
            raise ValueError('검색은 검색어만 지정해야 합니다.')
    elif current_action_name=='read':
        if not current_selected_references or not set(current_selected_references).issubset(candidate_reference_ids) or current_decision_values['search_query_text'] or current_decision_values['resolved_target_path']:
            raise ValueError('읽기는 검색 결과에 실제 존재하는 구간만 지정해야 합니다.')
    elif current_action_name=='finish':
        if not current_selected_references or not set(current_selected_references).issubset(read_reference_ids) or current_decision_values['search_query_text']:
            raise ValueError('탐색 완료는 실제 읽은 구간만 선택해야 합니다.')
    else:
        raise ValueError('지원하지 않는 탐색 동작입니다.')



def build_discovery_schema(current_request_values,current_candidate_entries,current_read_lookup,current_config_values,current_search_count=0):
    current_schema_variants=[]
    for current_action_name in ['read','finish','search','abort']:
        current_schema_value=copy.deepcopy(DISCOVERY_DECISION_SCHEMA)
        current_schema_fields=current_schema_value['properties']
        current_schema_fields['action_name']={'const':current_action_name}
        current_schema_fields['resolved_target_path']={'const':''}
        if current_action_name=='abort':
            current_schema_fields['search_query_text']={'const':''}
            current_schema_fields['source_reference_ids']={'const':[]}
        elif current_action_name=='search':
            if current_search_count>=2:
                continue
            current_schema_fields['search_query_text']['minLength']=1
            current_schema_fields['source_reference_ids']['maxItems']=0
        else:
            current_schema_fields['search_query_text']={'const':''}
            current_reference_values=[current_candidate_entry['source_reference_id'] for current_candidate_entry in current_candidate_entries if current_candidate_entry['source_reference_id'] not in current_read_lookup and sum(current_read_entry['source_document_path']==current_candidate_entry['source_document_path'] for current_read_entry in current_read_lookup.values())<2] if current_action_name=='read' else list(current_read_lookup)
            if not current_reference_values or (current_action_name=='read' and len(current_read_lookup)>=4):
                continue
            current_schema_fields['source_reference_ids'].update(minItems=1,maxItems=1,items={'enum':current_reference_values})
            if current_action_name=='finish':
                current_schema_fields['source_reference_ids']={'const':list(current_read_lookup)}
            if current_action_name=='finish' and current_request_values['requested_operation_mode']!='create':
                current_target_values=sorted({current_read_entry['source_document_path'] for current_read_entry in current_read_lookup.values() if Path(current_read_entry['source_document_path']).suffix=='.md' and current_read_entry['source_document_path'] not in current_config_values['protected_document_paths'] and any(current_read_entry['source_document_path'].startswith(current_write_root.rstrip('/')+'/') for current_write_root in current_config_values['allowed_write_roots']) and (not current_request_values['requested_target_path'] or current_read_entry['source_document_path']==current_request_values['requested_target_path'])})
                if not current_target_values:
                    continue
                current_schema_fields['resolved_target_path']={'enum':current_target_values}
        current_schema_variants.append(current_schema_value)
    return {'anyOf':current_schema_variants}



def retrieve_candidate_sections(current_document_map,current_query_text,preferred_document_paths,primary_document_roots,semantic_search_function):
    lexical_result_entries=search_document_map(current_document_map,current_query_text,preferred_document_paths,primary_document_roots)
    if semantic_search_function is None:
        return lexical_result_entries
    semantic_result_entries=semantic_search_function(current_query_text)
    current_candidate_lookup={current_candidate_entry['source_reference_id']:dict(current_candidate_entry) for current_candidate_entry in lexical_result_entries}
    current_rank_scores={current_candidate_entry['source_reference_id']:1/(60+current_rank_number) for current_rank_number,current_candidate_entry in enumerate(lexical_result_entries,1)}
    current_section_lookup={current_section_entry['source_reference_id']:(current_document_record,current_section_entry) for current_document_record in current_document_map['document_records'].values() for current_section_entry in current_document_record['document_section_entries']}
    for current_rank_number,current_semantic_entry in enumerate(semantic_result_entries,1):
        current_reference_id=current_semantic_entry['source_reference_id']
        if current_reference_id not in current_section_lookup:
            raise ValueError('현재 문서 지도에 없는 RAG 검색 구간입니다.')
        current_rank_scores[current_reference_id]=current_rank_scores.get(current_reference_id,0)+1/(60+current_rank_number)
        if current_reference_id not in current_candidate_lookup:
            current_document_record,current_section_entry=current_section_lookup[current_reference_id]
            current_candidate_lookup[current_reference_id]={'source_reference_id':current_reference_id,'source_document_path':current_document_record['source_document_path'],'document_title_text':current_document_record['document_title_text'],'section_heading_text':current_section_entry['section_heading_text'],'section_preview_text':current_section_entry['section_preview_text'],'related_document_paths':[current_link_entry['linked_document_path'] for current_link_entry in current_document_record['document_link_entries'] if current_link_entry['linked_document_path'] in current_document_map['document_records']][:8]}
        current_candidate_lookup[current_reference_id]['semantic_similarity_score']=round(current_semantic_entry['similarity_score'],5)
    selected_candidate_entries=[]
    selected_document_counts=Counter()
    for current_reference_id in sorted(current_rank_scores,key=lambda current_reference_id:(-current_rank_scores[current_reference_id],current_reference_id)):
        current_candidate_entry=current_candidate_lookup[current_reference_id]
        if selected_document_counts[current_candidate_entry['source_document_path']]>=2:
            continue
        current_candidate_entry['search_match_score']=round(current_rank_scores[current_reference_id],6)
        selected_candidate_entries.append(current_candidate_entry)
        selected_document_counts[current_candidate_entry['source_document_path']]+=1
        if len(selected_candidate_entries)>=MAXIMUM_SEARCH_RESULTS:
            break
    return selected_candidate_entries


def discover_document_context(current_config_values,current_request_values,current_document_map,source_document_entries,request_decision_function,record_decision_function,semantic_search_function=None):
    """검색 결과를 읽은 뒤에만 작성 단계로 전환한다. 모델 호출은 주입한다."""
    from jsonschema import Draft202012Validator
    current_query_text=current_request_values['requested_instruction_text']
    preferred_document_paths=[current_request_values['requested_target_path']] if current_request_values['requested_target_path'] else []
    current_candidate_entries=retrieve_candidate_sections(current_document_map,current_query_text,preferred_document_paths,current_config_values['allowed_write_roots'],semantic_search_function)
    current_read_lookup={}
    current_search_history=[]
    current_document_records=current_document_map['document_records']
    for current_round_number in range(1,MAXIMUM_DISCOVERY_ROUNDS+1):
        current_discovery_payload={'task_instruction_data':current_request_values,'source_document_root':current_config_values['source_document_root'],'primary_document_roots':[str(Path(current_config_values['source_document_root'])/current_write_root) for current_write_root in current_config_values['allowed_write_roots']],'required_source_paths':current_config_values['required_source_paths'],'document_count':len(current_document_records),'round_number':current_round_number,'remaining_rounds':MAXIMUM_DISCOVERY_ROUNDS-current_round_number,'search_history':current_search_history,'search_results':current_candidate_entries,'read_source_entries':list(current_read_lookup.values())}
        current_decision_schema=build_discovery_schema(current_request_values,current_candidate_entries,current_read_lookup,current_config_values,len(current_search_history))
        current_decision_values=request_decision_function(current_discovery_payload,current_decision_schema)
        Draft202012Validator(current_decision_schema).validate(current_decision_values)
        if current_decision_values['action_name']=='abort':
            record_decision_function(current_round_number,current_discovery_payload,current_decision_values)
            raise ValueError('문서 탐색 근거 부족: '+current_decision_values['decision_reason_text'])
        validate_discovery_decision(current_decision_values,{current_candidate_entry['source_reference_id'] for current_candidate_entry in current_candidate_entries},set(current_read_lookup))
        record_decision_function(current_round_number,current_discovery_payload,current_decision_values)
        if current_decision_values['action_name']=='search':
            current_query_text=current_decision_values['search_query_text']
            current_candidate_entries=retrieve_candidate_sections(current_document_map,current_query_text,[],current_config_values['allowed_write_roots'],semantic_search_function)
            current_search_history.append({'search_query_text':current_query_text,'result_count':len(current_candidate_entries)})
        elif current_decision_values['action_name']=='read':
            for current_read_entry in read_document_sections(current_document_map,source_document_entries,current_decision_values['source_reference_ids']):
                current_read_lookup[current_read_entry['source_reference_id']]=current_read_entry
            if sum(len(current_read_entry['source_excerpt_text']) for current_read_entry in current_read_lookup.values())>MAXIMUM_READING_CHARACTERS:
                raise ValueError('탐색 원문 예산 초과: 지시의 주제를 좁혀 주세요.')
            related_document_paths={current_link_entry['linked_document_path'] for current_read_entry in current_read_lookup.values() for current_link_entry in current_document_records[current_read_entry['source_document_path']]['document_link_entries'] if current_link_entry['linked_document_path'] in current_document_records}
            related_document_paths.update(current_read_entry['source_document_path'] for current_read_entry in current_read_lookup.values())
            current_candidate_entries=retrieve_candidate_sections(current_document_map,current_query_text,related_document_paths,current_config_values['allowed_write_roots'],semantic_search_function)
        else:
            selected_source_entries=[current_read_lookup[current_reference_id] for current_reference_id in current_decision_values['source_reference_ids']]
            resolved_request_values=dict(current_request_values)
            if current_request_values['requested_operation_mode']!='create':
                resolved_target_path=current_decision_values['resolved_target_path']
                if current_request_values['requested_target_path'] and resolved_target_path!=current_request_values['requested_target_path']:
                    raise ValueError('탐색 결과가 사용자가 지정한 수정 대상과 다릅니다.')
                if resolved_target_path not in {current_read_entry['source_document_path'] for current_read_entry in selected_source_entries}:
                    raise ValueError('수정 대상은 최종 문맥으로 선택한 원문이어야 합니다.')
                if Path(resolved_target_path).suffix!='.md':
                    raise ValueError('수정 대상은 Markdown(.md) 문서여야 합니다. YAML은 참고 자료로만 사용합니다.')
                if resolved_target_path in current_config_values['protected_document_paths'] or not any(resolved_target_path.startswith(current_write_root.rstrip('/')+'/') for current_write_root in current_config_values['allowed_write_roots']):
                    raise ValueError('탐색한 수정 대상이 허용된 쓰기 범위 밖입니다.')
                resolved_request_values['requested_target_path']=resolved_target_path
            elif current_decision_values['resolved_target_path']:
                raise ValueError('신규 작성 탐색은 기존 수정 대상을 지정하지 않습니다.')
            return selected_source_entries,resolved_request_values
    raise ValueError('문서 탐색 횟수 안에 근거를 확정하지 못했습니다. 탐색 기록을 확인하고 지시를 구체화하세요.')

"""운영 대화와 직접 조회 화면이 공유하는 관리 기능 목록."""

def format_capability_table(current_catalog_record, current_search_text=""):
    current_effect_labels = {'read':'조회', 'write':'원본 저장', 'enqueue':'대기열 접수', 'recovery_possible':'상태 복구 가능', 'cancel_request':'중지 요청', 'local_bookkeeping':'상태 조회·로컬 잠금'}
    current_gpu_labels = {'none':'사용 안 함', 'exclusive':'배타 사용', 'queued':'대기열 사용', 'inspection':'GPU 상태 조회 · 대기열 밖'}
    current_interface_labels={'gui':'화면','mcp':'Codex MCP','isolated_fixed_bridge':'격리 조회'}
    current_retry_labels={'safe':'같은 요청 재시도 가능','request_id':'같은 접수 ID','request_id_or_unknown':'같은 ID · 불확실 시 확인','check_status':'상태 확인'}
    current_all_rows=[[current_record['label'],current_record['command'],', '.join(current_interface_labels.get(current_interface,current_interface) for current_interface in current_record['interfaces']),'필수: '+(', '.join(current_record['required']) or '없음')+' · 선택: '+(', '.join(current_record.get('optional', [])) or '없음'),current_effect_labels.get(current_record['effect'],current_record['effect']),current_gpu_labels.get(current_record['gpu'],current_record['gpu']),current_retry_labels.get(current_record['retry'],current_record['retry']),current_record['note']] for current_record in current_catalog_record['records']]
    for current_tool_record in current_catalog_record.get('mcp_only_tools',[]):
        current_all_rows.append([current_tool_record['label'],current_tool_record['name'],'Codex MCP','필수: '+(', '.join(current_tool_record['required']) or '없음')+' · 선택: '+(', '.join(current_tool_record['optional']) or '없음'),current_effect_labels.get(current_tool_record['effect'],current_tool_record['effect']),current_gpu_labels.get(current_tool_record['gpu'],current_tool_record['gpu']),current_retry_labels.get(current_tool_record['retry'],current_tool_record['retry']),current_tool_record['note']])
    if not isinstance(current_search_text,str) or len(current_search_text)>100:
        raise ValueError('검색어는 100자 이하여야 합니다.')
    current_search_value=current_search_text.strip().casefold()
    current_rows_value=[current_row_value for current_row_value in current_all_rows if not current_search_value or current_search_value in ' '.join(current_row_value).casefold()]
    current_unlisted_commands=current_catalog_record.get('unlisted_commands',[])
    current_status_text='기능 '+str(len(current_rows_value))+'개 / 전체 '+str(len(current_all_rows))+'개 · 작업 변경은 각 확인 절차와 서비스 검증을 따릅니다. MCP 표시는 서버 구현 기준입니다. 현재 Codex 연결의 도구 목록에 없으면 MCP를 다시 연결하세요.'
    if current_unlisted_commands:
        current_status_text+=' 목록에 없는 등록 명령: '+', '.join(current_unlisted_commands)+' · 지원 여부 확인 필요'
    return current_rows_value,current_status_text

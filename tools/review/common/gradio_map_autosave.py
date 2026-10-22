"""브라우저 임시 초안 복구 검증. 원본 저장과 분리한다."""
import copy

MAP_AUTOSAVE_KEY_PREFIX='slime-map-editor-draft-v1:'


def restore_map_autosave_state(current_map_identifier,current_live_state,current_saved_record,current_load_callback):
    if current_live_state:return current_live_state
    current_fresh_state=current_load_callback(current_map_identifier,{})[0]
    if current_saved_record is None:return current_fresh_state
    if not isinstance(current_saved_record,dict) or current_saved_record.get('version')!=1:raise ValueError('지원하지 않는 임시저장 형식입니다. 임시본을 보관한 뒤 삭제하세요.')
    current_saved_state=current_saved_record.get('state')
    if not isinstance(current_saved_state,dict) or set(current_saved_state)!={'snapshot','draft','history','future'}:raise ValueError('임시저장 상태 형식 오류')
    if not isinstance(current_saved_state['draft'],dict) or not isinstance(current_saved_state['history'],list) or not isinstance(current_saved_state['future'],list):raise ValueError('임시저장 편집 이력 형식 오류')
    if current_saved_state['draft'].get('map')!=current_map_identifier:raise ValueError('다른 맵의 임시저장입니다.')
    if current_saved_state['draft'].get('revision')!=current_fresh_state['draft']['revision']:raise ValueError('원본이 변경되어 임시본 자동 복구를 중단했습니다. 임시본은 보존됩니다. JSON으로 보관한 뒤 원본과 비교하세요.')
    current_saved_revision=current_fresh_state['draft']['revision']
    for current_draft_record in [current_saved_state['draft'],*current_saved_state['history'],*current_saved_state['future']]:
        if not isinstance(current_draft_record,dict) or set(current_draft_record)!={'map','revision','cells','objects'} or current_draft_record['map']!=current_map_identifier or current_draft_record['revision']!=current_saved_revision or not isinstance(current_draft_record['cells'],list) or not isinstance(current_draft_record['objects'],list):raise ValueError('임시저장 편집 이력 형식 오류')
    current_restored_state=copy.deepcopy(current_saved_state)
    current_restored_state['snapshot']=current_fresh_state['snapshot']
    return current_restored_state

MAP_AUTOSAVE_WRITE_SCRIPT="""currentEditorState=>{
 if(!currentEditorState?.draft)return '임시저장 대기 · 편집 내용이 생기면 현재 탭에 자동 보관합니다.';
 if(!currentEditorState.history.length&&!currentEditorState.future?.length)return '임시저장 대기 · 변경 내용이 없습니다.';
 try{const currentSavedTime=new Date().toISOString();sessionStorage.setItem('slime-map-editor-draft-v1:'+currentEditorState.draft.map,JSON.stringify({version:1,savedAt:currentSavedTime,state:currentEditorState}));return '자동 임시저장 완료 · '+new Date(currentSavedTime).toLocaleTimeString()+' · 현재 탭에 보관됨. 원본 저장은 별도입니다.';}
 catch(currentStorageError){return '임시저장 실패 · '+currentStorageError.message+' · 초안 JSON을 보관하거나 원본에 저장하세요.';}
}"""

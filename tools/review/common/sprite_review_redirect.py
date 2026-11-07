"""이전 등록 애니메이션 문서 링크를 통합 편집기로 연결한다."""
from urllib.parse import urlencode


def resolve_sprite_review_redirect(current_request_path,current_query_values,current_page_records):
    current_review_identifier=(current_query_values.get('review') or current_query_values.get('tool') or [''])[0]
    current_animation_pages=[current_page_record for current_page_record in current_page_records if current_page_record.get('anchorEditor') or current_page_record.get('category')=='animation']
    current_selected_page=next((current_page_record for current_page_record in current_animation_pages if current_page_record['id']==current_review_identifier),None)
    if current_request_path.rstrip('/') in ('/management','/management/frame/static-review'):
        if current_selected_page is None:return None
    else:
        current_selected_page=next((current_page_record for current_page_record in current_animation_pages if '/'+current_page_record['path'].lstrip('/').split('?')[0]==current_request_path),None)
        if current_selected_page is None:return None
    current_target_values={'tool':'sprite-sheet-editor','category':'animation-tool'}
    current_action_identifier=(current_query_values.get('action') or [''])[0]
    if current_action_identifier.startswith('asset:'):
        current_target_values['action']=current_action_identifier
    else:
        current_description_parts=current_selected_page.get('description','').split(' · ')
        if len(current_description_parts)>=3 and current_description_parts[0]=='Gradio':
            current_target_values['action']='asset:'+current_description_parts[1]
    return '/management/frame/sprite-sheet-editor/?'+urlencode(current_target_values)

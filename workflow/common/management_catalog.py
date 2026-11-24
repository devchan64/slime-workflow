"""운영 대화와 관리 메뉴가 공유하는 도구 카탈로그."""
import json
from urllib.parse import quote


CATEGORY_LABEL_VALUES={'all':'전체','model-management':'모델 관리','map-review':'맵 검수','sound-management':'소리 관리','writer-agent':'텍스트 기반','image-generation':'이미지 생성','animation-tool':'애니메이션 도구','game-ui':'게임 UI · 디자인 시스템'}
ARCHIVED_IMAGE_PAGE_IDENTIFIERS=frozenset(('mannequin-generator','character-generator','qwen-21-generator','qwen-21-circular-generator','expression-generator','vegetation-generator','prop-generator','billboard-generator'))
LEGACY_SOUND_CATEGORY_NAMES=('music-generation','sound-effects')
MANAGEMENT_FRAME_PATH_PREFIX='/management/frame/'
MANAGEMENT_FRAME_IDENTIFIER_VALUES={}
NATIVE_MANAGEMENT_APPLICATIONS=frozenset(('mannequin-generator','character-generator','model-management','dwpose-generator','wan22-animate2-generator','kimodo-generator','wan22-vace-generator','wan22-fun-control-generator','billboard-generator','effect-editor','asset-editor','building-editor','world-map','vegetation-generator','prop-generator','building-generator','sfx-dasheng-audiogen','music-heartmula','qwen-21-circular-generator','qwen-21-generator','expression-generator','map-review','writer-agent','sprite-sheet-editor'))
NATIVE_MANAGEMENT_APPLICATIONS = NATIVE_MANAGEMENT_APPLICATIONS | {'prompt-translation'}
NATIVE_MANAGEMENT_APPLICATIONS = NATIVE_MANAGEMENT_APPLICATIONS | {'flux-expression-generator'}
NATIVE_MANAGEMENT_APPLICATIONS = NATIVE_MANAGEMENT_APPLICATIONS | {'hermes-agent'}
NATIVE_MANAGEMENT_APPLICATIONS = NATIVE_MANAGEMENT_APPLICATIONS | {'wan22-i2v-generator'}
NATIVE_MANAGEMENT_APPLICATIONS = NATIVE_MANAGEMENT_APPLICATIONS | {'wan21-t2v-generator','wan21-i2v-generator'}
NATIVE_MANAGEMENT_APPLICATIONS = NATIVE_MANAGEMENT_APPLICATIONS | {current_flux_profile+'-generator' for current_flux_profile in ('flux-image','flux-character','flux-mannequin','flux-billboard','flux-prop','flux-vegetation','flux-building','flux-seamless')}
LEGACY_PAGE_IDENTIFIER_VALUES={'map-review':'map-review-iseulon','animation-2':'animation-1','animation-3':'animation-1'}
REACT_REVIEW_PATHS = {"kimodo-generator": "/management/frame/kimodo-generator/", "asset-editor": "/management/frame/asset-editor/", "sprite-sheet-editor": "/management/frame/sprite-sheet-editor/", "effect-editor": "/management/frame/effect-editor/", "building-editor": "/management/frame/building-editor/", "map-review": "/management/frame/map-review/", "wan22-fun-control-generator":"/management/frame/wan22-fun-control-generator/", "wan22-vace-generator":"/management/frame/wan22-vace-generator/", "wan22-animate2-generator":"/management/frame/wan22-animate2-generator/", "writer-agent":"/management/frame/writer-agent/", **{name+"-generator": "/management/frame/"+name+"-generator/" for name in ("flux-prop","flux-vegetation","flux-billboard","flux-mannequin","flux-building","flux-character","flux-seamless","flux-expression")}, "flux-image-generator": "/management/frame/flux-image-generator/", "music-heartmula": "/management/frame/music-heartmula/", "sfx-dasheng-audiogen": "/management/frame/sfx-dasheng-audiogen/", "dwpose-generator": "/management/frame/dwpose-generator/", "hermes-agent": "/management/frame/hermes-agent/", "model-management": "/management/frame/model-management/", "world-map": "/management/frame/world-map/", "prompt-translation": "/management/frame/prompt-translation/"}
REACT_REVIEW_PATHS['wan22-i2v-generator'] = '/management/frame/wan22-i2v-generator/'
REACT_REVIEW_PATHS.update({name: '/management/frame/'+name+'/' for name in ('wan21-t2v-generator','wan21-i2v-generator')})
DEFAULT_PAGE_RECORDS=(
    *({'id':name+'-generator','label':'FLUX 3 '+label+' 생성기','path':'/management/frame/'+name+'-generator/','category':'image-generation','uiMode':'react','description':'공용 화풍 · FLUX 이력 및 입력 복원'} for name,label in (('flux-image','일반 이미지'),('flux-character','캐릭터'),('flux-mannequin','마네킨'),('flux-billboard','빌보드 가이드'),('flux-prop','소품'),('flux-vegetation','식생'),('flux-building','건물'),('flux-seamless','심리스 타일'))),
    {'id':'flux-expression-generator','label':'FLUX 3 표정 생성기','path':'/management/frame/flux-expression-generator/','category':'image-generation','uiMode':'react','description':'얼굴 참조 1장 · 표정 프리셋 · 이력 입력 복원'},
    {'id':'model-management','label':'모델 다운로드·빌드 상태','path':REACT_REVIEW_PATHS['model-management'],'category':'model-management','uiMode':'react','description':'생성기 모델 다운로드와 GPU 빌드 상태'},
    {'id':'sprite-sheet-editor','label':'스프라이트 시트 편집기','path':REACT_REVIEW_PATHS['sprite-sheet-editor'],'category':'animation-tool','uiMode':'react','description':'프레임 크롭 · 앵커 정렬 · 시트와 좌표맵 출력'},
    {'id':'effect-editor','label':'발광 이펙트 좌표 검수','path':REACT_REVIEW_PATHS['effect-editor'],'category':'map-review','uiMode':'react','description':'빌보드 연결 발광·프레임 정렬·DB 저장'},
    {'id':'building-editor','label':'건물 에셋 관리','path':'/management/frame/building-editor/','category':'map-review','uiMode':'react','description':'건물 원본·사용 맵·공용 앵커 관리'},
    {'id':'asset-editor','label':'공용 빌보드 에셋 관리','path':REACT_REVIEW_PATHS['asset-editor'],'category':'map-review','uiMode':'react','description':'전체 에셋 속성·점유 타일·미리보기·일괄 편집'},
    {'id':'world-map','label':'월드맵 검수','path':REACT_REVIEW_PATHS['world-map'],'category':'map-review','uiMode':'react','description':'전체 맵 썸네일·노드·연결·원본 해시 검증'},
    {'id': 'sfx-dasheng-audiogen', 'label': 'Dasheng-AudioGen 효과음 생성기', 'path': REACT_REVIEW_PATHS['sfx-dasheng-audiogen'], 'category': 'sound-management', 'uiMode': 'react', 'description': '로컬 ROCm · 길이 자동 예측 · 시드 · 16kHz WAV'},
    {'id': 'music-heartmula', 'label': 'HeartMuLa 3B 음악 생성기', 'path': REACT_REVIEW_PATHS['music-heartmula'], 'category': 'sound-management', 'uiMode': 'react', 'description': 'tags·lyrics 입력 · 무보컬 보장 없음'},
    {'id':'kimodo-generator','label':'Kimodo 모션 생성기','path':'/management/frame/kimodo-generator/','category':'animation-tool','uiMode':'react','description':'ROCm · SOMA v1.2 · 텍스트→3D 모션 · 비양자화 BF16 인코더'},
    {'id':'wan22-vace-generator','label':'Wan2.2 VACE-Fun 영상 생성기','path':'/management/frame/wan22-vace-generator/','category':'animation-tool','uiMode':'react','description':'A14B BF16 · 텍스트·외형 참조·첫 프레임'},
    {'id':'wan22-i2v-generator','label':'Wan2.2 I2V 영상 생성기','path':'/management/frame/wan22-i2v-generator/','category':'animation-tool','uiMode':'react','description':'첫 이미지 + 프롬프트 · Lightning'},
    {'id':'wan21-t2v-generator','label':'Wan 2.1 T2V 영상 생성기','path':REACT_REVIEW_PATHS['wan21-t2v-generator'],'category':'animation-tool','uiMode':'react','description':'1.3B · 텍스트 · 가속 및 KXSR LoRA 실험'},
    {'id':'wan21-i2v-generator','label':'Wan 2.1 I2V 영상 생성기','path':REACT_REVIEW_PATHS['wan21-i2v-generator'],'category':'animation-tool','uiMode':'react','description':'14B 480p · 첫 이미지 · 가속 및 격투 LoRA 실험'},
    {'id':'wan22-animate2-generator','label':'Wan Animate-2 캐릭터 동작 전사','path':'/management/frame/wan22-animate2-generator/','category':'animation-tool','uiMode':'react','description':'RGB 동작 영상 + 캐릭터 참조 · 일관성 실험'},
    {'id':'dwpose-generator','label':'DWPose 이미지 추출','path':REACT_REVIEW_PATHS['dwpose-generator'],'category':'animation-tool','uiMode':'react','description':'단일 PNG · 포즈와 좌표 추출 · ROCm 대기열'},
    {'id':'wan22-fun-control-generator','label':'Wan Fun Control 영상 생성기','path':'/management/frame/wan22-fun-control-generator/','category':'animation-tool','uiMode':'react','description':'2.2 A14B·2.1 1.3B · 외형 참조+제어 영상'},
    {'id':'qwen-21-circular-generator','label':'Qwen 2.1 순환 VAE 생성기','path':'/image-generation-21-circular/','category':'image-generation','uiMode':'archive','description':'XY 순환 디코더 · 3×3 반복 검수'},
    {'id':'vegetation-generator','label':'Qwen 2.1 빌보드 자연물타입 생성기','path':'/vegetation-generator/','category':'image-generation','uiMode':'archive','description':'자연물 빌보드 기본 문구 · 레이아웃·외형 참조 · 전용 대기열·이력'},
    {'id':'billboard-generator','label':'Qwen2.1 빌보드 가이드참조 생성기','path':'/billboard-generator/','category':'image-generation','uiMode':'archive','description':'높은형·중간형·바닥형 점유 가이드 · 80% 채움 · 벽면 밀착·낮은 판형 · 빌보드 독립 대기열·이력'},
    {'id':'prop-generator','label':'Qwen 2.1 빌보드 소품타입 생성기','path':'/prop-generator/','category':'image-generation','uiMode':'archive','description':'소품 직교투영 기본 문구 · 레이아웃·자재 참조 · 전용 대기열·이력'},
    {'id':'building-generator','label':'Qwen 2.1 건물 생성기','path':'/building-generator/','category':'image-generation','uiMode':'archive','description':'직교투영 기본 문구 · 레이아웃 이미지 선택 · 전용 대기열·이력'},
    {'id':'mannequin-generator','label':'Qwen 2.1 마네킨 생성기','path':'/mannequin-generator/','category':'image-generation','uiMode':'archive','description':'관절 신체·피부·기본복·얼굴 기준 후보 생성 · 마네킨 전용 이력'},
    {'id':'character-generator','label':'Qwen 2.1 캐릭터 이미지 생성기','path':'/character-generator/','category':'image-generation','uiMode':'archive','description':'공용 화풍 v1.5.0 원문 · 캐릭터 외관 예시 · Qwen 이력 공유'},
    {'id':'qwen-21-generator','label':'Qwen 2.1 이미지 생성기','path':'/image-generation-21/','category':'image-generation','uiMode':'archive','description':'공용 화풍 v1.5.0 기본 적용 · 투명 배경·참조 이미지 선택'},
    {'id':'writer-agent','label':'작가 AI 에이전트','path':REACT_REVIEW_PATHS['writer-agent'],'category':'writer-agent','uiMode':'react','description':' 문서 학습 · 아이디어 작성 · 실행 기록'},
    {'id':'hermes-agent','label':'운영 대화','path':REACT_REVIEW_PATHS['hermes-agent'],'category':'writer-agent','uiMode':'react','description':'대화로 관리 상태 확인과 작업 요청'},
    {'id':'prompt-translation','label':'프롬프트 번역','path':REACT_REVIEW_PATHS['prompt-translation'],'category':'writer-agent','uiMode':'react','description':'한국어 프롬프트 번역 · 작업 이력과 결과 검토'},
    {'id':'expression-generator','label':'Qwen 2.1 표정 생성기','path':'/expression-generator/','category':'image-generation','uiMode':'archive','description':'Qwen 2.1 · AU 표정 39종 · 참조 1~3장'},
)

def load_manager_page_records(source_file_path, current_animation_catalog=False):
    source_record_values=json.loads(source_file_path.read_text())
    if not isinstance(source_record_values,dict):
        raise ValueError('관리 메뉴 원본은 객체여야 합니다.')
    page_record_values=source_record_values.get('pages',[])
    if not isinstance(page_record_values,list):raise ValueError('관리 메뉴 페이지 목록 형식 오류')
    page_identifier_values=set()
    validated_page_records=[]
    for current_page_record in [*page_record_values,*DEFAULT_PAGE_RECORDS]:
        if not isinstance(current_page_record,dict):
            raise ValueError('관리 메뉴 페이지 항목은 객체여야 합니다.')
        if current_page_record.get('id') in ('mock-progress-validation','mock-dwpose-validation','mock-animate-validation','three-reference-generator','image-generator','floor-tile-generator','seamless-tile-generator','building-generator'):continue
        current_invalid_fields = [current_field_name for current_field_name in ('id','label','path','category','description') if not isinstance(current_page_record.get(current_field_name),str)]
        if current_invalid_fields:
            raise ValueError('관리 메뉴 페이지 필드는 문자열이어야 합니다: '+', '.join(current_invalid_fields))
        if any(current_page_record.get(current_field_name) is not None and not isinstance(current_page_record[current_field_name],str) for current_field_name in ('frameIdentifier','frameQuery')):raise ValueError('관리 메뉴 프레임 항목 형식 오류')
        if current_page_record['category'] in LEGACY_SOUND_CATEGORY_NAMES:
            current_page_record={**current_page_record,'category':'sound-management'}
        if current_page_record['id'] in ARCHIVED_IMAGE_PAGE_IDENTIFIERS: continue
        if current_page_record['id'] in ('tile-map-generator','sprite-editor-v2','character-review'):continue
        if current_page_record['id'] in ('wan22-animate-generator', 'anny-attribute-renderer', 'anny-attributes', 'anny-landmarks', 'pose-transfer-generator', 'animation-separation', 'outfit-transfer-generator', 'hy-motion-generator', 'character-animation', 'momask-generator', 'wan21-vace-generator', 'music-stable-audio', 'music-ace-step', 'sfx-stable-audio'):continue
        if current_page_record['id'] in ('qwen-21-generator','expression-generator','vegetation-generator','prop-generator','billboard-generator'):
            current_release_record = next(current_default_record for current_default_record in DEFAULT_PAGE_RECORDS if current_default_record['id'] == current_page_record['id'])
            current_page_record = {**current_page_record, 'label': current_release_record['label'], 'description': current_release_record['description']}
        if current_page_record['id'].startswith('map-review-'):
            # 빌드된 메뉴의 분류를 사용한다. 공용 메뉴 표시에는 콘텐츠 API가 필요하지 않다.
            current_review_category=current_page_record['category']
            current_map_name=current_page_record['label'].split(' · ')[0]
            current_page_record={**current_page_record,'category':current_review_category,'label':current_map_name+' · '+('도시맵 검수' if current_review_category=='town-map-review' else '맵 검수')}
        if current_page_record['id'] in page_identifier_values:continue
        if not current_page_record['path'].startswith('/'):current_page_record={**current_page_record,'path':'/'+current_page_record['path']}
        if current_page_record['id'] in REACT_REVIEW_PATHS:
            current_page_record = {**current_page_record, 'uiMode':'react', 'path':REACT_REVIEW_PATHS[current_page_record['id']]}
        page_identifier_values.add(current_page_record['id'])
        validated_page_records.append(current_page_record)
    if not current_animation_catalog:
        validated_page_records=[current_page_record for current_page_record in validated_page_records if current_page_record['category']!='animation' and not current_page_record.get('anchorEditor')]
    if not current_animation_catalog:
        current_map_records=[current_page_record for current_page_record in validated_page_records if current_page_record['category'] in ('field-map-review','town-map-review')]
        if current_map_records:
            current_map_entry={**current_map_records[0],'label':'맵 통합 검수','category':'map-review','description':'야외필드·도시맵·전투필드 · 선택 맵 리소스 로딩','reviewAliases':[current_page_record['id'] for current_page_record in current_map_records]}
            validated_page_records=[current_page_record for current_page_record in validated_page_records if current_page_record['category'] not in ('field-map-review','town-map-review')]+[current_map_entry]
    validated_page_records=[{**current_page_record,'category':'map-review','label':current_page_record['label'].replace(' · 도시맵 검수',' · 맵 검수')} if current_page_record['category'] in ('field-map-review','town-map-review') else current_page_record for current_page_record in validated_page_records]
    validated_page_records=[{**current_page_record,'category':'animation-tool','registeredAnimation':True} if current_page_record['category']=='animation' or current_page_record.get('anchorEditor') else current_page_record for current_page_record in validated_page_records]
    # 분류 접두어와 등록 순서 대신 도구 이름 오름차순을 모든 탐색에 공유한다.
    return sorted(validated_page_records,key=lambda current_page_record:(current_page_record['label'].casefold(),current_page_record['id']))

def filter_manager_page_records(page_record_values, search_text_value, category_name_value):
    search_token_values=search_text_value.casefold().split()
    return [current_page_record for current_page_record in page_record_values if (category_name_value=='all' or current_page_record['category']==category_name_value) and all(current_search_token in f"{current_page_record['label']} {current_page_record['description']} {current_page_record['id']}".casefold() for current_search_token in search_token_values)]

def create_tool_choice_values(page_record_values):
    """분류를 함께 표시해 긴 도구 목록에서도 찾기 쉽게 만든다."""
    return [
        (f"{CATEGORY_LABEL_VALUES.get(current_page_record['category'],current_page_record['category'])} · {current_page_record['label'].split(' · ')[0] if current_page_record['id'].startswith('map-review-') else current_page_record['label']}",current_page_record['id'])
        for current_page_record in page_record_values
    ]

def game_review_document_path(page_path):
    """게시한 게임 UI 번들의 독립 검수 문서 경로를 반환한다."""
    import re
    path = '/' + page_path.lstrip('/')
    return path if re.fullmatch(r'/ui-[a-f0-9]{16}/review/(?:design-system|battlefield-preview)\.html', path) else None


def resolve_management_page_path(current_page_record):
    """공용 메뉴·직접 진입이 같은 도구 주소와 맵 매개변수를 사용한다."""
    if current_page_record['id'] in REACT_REVIEW_PATHS:
        return REACT_REVIEW_PATHS[current_page_record['id']]
    if current_page_record.get('uiMode') in ('static', 'gradio-static'):
        document = game_review_document_path(current_page_record['path'])
        if document:
            return document
        return f'{MANAGEMENT_FRAME_PATH_PREFIX}static-review/?review={quote(current_page_record["id"],safe="")}'
    if current_page_record.get('uiMode') in ('archive', 'react', 'gradio'):
        current_application_name=current_page_record.get('frameIdentifier') or MANAGEMENT_FRAME_IDENTIFIER_VALUES.get(current_page_record['id'],current_page_record['id'])
        if current_application_name in NATIVE_MANAGEMENT_APPLICATIONS:
            current_query_suffix=current_page_record.get('frameQuery')
            return f'{MANAGEMENT_FRAME_PATH_PREFIX}{current_application_name}/'+(f'?{current_query_suffix}' if current_query_suffix else '')
    return None


def serialize_manager_navigation(page_record_values):
    return json.dumps([{**current_page_record,'nativePath':resolve_management_page_path(current_page_record)} for current_page_record in page_record_values],ensure_ascii=False).replace('<','\\u003c')

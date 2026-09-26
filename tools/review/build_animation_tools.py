"""현재 제공하는 애니메이션 관리 페이지를 등록한다."""


def build_animation_tools(output):
    records=[]
    records.append({'id':'anny-attribute-renderer','label':'Anny 속성 렌더러','path':'/anny-attributes/','anchorEditor':False,'category':'animation-tool','description':'나이·체중·키와 몸통·어깨·다리 로컬 속성의 렌더 입력 검토'})
    records.append({'id':'momask-generator','label':'MoMask 모션 생성기','path':'/momask-generator/','anchorEditor':False,'category':'animation-tool','uiMode':'gradio','description':'Gradio · 고정 포즈 스크립트 · 방향 선택 · 생성 로그·취소·결과 재생'})
    records.append({'id':'character-animation','label':'캐릭터 애니메이션 생성기','path':'/character-animation/','anchorEditor':False,'category':'animation-tool','uiMode':'gradio','description':'Gradio · 모션 에셋 · 캐릭터 레퍼런스 · 방향 선택 · 생성 이력과 재생'})
    records.append({'id':'sprite-editor','label':'스프라이트 정규화 편집기','path':'/character-animation/sprite-editor','anchorEditor':False,'category':'animation-tool','uiMode':'gradio','description':'Gradio · 생성 ID · 프레임 정렬 · 중심·바닥·머리 가이드 · 프레임 재생 · 시트 내보내기'})
    return records

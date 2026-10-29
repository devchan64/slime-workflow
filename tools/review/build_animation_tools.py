"""현재 제공하는 애니메이션 관리 페이지를 등록한다."""


def build_animation_tools(output):
    records=[]
    records.append({'id':'animation-separation','label':'캐릭터 레퍼런스 복장 분리 생성','path':'/animation-separation/','anchorEditor':False,'category':'image-generation','uiMode':'gradio','description':'Qwen 2.1 · 신체 베이스·복장 독립 생성 · 참조 이미지 1장 분리'})
    records.append({'id':'sprite-editor-v2','label':'스프라이트 정규화 편집기 v2','path':'/character-animation/sprite-editor-v2','anchorEditor':False,'category':'animation-tool','uiMode':'gradio','description':'참조·개별 프레임 등록 · 얼굴·신체 비교 · 384/256 · 수정 이력·GIF'})
    return records

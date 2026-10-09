"""현재 제공하는 애니메이션 관리 페이지를 등록한다."""


def build_animation_tools(output):
    records=[]
    records.append({'id':'anny-landmarks','label':'ANNY 해부학 기준점 검수','path':'/management/frame/anny-landmarks/','anchorEditor':False,'category':'animation-tool','uiMode':'gradio','description':'neutral_v4 · 후보 기준점·기하 축 검수 · 승인·리타기팅 미적용'})
    records.append({'id':'hy-motion-generator','label':'HY-Motion 모션 생성기','path':'/hy-motion-generator/','anchorEditor':False,'category':'animation-tool','uiMode':'gradio','description':'Lite · 원본 모션 · 방향별 미리보기 · 로그·이력·취소·재개'})
    records.append({'id':'anny-attribute-renderer','label':'Anny 속성 렌더러','path':'/anny-attributes/','anchorEditor':False,'category':'animation-tool','uiMode':'gradio','description':'Gradio · 나이·체중·키와 몸통·어깨·다리 로컬 속성의 렌더 입력 검토'})
    records.append({'id':'animation-separation','label':'캐릭터 레퍼런스 복장 분리 생성','path':'/animation-separation/','anchorEditor':False,'category':'image-generation','uiMode':'gradio','description':'Qwen 2.1 · 신체 베이스·복장 독립 생성 · 참조 이미지 1장 분리'})
    records.append({'id':'sprite-editor-v2','label':'스프라이트 정규화 편집기 v2','path':'/character-animation/sprite-editor-v2','anchorEditor':False,'category':'animation-tool','uiMode':'gradio','description':'참조·개별 프레임 등록 · 얼굴·신체 비교 · 384/256 · 수정 이력·GIF'})
    return records

"""현재 제공하는 애니메이션 관리 페이지를 등록한다."""


def build_animation_tools(output):
    records=[]
    records.append({'id':'sprite-sheet-editor','label':'스프라이트 시트 편집기','path':'/management/frame/sprite-sheet-editor/','anchorEditor':False,'category':'animation-tool','uiMode':'gradio','description':'프레임 크롭 · 앵커 정렬 · 시트와 좌표맵 출력'})
    return records

"""브라우저 프레임 재생기에 필요한 미디어 배치만 공유한다."""

# 프레임 비율과 탐색 영역만 지정한다. 입력·버튼·색상·테마는 덮어쓰지 않는다.
BROWSER_FRAME_PLAYER_STYLES='img{max-width:100%;max-height:560px;object-fit:contain}.frame-comparison-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))}.frame-comparison-grid img{width:100%}#seek{width:100%}'


def apply_browser_player_layout(current_player_document):
    """재생 문서의 명시적인 미디어 배치 자리에 공용 규칙을 넣는다."""
    if current_player_document.count('__FRAME_PLAYER_LAYOUT__')!=1:
        raise ValueError('프레임 재생기 배치 자리표시는 한 개여야 합니다.')
    return current_player_document.replace('__FRAME_PLAYER_LAYOUT__',BROWSER_FRAME_PLAYER_STYLES)

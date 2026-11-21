"""공유 앵커 편집 코드를 Gradio 문서의 독립 캔버스에 연결한다."""
import json
from pathlib import Path

ANCHOR_EDITOR_SOURCE_DIRECTORY = Path(__file__).parents[1] / 'shared/animation-anchor-editor'


def read_native_anchor_loader():
    """게시 문서에서는 JSON만 읽고 실행 코드는 Git의 공용 구현을 사용한다."""
    current_template_source = (ANCHOR_EDITOR_SOURCE_DIRECTORY / 'editor.html').read_text()
    current_markup_start = current_template_source.index('<header>')
    current_markup_end = current_template_source.index('</main>') + len('</main>')
    current_editor_markup = current_template_source[current_markup_start:current_markup_end]
    current_editor_source = (ANCHOR_EDITOR_SOURCE_DIRECTORY / 'editor.js').read_text()
    current_loader_source = (ANCHOR_EDITOR_SOURCE_DIRECTORY / 'native-loader.js').read_text()
    return ('const currentAnchorMarkup=' + json.dumps(current_editor_markup, ensure_ascii=False).replace('<', '\\u003c') + ';\n'
            'const createNativeAnchorRuntime=(document,window,requestAnimationFrame,fetch)=>{\n' + current_editor_source + '\nreturn window;\n};\n' + current_loader_source)

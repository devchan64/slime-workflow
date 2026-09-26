"""관리도구 UI 파일의 도메인별 경로. 외부 URL은 변경하지 않는다."""
from pathlib import Path

REVIEW_UI_DIRECTORY=Path(__file__).resolve().parent
REVIEW_UI_FILES={'terrain-layout.html':'ui/game/terrain-layout.html','tile-generation.js':'ui/tile/tile-generation.js','management.css':'ui/shared/management.css','generation-history.js': 'ui/shared/generation-history.js', 'generation-progress.js': 'ui/shared/generation-progress.js', 'generation-studio.css': 'ui/shared/generation-studio.css', 'management-workflow.js': 'ui/shared/management-workflow.js', 'review-ui.css': 'ui/shared/review-ui.css', 'character-animation.html': 'ui/character_animation/character-animation.html', 'character-animation.js': 'ui/character_animation/character-animation.js', 'character-animation-assets.js': 'ui/character_animation/character-animation-assets.js', 'anny-attributes.html': 'ui/anny/anny-attributes.html', 'anny-attributes.css': 'ui/anny/anny-attributes.css', 'anny-mesh-viewer.js': 'ui/anny/anny-mesh-viewer.js', 'momask-studio.css': 'ui/momask/momask-studio.css', 'image-generation.html': 'ui/image/image-generation.html', 'three-reference-generation.html': 'ui/image/three-reference-generation.html', 'isloon-map-review.html': 'ui/map/isloon-map-review.html', 'tile-review.html': 'ui/map/tile-review.html', 'frame-manager.html': 'ui/asset_review/frame-manager.html', 'pose-transfer-review.html': 'ui/asset_review/pose-transfer-review.html', 'walk-sheet.html': 'ui/asset_review/walk-sheet.html'}

def resolve_review_ui_asset(asset_file_name):
    if asset_file_name not in REVIEW_UI_FILES:
        raise ValueError("등록되지 않은 관리도구 UI 파일")
    return REVIEW_UI_DIRECTORY/REVIEW_UI_FILES[asset_file_name]


def read_review_shared_styles():
    """단독 HTML 검수에서도 전역 스타일과 검수 배치를 함께 제공한다."""
    return resolve_review_ui_asset('management.css').read_text()+'\n'+resolve_review_ui_asset('review-ui.css').read_text()

"""Gradio 관리 페이지에서 사용하는 동일 포트 전역 탐색 링크."""
from html import escape

MANAGEMENT_NAVIGATION_RECORDS=(
    ('관리 메뉴','/management/'),
    ('MoMask','/momask-generator/'),
    ('캐릭터 애니메이션','/character-animation/'),
    ('Qwen 2512','/image-generation/'),
    ('Qwen 2511','/image-generation-2511/'),
    ('타일 에셋','/tile-map-generator/'),
)

def build_management_navigation(current_path_value):
    link_html_values=[]
    for link_label_value,link_path_value in MANAGEMENT_NAVIGATION_RECORDS:
        current_attribute_value=' aria-current="page"' if link_path_value==current_path_value else ''
        link_html_values.append(f'<a href="{escape(link_path_value,quote=True)}"{current_attribute_value}>{escape(link_label_value)}</a>')
    return '<nav class="management-global-navigation" aria-label="관리도구 메뉴">'+' '.join(link_html_values)+'</nav>'

MANAGEMENT_NAVIGATION_STYLES='''.management-global-navigation{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px}.management-global-navigation a{padding:7px 10px;border:1px solid #40516a;border-radius:8px;color:#dbeafe;text-decoration:none;background:#192230}.management-global-navigation a[aria-current="page"]{background:#315482;border-color:#93baff;color:#fff;font-weight:700}'''

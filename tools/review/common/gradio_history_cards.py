"""Gradio Gallery를 확장한 공용 카드 갤러리."""
from datetime import datetime
from collections import OrderedDict
from threading import Lock
from time import monotonic
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo
import gradio as gr
from gradio.data_classes import DeveloperPath
from PIL import Image
from tools.review.common.gradio_results import load_gallery_image_values


_thumbnail_cache_values = OrderedDict()
_thumbnail_cache_lock = Lock()
_THUMBNAIL_CACHE_SECONDS = 30
_THUMBNAIL_CACHE_LIMIT = 128


def load_cached_history_thumbnail(current_image_address, server_base_address):
    """짧게 보관한 카드 이미지를 재사용하고 실패는 보관하지 않는다."""
    current_cache_key = (server_base_address, current_image_address)
    with _thumbnail_cache_lock:
        current_cache_entry = _thumbnail_cache_values.get(current_cache_key)
        if current_cache_entry and monotonic() - current_cache_entry[0] < _THUMBNAIL_CACHE_SECONDS:
            _thumbnail_cache_values.move_to_end(current_cache_key)
            return current_cache_entry[1].copy()
        _thumbnail_cache_values.pop(current_cache_key, None)
    current_thumbnail_image = load_gallery_image_values([(current_image_address, '')], server_base_address, timeout_seconds=1)[0][0]
    current_thumbnail_image.thumbnail((320, 320), Image.Resampling.LANCZOS)
    with _thumbnail_cache_lock:
        _thumbnail_cache_values[current_cache_key] = (monotonic(), current_thumbnail_image.copy())
        _thumbnail_cache_values.move_to_end(current_cache_key)
        while len(_thumbnail_cache_values) > _THUMBNAIL_CACHE_LIMIT:
            _thumbnail_cache_values.popitem(last=False)
    return current_thumbnail_image


class CardGallery(gr.Gallery):
    """Gradio Gallery 소스에 정보 필드를 확장한 카드 격자."""

    TEMPLATE_DIR = DeveloperPath('card_gallery_templates')
    DEFAULT_COLUMNS = 4
    DEFAULT_ROWS = 2
    DEFAULT_PAGE_SIZE = DEFAULT_COLUMNS * DEFAULT_ROWS

    def __init__(self, *current_component_args, **current_component_options):
        current_component_options.setdefault('columns', self.DEFAULT_COLUMNS)
        current_component_options.setdefault('rows', self.DEFAULT_ROWS)
        current_component_options.setdefault('object_fit', 'contain')
        current_component_options.setdefault('height', 'auto')
        current_component_options.setdefault('allow_preview', False)
        current_component_options.setdefault('fit_columns', False)
        current_component_options.setdefault('interactive', False)
        current_component_options.setdefault('buttons', [])
        super().__init__(*current_component_args, **current_component_options)

    def get_config(self, cls=None):
        return super().get_config(gr.Gallery)


def build_card_gallery_panel():
    """갤러리와 탐색 도구를 같은 패널 레이아웃에 배치한다."""
    return gr.Column(variant='panel')


def build_card_gallery_pagination(initial_notice_text, initial_page_count=1, show_refresh_button=False):
    """카드 갤러리의 공용 페이지 크기·번호·이전/다음 UI를 만든다."""
    with gr.Row():
        with gr.Column(scale=0, min_width=210):
            with gr.Row(equal_height=True):
                current_refresh_button = gr.Button('새로고침', variant='secondary', size='md', scale=0, min_width=80) if show_refresh_button else None
                current_page_size = gr.Dropdown(choices=[(f'{current_size_value}개씩', current_size_value) for current_size_value in (4, 8, 16, 32)],
                    value=CardGallery.DEFAULT_PAGE_SIZE, label='페이지당 항목', show_label=False, container=False, scale=0, min_width=95, interactive=True)
        with gr.Column(scale=1, min_width=480):
            with gr.Row():
                current_page_notice = gr.Markdown(initial_notice_text, scale=1, min_width=200)
                with gr.Column(scale=0, min_width=260):
                    with gr.Row(equal_height=True):
                        current_previous_button = gr.Button('← 이전', size='md', scale=0, min_width=72, interactive=False)
                        current_page_number = gr.Number(value=1, minimum=1, precision=0,
                            label='페이지 이동 (입력 후 Enter)', show_label=False, container=False, scale=0, min_width=64,
                            interactive=initial_page_count > 1, elem_classes=['generation-history-page'])
                        current_next_button = gr.Button('다음 →', size='md', scale=0, min_width=72, interactive=initial_page_count > 1)
    return current_refresh_button, current_page_size, current_page_notice, current_previous_button, current_page_number, current_next_button


def format_history_timestamp(current_time_value):
    if not isinstance(current_time_value,str) or not current_time_value.strip():
        return '기록 없음'
    try:
        current_datetime_value=datetime.fromisoformat(current_time_value.replace('Z','+00:00'))
        if current_datetime_value.tzinfo is not None:
            current_datetime_value=current_datetime_value.astimezone(ZoneInfo('Asia/Seoul'))
        return current_datetime_value.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return '기록 없음'


def describe_history_completion_time(current_history_record):
    current_status_record=current_history_record.get('status')
    current_status_name=current_status_record.get('status') if isinstance(current_status_record,dict) else current_status_record
    if current_status_name!='completed':
        return '완료 시각: 미완료'
    if not isinstance(current_status_record,dict):
        current_status_record={}
    current_completion_value=current_status_record.get('completed_at') or current_history_record.get('completed_at')
    if current_completion_value and format_history_timestamp(current_completion_value)!='기록 없음':
        return '완료 시각: '+format_history_timestamp(current_completion_value)
    current_metrics_record=current_status_record.get('metrics')
    if isinstance(current_metrics_record,dict) and current_metrics_record.get('status')=='completed':
        current_observed_time=format_history_timestamp(current_metrics_record.get('updated_at'))
        if current_observed_time!='기록 없음':
            return '완료 관측 시각: '+current_observed_time
    return '완료 시각: 기록 없음'


def render_generation_history_cards(current_history_records, current_table_rows, selected_history_identifier=None, show_thumbnail_column=True, server_base_address=''):
    def load_history_thumbnail(current_record_value):
        current_image_path=current_record_value.get('image') or (current_record_value.get('status',{}).get('image') if isinstance(current_record_value.get('status'),dict) else None)
        if show_thumbnail_column and isinstance(current_image_path,str) and current_image_path.startswith('/') and not current_image_path.startswith('//'):
            try:
                current_thumbnail_image=load_cached_history_thumbnail(server_base_address.rstrip('/')+current_image_path,server_base_address)
                return current_thumbnail_image, None
            except (OSError,ValueError):
                return None, '썸네일 조회 실패 · 새로고침으로 재시도'
        return None, '이미지 없음' if show_thumbnail_column else None

    # 썸네일을 병렬로 읽고 카드 표시 크기에 맞춰 전송량을 줄인다.
    with ThreadPoolExecutor(max_workers=min(8,max(1,len(current_history_records)))) as current_thumbnail_pool:
        current_thumbnail_values=list(current_thumbnail_pool.map(load_history_thumbnail,current_history_records))
    current_card_values=[]
    for current_record_value,current_table_row,(current_thumbnail_value,current_thumbnail_notice) in zip(current_history_records,current_table_rows,current_thumbnail_values):
        current_status_text,current_created_text,current_settings_text,current_progress_text,current_job_identifier=current_table_row
        current_image_value=current_thumbnail_value if current_thumbnail_value is not None else Image.new('RGB',(128,128),(75,75,80))
        current_completion_text=describe_history_completion_time(current_record_value)
        current_caption_text=f'상태: {current_status_text}\n생성 시각: {current_created_text}\n{current_completion_text}\n설정: {current_settings_text}'
        if current_thumbnail_notice:
            current_caption_text+='\n'+current_thumbnail_notice
        if not show_thumbnail_column:
            current_caption_text='__card_no_thumbnail__\n'+current_caption_text
        if current_progress_text:
            current_caption_text+='\n진행: '+current_progress_text
        current_card_values.append((current_image_value,current_caption_text+'\n생성 ID: '+current_job_identifier))
    return current_card_values


def build_generation_history_cards():
    return CardGallery(value=[],show_label=False,elem_id='generation-history-cards')

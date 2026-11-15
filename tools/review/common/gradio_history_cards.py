"""Gradio Gallery를 확장한 공용 카드 갤러리."""
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo
import gradio as gr
from gradio.data_classes import DeveloperPath
from PIL import Image
from tools.review.common.gradio_results import load_gallery_image_values


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
                return load_gallery_image_values([(server_base_address.rstrip('/')+current_image_path,'')],server_base_address,timeout_seconds=1)[0][0], None
            except (OSError,ValueError):
                return None, '썸네일 조회 실패 · 새로고침으로 재시도'
        return None, '이미지 없음'

    # 1枚の遅いサムネイルがページ全体や他のサムネイルを待たせない。
    with ThreadPoolExecutor(max_workers=min(8,max(1,len(current_history_records)))) as current_thumbnail_pool:
        current_thumbnail_values=list(current_thumbnail_pool.map(load_history_thumbnail,current_history_records))
    current_card_values=[]
    for current_record_value,current_table_row,(current_thumbnail_value,current_thumbnail_notice) in zip(current_history_records,current_table_rows,current_thumbnail_values):
        current_status_text,current_created_text,current_settings_text,current_progress_text,current_job_identifier=current_table_row
        current_image_value=current_thumbnail_value if current_thumbnail_value is not None else Image.new('RGB',(128,128),(75,75,80))
        current_image_available=current_thumbnail_value is not None
        current_completion_text=describe_history_completion_time(current_record_value)
        current_caption_text=f'상태: {current_status_text}\n생성 시각: {current_created_text}\n{current_completion_text}\n설정: {current_settings_text}'
        if not current_image_available:
            current_caption_text+='\n'+current_thumbnail_notice
        if current_progress_text:
            current_caption_text+='\n진행: '+current_progress_text
        current_card_values.append((current_image_value,current_caption_text+'\n생성 ID: '+current_job_identifier))
    return current_card_values


def build_generation_history_cards():
    return CardGallery(value=[],label='카드 갤러리',elem_id='generation-history-cards')

"""Gradio Gallery를 확장한 공용 카드 갤러리."""
from datetime import datetime
from zoneinfo import ZoneInfo
import gradio as gr
from PIL import Image
from tools.review.common.gradio_results import load_gallery_image_values

from gradio.events import Dependency

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
    from typing import Callable, Literal, Sequence, Any, TYPE_CHECKING
    from gradio.blocks import Block
    if TYPE_CHECKING:
        from gradio.components import Timer
        from gradio.components.base import Component


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
    current_card_values=[]
    for current_record_value,current_table_row in zip(current_history_records,current_table_rows):
        current_status_text,current_created_text,current_settings_text,current_progress_text,current_job_identifier=current_table_row
        current_image_path=current_record_value.get('image') or (current_record_value.get('status',{}).get('image') if isinstance(current_record_value.get('status'),dict) else None)
        current_image_value=Image.new('RGB',(128,128),(75,75,80))
        current_image_available=False
        if show_thumbnail_column and isinstance(current_image_path,str) and current_image_path.startswith('/') and not current_image_path.startswith('//'):
            try:
                current_image_value=load_gallery_image_values([(server_base_address.rstrip('/')+current_image_path,'')],server_base_address)[0][0]
                current_image_available=True
            except (OSError,ValueError):
                pass
        current_completion_text=describe_history_completion_time(current_record_value)
        current_caption_text=f'{current_status_text} · '+('' if current_image_available else '이미지 없음 · ')+f'생성 {current_created_text} · {current_completion_text} · {current_settings_text}'
        if current_progress_text:
            current_caption_text+=' · 진행: '+current_progress_text
        current_card_values.append((current_image_value,current_caption_text+' · ID: '+current_job_identifier))
    return current_card_values


def build_generation_history_cards():
    return CardGallery(value=[],label='카드 갤러리',elem_id='generation-history-cards')
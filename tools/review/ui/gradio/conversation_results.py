"""운영 대화의 읽기 전용 결과 표."""
from html import escape

import gradio as gr

from ..shared.conversation_results import generation_history_table


def conversation_result_table(title, summary, columns, rows):
    headings = "".join(f'<th scope="col">{escape(column)}</th>' for column in columns)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in row) + "</tr>" for row in rows)
    if not body:
        body = f'<tr><td colspan="{len(columns)}">조회된 항목이 없습니다.</td></tr>'
    return gr.HTML(f'<section class="hermes-result-table"><strong>{escape(title)}</strong>'
                   f'<div>{escape(summary)}</div><table aria-label="{escape(title, quote=True)}">'
                   f'<thead><tr>{headings}</tr></thead><tbody>{body}</tbody></table></section>', render=False)


def generation_history_component(activity):
    table = generation_history_table(activity)
    return conversation_result_table(**table) if table is not None else None

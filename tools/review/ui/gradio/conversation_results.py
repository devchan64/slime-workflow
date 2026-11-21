"""운영 대화의 읽기 전용 결과 표."""
from html import escape
import re

import gradio as gr


def conversation_result_table(title, summary, columns, rows):
    headings = "".join(f'<th scope="col">{escape(column)}</th>' for column in columns)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in row) + "</tr>" for row in rows)
    if not body:
        body = f'<tr><td colspan="{len(columns)}">조회된 항목이 없습니다.</td></tr>'
    return gr.HTML(f'<section class="hermes-result-table"><strong>{escape(title)}</strong>'
                   f'<div>{escape(summary)}</div><table aria-label="{escape(title, quote=True)}">'
                   f'<thead><tr>{headings}</tr></thead><tbody>{body}</tbody></table></section>', render=False)


def generation_history_component(activity):
    page = activity.get("source_history_page")
    if not isinstance(page, dict):
        # 기존 게이트웨이가 제공하는 정형 요약도 같은 표로 표시한다.
        lines = (activity.get("source_history_summary") or "").splitlines()
        header = re.fullmatch(r"([a-z0-9-]+) 생성 이력 · 총 (\d+)건 · 조회된 (\d+)건", lines[0]) if lines else None
        if not header or int(header[3]) != len(lines) - 1:
            return None
        rows = []
        for line in lines[1:]:
            match = re.fullmatch(r"- `([A-Za-z0-9_-]+)` · (.+)", line)
            if not match:
                return None
            rows.append(match.groups())
        service, total = header[1], int(header[2])
    else:
        service, total = page["service"], page["total"]
        rows = [(row["id"], row["status"]) for row in page["rows"]]
    return conversation_result_table(f"{service} 생성 이력", f"전체 {total}건 · 이번 조회 {len(rows)}건",
                                     ("작업 ID", "상태"), rows)

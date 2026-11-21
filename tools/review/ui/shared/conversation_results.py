"""헤르메스 대화 UI에서 공통으로 사용하는 생성 이력 표 데이터."""
import re


def generation_history_table(activity):
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
    return {
        "title": f"{service} 생성 이력",
        "summary": f"전체 {total}건 · 이번 조회 {len(rows)}건",
        "columns": ["작업 ID", "상태"],
        "rows": [list(row) for row in rows],
    }

"""명시된 배치와 일부 조건의 번역 누락 가능성을 검사한다."""
import re

_NUMBER_VALUES = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5}
_NUMBER_PATTERN = r'(?:\d+|one|two|three|four|five|一|二|两|三|四|五)'


def _read_layout_number(quality_number_text):
    quality_lower_text = quality_number_text.lower()
    return int(quality_lower_text) if quality_lower_text.isdigit() else _NUMBER_VALUES[quality_lower_text]


def _extract_target_layout(quality_result_text, quality_target_language):
    quality_unit_pattern = r'(?:columns?|cols?|rows?)' if quality_target_language == 'en' else r'(?:列|行)'
    quality_pattern_text = rf'(?<![\w])({_NUMBER_PATTERN})\s*({quality_unit_pattern})' if quality_target_language == 'en' else rf'({_NUMBER_PATTERN})\s*({quality_unit_pattern})'
    quality_matches = list(re.finditer(quality_pattern_text, quality_result_text, re.IGNORECASE))
    quality_pairs = []
    for quality_first_match, quality_second_match in zip(quality_matches, quality_matches[1:]):
        if quality_second_match.start() - quality_first_match.end() > 35:
            continue
        quality_units = [quality_first_match.group(2).lower(), quality_second_match.group(2).lower()]
        quality_columns = [quality_unit.startswith(('col', '列')) for quality_unit in quality_units]
        if quality_columns[0] == quality_columns[1]:
            continue
        quality_numbers = [_read_layout_number(quality_first_match.group(1)), _read_layout_number(quality_second_match.group(1))]
        quality_pairs.append((quality_numbers[quality_columns.index(True)], quality_numbers[quality_columns.index(False)]))
    return quality_pairs


def inspect_translation_quality(quality_source_text, quality_result_text, quality_target_language):
    """검증 가능한 근거만 제시하며, 미확인은 누락 확정이나 정상 판정이 아니다."""
    quality_check_records = []
    quality_source_layouts = re.findall(r'(\d+)\s*열\s*[×xX*]\s*(\d+)\s*행', quality_source_text)
    if quality_source_layouts:
        quality_source_pairs = {(int(quality_columns), int(quality_rows)) for quality_columns, quality_rows in quality_source_layouts}
        quality_target_pairs = _extract_target_layout(quality_result_text, quality_target_language)
        quality_expected_text = ', '.join(f'{quality_columns}열×{quality_rows}행' for quality_columns, quality_rows in sorted(quality_source_pairs))
        quality_observed_text = ', '.join(f'{quality_columns}열×{quality_rows}행' for quality_columns, quality_rows in quality_target_pairs) or '인식하지 못함'
        if len(quality_source_pairs) == 1 and len(quality_target_pairs) == 1:
            quality_expected_pair = next(iter(quality_source_pairs))
            quality_observed_pair = quality_target_pairs[0]
            if quality_expected_pair == quality_observed_pair:
                quality_status_text = 'matched'
            elif quality_expected_pair[0] != quality_expected_pair[1] and quality_expected_pair == quality_observed_pair[::-1]:
                quality_status_text = 'reversed'
            else:
                quality_status_text = 'review'
        else:
            quality_status_text = 'review'
        quality_check_records.append({'source': quality_expected_text, 'target': quality_observed_text, 'status': quality_status_text, 'source_ref': '배치 수량 규칙'})
    quality_condition_patterns = [
        ('모든 방향에서', {'en': r'\b(?:all|every)\s+(?:the\s+)?(?:views?|directions?|angles?)\b', 'zh-CN': r'(?:所有|全部|各个?|每个?)(?:的)?(?:方向|角度|视角|方位)'}),
        ('눈의 크기와 간격', {'en': r'\beye(?:s|\s*\w+){0,3}[^.。；;]{0,35}\b(?:size|sizes)\b[^.。；;]{0,35}\b(?:spacing|distance|gap)\b', 'zh-CN': r'眼(?:睛|部)?[^。；;]{0,15}大小[^。；;]{0,15}(?:间距|距离|间隔)'}),
        ('투명 배경', {'en': r'\btransparent\s+(?:background|sheet|png)\b|\btransparent\b[^.。;]{0,35}\bbackground\b', 'zh-CN': r'透明(?:的)?背景|背景(?:是|为)?透明'}),
        ('4프레임', {'en': r'\b(?:4|four)\s+(?:animation\s+)?frames?\b', 'zh-CN': r'(?:4|四)\s*帧'}),
        ('양발 접지선', {'en': r'\b(?:both\s+feet|feet|foot)\b[^.。;]{0,40}\b(?:ground|contact|placement|position)\b|\b(?:placement|position|contact)\b[^.。;]{0,40}\b(?:both\s+feet|feet|foot)\b', 'zh-CN': r'(?:双脚|两脚|脚部)[^。；;]{0,20}(?:接触|接地|位置|固定)'}),
        ('얼굴 비율 참조가 제공되면', {'en': r'\b(?:if|when)\b[^.。;]{0,100}\b(?:reference|provided)\b', 'zh-CN': r'(?:如果|若|当)[^。；;]{0,40}(?:参考|提供)'}),
    ]
    for quality_source_phrase, quality_target_patterns in quality_condition_patterns:
        if quality_source_phrase not in quality_source_text:
            continue
        quality_found_value = bool(re.search(quality_target_patterns[quality_target_language], quality_result_text, re.IGNORECASE))
        quality_check_records.append({'source': quality_source_phrase, 'target': '대응 표현 발견' if quality_found_value else '대응 표현을 확인하지 못함', 'status': 'matched' if quality_found_value else 'review', 'source_ref': '핵심 조건 표현 규칙'})
    quality_negation_rules = [
        ('머리 크기', r'머리 크기와 다리 길이를 바꾸지 않', {'en': r'\bhead\s+size\b', 'zh-CN': r'头(?:部)?(?:的)?大小'}),
        ('다리 길이', r'머리 크기와 다리 길이를 바꾸지 않', {'en': r'\bleg\s+length\b', 'zh-CN': r'腿(?:的)?长度'}),
        ('문자 금지', r'문자[·ㆍ,、와과 ]+격자선은? 넣지 않', {'en': r'\b(?:text|letters?|writing)\b', 'zh-CN': r'文字|文本|字母'}),
        ('격자선 금지', r'문자[·ㆍ,、와과 ]+격자선은? 넣지 않', {'en': r'\bgrid\s*lines?\b', 'zh-CN': r'网格线|网格'}),
        ('과장 금지', r'과장 없이', {'en': r'\bexaggerat(?:ion|e|ed|ing)\b', 'zh-CN': r'夸张'}),
    ]
    quality_target_clauses = re.split(r'[.。!！?？;；]|\b(?:but|however)\b|但是|但(?!是)', quality_result_text, flags=re.IGNORECASE)
    quality_negative_pattern = {'en': r"\b(?:no|not|never|without|avoid|avoiding|prohibit|prohibited|don't|dont)\b", 'zh-CN': r'不|无|没有|避免|禁止|勿|别'}[quality_target_language]
    quality_matched_source_patterns = []
    for quality_source_label, quality_source_pattern, quality_target_patterns in quality_negation_rules:
        if not re.search(quality_source_pattern, quality_source_text):
            continue
        quality_matched_source_patterns.append(quality_source_pattern)
        quality_relevant_clauses = [quality_clause for quality_clause in quality_target_clauses if re.search(quality_target_patterns[quality_target_language], quality_clause, re.IGNORECASE)]
        quality_negative_clauses = [quality_clause for quality_clause in quality_relevant_clauses if re.search(quality_negative_pattern, quality_clause, re.IGNORECASE)]
        quality_has_evidence = bool(quality_negative_clauses) and len(quality_negative_clauses) == len(quality_relevant_clauses)
        quality_check_records.append({'source': quality_source_label, 'target': '대상과 부정 표현 발견 · 적용 관계 확인 필요' if quality_has_evidence else '대상 또는 부정 표현을 확인하지 못함', 'status': 'review', 'source_ref': '부정 표현 후보 규칙'})
    for quality_source_clause in re.split(r'[.。!！?？;；\n]', quality_source_text):
        if re.search(r'(?:제공되면|있으면|없으면|필요하면|경우(?:에는|에|라면|는)?)', quality_source_clause) and not any(quality_phrase in quality_source_clause for quality_phrase, _ in quality_condition_patterns):
            quality_check_records.append({'source': quality_source_clause.strip(), 'target': '조건의 대응 관계 자동 판정 미지원', 'status': 'review', 'source_ref': '미지원 조건문'})
        quality_remaining_clause = quality_source_clause
        for quality_source_pattern in quality_matched_source_patterns:
            quality_remaining_clause = re.sub(quality_source_pattern, '', quality_remaining_clause)
        if not re.search(r'(?:지\s*않|지\s*말|없이|없(?:는|다|어야)|금지|아닌|아니다)', quality_remaining_clause):
            continue
        quality_check_records.append({'source': quality_source_clause.strip(), 'target': '대응 부정 표현 자동 판정 미지원', 'status': 'review', 'source_ref': '미지원 부정문'})
    return quality_check_records

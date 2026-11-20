"""관리 명령 조사표가 현재 서비스 등록 명령을 빠짐없이 열거하는지 검사한다."""
import argparse
from collections import Counter
from pathlib import Path
import re
import sys

from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS


def inspect_hermes_command_coverage(current_audit_text):
    current_sections_map={}
    for current_section_match in re.finditer(r'^## ([^\n]+)\n(.*?)(?=^## |\Z)',current_audit_text,re.MULTILINE|re.DOTALL):
        current_service_name,current_section_text=current_section_match.groups()
        if current_service_name in current_sections_map:raise ValueError('중복 서비스 제목: '+current_service_name)
        current_sections_map[current_service_name]=current_section_text
    current_missing_rows=[]
    current_obsolete_rows=[]
    current_duplicate_rows=[]
    current_unregistered_sections=sorted(current_section_name for current_section_name,current_section_text in current_sections_map.items() if current_section_name not in MANAGEMENT_SERVICE_COMMANDS and re.search(r'^\| `[^`]+` \|',current_section_text,re.MULTILINE))
    for current_service_name,current_command_names in MANAGEMENT_SERVICE_COMMANDS.items():
        current_row_names=re.findall(r'^\| `([^`]+)` \|',current_sections_map.get(current_service_name,''),re.MULTILINE)
        current_row_counts=Counter(current_row_names)
        current_missing_rows.extend((current_service_name,current_command_name) for current_command_name in current_command_names if current_command_name not in current_row_counts)
        current_obsolete_rows.extend((current_service_name,current_command_name) for current_command_name in sorted(set(current_row_names)-set(current_command_names)))
        current_duplicate_rows.extend((current_service_name,current_command_name) for current_command_name,current_count_value in current_row_counts.items() if current_count_value>1)
    return {'services':len(MANAGEMENT_SERVICE_COMMANDS),'commands':sum(map(len,MANAGEMENT_SERVICE_COMMANDS.values())),'missing':current_missing_rows,'obsolete':current_obsolete_rows,'duplicates':current_duplicate_rows,'unregistered_sections':current_unregistered_sections}


def run_hermes_audit_check():
    current_argument_parser=argparse.ArgumentParser(description='조사표의 등록 명령 이름 누락·초과·중복을 확인한다. 명령 실행이나 계약 검증은 하지 않는다.')
    current_argument_parser.add_argument('--audit',type=Path,required=True,help='관리 명령별 조사 Markdown 경로')
    current_argument_values=current_argument_parser.parse_args()
    current_coverage_record=inspect_hermes_command_coverage(current_argument_values.audit.read_text(encoding='utf-8'))
    print('서비스 {services}개 · 명령 {commands}개'.format(**current_coverage_record))
    for current_category_name in ('missing','obsolete','duplicates'):
        for current_service_name,current_command_name in current_coverage_record[current_category_name]:print(current_category_name+': '+current_service_name+' / '+current_command_name)
    for current_section_name in current_coverage_record['unregistered_sections']:print('unregistered_service: '+current_section_name)
    return 1 if any(current_coverage_record[current_category_name] for current_category_name in ('missing','obsolete','duplicates','unregistered_sections')) else 0


if __name__=='__main__':
    sys.exit(run_hermes_audit_check())

"""결과 경로가 없는 작업의 상태별 공용 안내."""

def describe_missing_generation_result(current_status_record, current_media_label):
    current_status_name = current_status_record.get('status')
    if current_status_name == 'completed':
        return f'완료 기록에 조회 가능한 {current_media_label} 결과가 없습니다. 기록 경로와 실행 로그를 확인하세요.'
    if current_status_name in ('failed', 'cancelled', 'interrupted'):
        return f'종료된 작업에 조회 가능한 {current_media_label} 결과가 없습니다. 작업 상태와 실행 로그를 확인하세요.'
    return f'생성 완료 후 {current_media_label} 결과와 다운로드를 표시합니다.'

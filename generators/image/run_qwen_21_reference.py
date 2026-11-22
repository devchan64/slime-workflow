"""폐기된 Qwen Image 2.1 작업자 호환 진입점."""


def execute_qwen_reference_worker():
    """기존 대기열 명령을 추론이나 파일 변경 전에 거절한다."""
    raise RuntimeError('Qwen 이미지 생성기는 폐기되었습니다.')


if __name__ == '__main__':
    execute_qwen_reference_worker()

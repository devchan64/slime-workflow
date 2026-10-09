"""폐기된 MoMask 리그 재렌더 명령의 호환 종료 진입점."""


def resume_render_frames(generation_job_path):
    raise ValueError('MoMask 생성기의 과거 작업 렌더 재개는 폐기되었습니다.')


if __name__ == '__main__':
    raise ValueError('MoMask 리그 재렌더 기능은 폐기되었습니다.')

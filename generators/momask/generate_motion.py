"""폐기된 MoMask 추론 진입점. 모델 준비·기록 생성 전에 거절한다."""


def execute_motion_attempt():
    raise ValueError('MoMask 모션 추론은 폐기되었습니다. HY-Motion을 사용하세요.')


if __name__ == '__main__':
    execute_motion_attempt()

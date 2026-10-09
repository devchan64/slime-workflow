"""폐기된 MoMask 생성 명령의 명시적 종료 진입점."""


def reject_retired_generation():
    raise ValueError('MoMask 포즈 생성기는 폐기되었습니다. HY-Motion을 사용하세요.')


if __name__ == '__main__':
    reject_retired_generation()

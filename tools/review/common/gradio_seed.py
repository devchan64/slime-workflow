"""생성 화면에서 공용으로 사용하는 무작위 Seed 선택."""
import secrets

RANDOM_SEED_UPPER_BOUND = 4294967296


def generate_random_seed_value():
    """게이트웨이가 허용하는 uint32 정수를 선택한다. 생성을 실행하지 않는다."""
    return secrets.randbelow(RANDOM_SEED_UPPER_BOUND)

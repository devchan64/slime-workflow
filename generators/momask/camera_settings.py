"""방향별 카메라 각도를 검증하고 같은 기준으로 투영·위치를 계산한다."""
import math

CAMERA_DIRECTION_NAMES = ('down_left', 'down_right', 'up_left', 'up_right')


def normalize_camera_angles(angle_values):
    if not isinstance(angle_values, dict):
        # 기존 단일각 CLI는 각 사분면의 0~90도 오프셋 의미를 유지한다.
        if type(angle_values) not in (int, float) or not math.isfinite(angle_values) or not 0 < angle_values < 90:
            raise ValueError('기존 단일 카메라 각도는 0도 초과 90도 미만이어야 합니다.')
        angle_values = {'down_left': angle_values, 'down_right': 360-angle_values,
                        'up_left': 180-angle_values, 'up_right': 180+angle_values}
    if set(angle_values) != set(CAMERA_DIRECTION_NAMES):
        raise ValueError('카메라 각도는 4방향을 모두 지정해야 합니다.')
    if any(type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value < 360 for value in angle_values.values()):
        raise ValueError('방향별 절대 방위각은 0도 이상 360도 미만이어야 합니다.')
    return dict(angle_values)


def camera_projection_angles(angle_values):
    return normalize_camera_angles(angle_values)


def camera_direction_positions(angle_values):
    angles = camera_projection_angles(angle_values)
    return {direction: (math.sqrt(52)*math.sin(math.radians(angle)),
                        -math.sqrt(52)*math.cos(math.radians(angle)), 3)
            for direction, angle in angles.items()}

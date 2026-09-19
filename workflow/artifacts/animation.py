"""단일 PNG 시트의 네 방향 셀 애니메이션 계약. 게임 판정은 처리하지 않는다."""
import math
import warnings
from .sidecar import fields, identifier

DIRECTIONS = frozenset(('down_left', 'down_right', 'up_left', 'up_right'))
MAX_INTEGER = 2**53 - 1


def integer(value, label, minimum=0):
    if type(value) is not int or not minimum <= value <= MAX_INTEGER:
        raise ValueError(f'{label}: {minimum} 이상의 안전한 정수가 필요합니다.')


def validate_animation(data):
    fields(data, {'animationId', 'version', 'sheet', 'frames', 'clips'}, 'animation')
    identifier(data['animationId'], 'animationId'); identifier(data['version'], 'animation.version')
    fields(data['sheet'], {'width', 'height'}, 'sheet')
    for key in ('width', 'height'):
        integer(data['sheet'][key], 'sheet.' + key, 1)
    if type(data['frames']) is not list or not data['frames']:
        raise ValueError('animation.frames에는 하나 이상의 프레임이 필요합니다.')
    frames = {}
    for frame in data['frames']:
        fields(frame, {'frameId', 'rect', 'anchor'}, 'frame')
        identifier(frame['frameId'], 'frameId')
        if frame['frameId'] in frames:
            raise ValueError('프레임 ID가 중복되었습니다.')
        frames[frame['frameId']] = frame
        rect = frame['rect']
        fields(rect, {'x','y','width','height'}, 'rect')
        for key in rect:
            integer(rect[key], 'rect.' + key, 1 if key in ('width','height') else 0)
        if (rect['x'] + rect['width'] > data['sheet']['width']
                or rect['y'] + rect['height'] > data['sheet']['height']):
            raise ValueError('프레임 영역이 시트 범위를 벗어났습니다.')
        fields(frame['anchor'], {'x','y'}, 'anchor')
        for axis, size in (('x','width'),('y','height')):
            value = frame['anchor'][axis]
            if type(value) not in (int,float) or not 0 <= value <= rect[size] or not math.isfinite(value):
                raise ValueError('기준점은 프레임 내부 또는 경계의 유한한 좌표여야 합니다.')
    if type(data['clips']) is not list or not data['clips']:
        raise ValueError('animation.clips에는 하나 이상의 클립이 필요합니다.')
    clips, combinations, used = {}, set(), set()
    for clip in data['clips']:
        fields(clip, {'clipId','action','direction','frames','loop','nextClipId'}, 'clip')
        identifier(clip['clipId'], 'clipId'); identifier(clip['action'], 'action')
        if type(clip['direction']) is not str or clip['direction'] not in DIRECTIONS:
            raise ValueError('클립 방향은 쿼터뷰 네 방향 중 하나여야 합니다.')
        pair = (clip['action'], clip['direction'])
        if clip['clipId'] in clips or pair in combinations:
            raise ValueError('클립 ID 또는 동작/방향 조합이 중복되었습니다.')
        clips[clip['clipId']] = clip; combinations.add(pair)
        if type(clip['frames']) is not list or not clip['frames']:
            raise ValueError('클립은 순서가 있는 프레임 목록이 필요합니다.')
        for item in clip['frames']:
            fields(item, {'frameId','durationMs'}, 'clip.frame')
            identifier(item['frameId'], 'clip.frameId')
            if item['frameId'] not in frames:
                raise ValueError('클립이 존재하지 않는 프레임을 참조합니다.')
            integer(item['durationMs'], 'durationMs', 1)
            used.add(item['frameId'])
        if sum(item['durationMs'] for item in clip['frames']) > MAX_INTEGER:
            raise ValueError('클립 재생 시간 합계가 안전한 정수 범위를 넘었습니다.')
        if type(clip['loop']) is not bool:
            raise ValueError('loop에는 참/거짓이 필요합니다.')
        if clip['nextClipId'] is not None:
            identifier(clip['nextClipId'], 'nextClipId')
            if clip['loop']:
                raise ValueError('반복 클립에는 종료 후 클립을 지정할 수 없습니다.')
    if used != set(frames):
        raise ValueError('어떤 클립에서도 사용하지 않는 프레임이 있습니다.')
    for action in {pair[0] for pair in combinations}:
        if {direction for name, direction in combinations if name == action} != DIRECTIONS:
            raise ValueError('모든 동작에는 쿼터뷰 네 방향 클립이 필요합니다.')
    for clip in clips.values():
        next_id = clip['nextClipId']
        if next_id is not None and (next_id not in clips or clips[next_id]['direction'] != clip['direction']):
            raise ValueError('종료 후 클립은 존재하며 같은 방향이어야 합니다.')
    return data


def validate_sheet(path, animation):
    from PIL import Image
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(path) as image:
                if image.format != 'PNG' or getattr(image, 'n_frames', 1) != 1:
                    raise ValueError('셀 애니메이션 시트에는 단일 PNG 이미지가 필요합니다.')
                if image.size != (animation['sheet']['width'], animation['sheet']['height']):
                    raise ValueError('실제 PNG 크기와 animation.sheet 크기가 다릅니다.')
                image.verify()
            with Image.open(path) as image:
                image.load()
    except (OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError(f'셀 애니메이션 PNG 검사 실패: {exc}') from exc

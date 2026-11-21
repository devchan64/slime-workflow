"""음악·효과음 서비스 이름의 의존성 없는 공용 정의."""
MUSIC_SERVICE_NAMES = ('music-minimax', 'music-magenta', 'music-heartmula')
RETIRED_AUDIO_SERVICE_NAMES = frozenset(('music-minimax', 'music-magenta'))
SOUND_EFFECT_SERVICE = 'sfx-dasheng-audiogen'
AUDIO_SERVICE_NAMES = (*MUSIC_SERVICE_NAMES, SOUND_EFFECT_SERVICE)


def inspect_retired_audio_rejection(current_service_name,current_command_name):
    """음악 서비스의 명시적 폐기 정책만 반환한다."""
    if current_service_name not in RETIRED_AUDIO_SERVICE_NAMES:
        return None
    if current_command_name in ('generate','prepare'):
        return '해당 음악 생성기는 폐기되었습니다. 기존 이력 조회만 지원합니다.'
    if current_command_name=='resume':
        return '폐기 또는 GPU 전용 실행 미검증 생성기는 재개할 수 없습니다.'
    return None

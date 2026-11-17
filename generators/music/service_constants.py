"""음악·효과음 서비스 이름의 의존성 없는 공용 정의."""
MUSIC_SERVICE_NAMES = ('music-minimax', 'music-magenta', 'music-heartmula')
RETIRED_AUDIO_SERVICE_NAMES = frozenset(('music-minimax', 'music-magenta'))
SOUND_EFFECT_SERVICE = 'sfx-dasheng-audiogen'
AUDIO_SERVICE_NAMES = (*MUSIC_SERVICE_NAMES, SOUND_EFFECT_SERVICE)

"""생성기 원본 이력 관측의 지원 대상과 서비스 소유권."""
from generators.music.service_constants import AUDIO_SERVICE_NAMES
from workflow.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS

SOURCE_HISTORY_VIDEO_SERVICES=('dwpose','wan22-animate2','wan22-fun-control','wan22-vace','wan22-i2v','minimax-h3-i2v','wan21-t2v','wan21-i2v')
SOURCE_HISTORY_ARCHIVED_IMAGE_SERVICES=('qwen-21','qwen-21-circular','mannequin-generator','billboard-generator','prop-generator','vegetation-generator','building-generator','expression','seamless-tile')
SOURCE_HISTORY_GENERATOR_SERVICES=(*FLUX_IMAGE_PROFILE_RECORDS,'flux-expression','minimax-h3-image','kimodo',*SOURCE_HISTORY_VIDEO_SERVICES,*SOURCE_HISTORY_ARCHIVED_IMAGE_SERVICES,'floor-tile','prompt-translation','writer-agent','character-animation')
SOURCE_HISTORY_AUDIO_SERVICES=AUDIO_SERVICE_NAMES
SOURCE_HISTORY_SERVICE_ALIASES={'building-generator':'billboard-generator'}

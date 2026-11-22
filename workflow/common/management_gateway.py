"""GUI·CLI의 활성 서비스 명령 계약과 HTTP 게이트웨이. 셸 명령을 실행하지 않는다."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import argparse
from datetime import datetime
import os
from workflow.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_loopback_request_host
import base64
import time
import io
import json
import math
import re
import urllib.error
import urllib.request
from email.message import Message
from urllib.parse import urlsplit, parse_qs

MANAGEMENT_SERVICE_ROUTES = {'qwen-21-circular': '/image-generation-21-circular', 'qwen-21': '/image-generation-21', 'seamless-tile': '/seamless-tile-generator', 'expression': '/expression-generator', 'floor-tile': '/floor-tile-generator', 'character-animation': '/character-animation', 'momask': '/momask-generator', 'qwen-2511': '/image-generation-2511'}
MANAGEMENT_COMMAND_ROUTES = {'anchor-history-reset':('POST','/anchor/history/reset'),'anchor-save':('POST','/anchor/save'),'anchor-history':('POST','/anchor/history'),'anchor-load':('POST','/anchor/load'),'history-delete':('POST','/history/{id}/delete'),'pause':('POST','/pause'),'resume':('POST','/resume'),'sprite-source':('POST','/sprite/source'),'sprite-save':('POST','/sprite/save'),'sprite-load':('POST','/sprite/load'),'sprite-history':('POST','/sprite/history'),'sprite-history-reset':('POST','/sprite/history/reset'),'sprite-history-delete':('POST','/sprite/history/delete'),'record-alpha-vnccs':('POST','/alpha/vnccs/record'),'catalog':('GET','/catalog'),'generate':('POST','/jobs'),'queue':('POST','/jobs'),'prepare':('POST','/jobs'),'status':('GET','/jobs/{id}'),'logs':('GET','/jobs/{id}/worker.log'),'history':('GET','/history'),'active':('GET','/active'),'model-status':('GET','/model-status'),'cancel':('POST','/cancel'),'history-reset':('POST','/history/reset')}
MANAGEMENT_SERVICE_COMMANDS = {'qwen-21-circular': ('history-delete', 'resume', 'generate', 'status', 'logs', 'history', 'active', 'model-status', 'cancel', 'history-reset'), 'qwen-21': ('history-delete', 'resume', 'generate', 'status', 'logs', 'history', 'active', 'model-status', 'cancel', 'history-reset'), 'seamless-tile': ('pause', 'history-delete', 'resume', 'generate', 'status', 'logs', 'history', 'active', 'model-status', 'cancel', 'history-reset'), 'expression': ('history-delete', 'resume', 'generate', 'status', 'logs', 'history', 'active', 'model-status', 'cancel', 'history-reset'), 'floor-tile': ('history-delete', 'resume', 'catalog', 'generate', 'status', 'logs', 'history', 'active', 'model-status', 'cancel', 'history-reset'), 'character-animation': ('anchor-save', 'anchor-history', 'anchor-load', 'anchor-history-reset', 'history-delete', 'resume', 'sprite-source', 'sprite-save', 'sprite-load', 'sprite-history', 'sprite-history-reset', 'sprite-history-delete', 'record-alpha-vnccs', 'catalog', 'generate', 'status', 'logs', 'history', 'active', 'cancel', 'history-reset'), 'momask': ('history-delete', 'resume', 'generate', 'status', 'logs', 'history', 'cancel', 'history-reset'), 'qwen-2511': ('history-delete', 'resume', 'generate', 'status', 'logs', 'history', 'active', 'model-status', 'cancel', 'history-reset')}


MANAGEMENT_SERVICE_ROUTES['model-downloads']='/model-downloads'
MANAGEMENT_SERVICE_COMMANDS['model-downloads']=('download-status','download-inventory','download-observe')
MANAGEMENT_SERVICE_ROUTES['hermes-model'] = '/hermes-model'
MANAGEMENT_SERVICE_COMMANDS['hermes-model'] = ('model-status', 'prepare')
MANAGEMENT_SERVICE_ROUTES['animationgpt'] = '/animationgpt'
MANAGEMENT_SERVICE_COMMANDS['animationgpt'] = ('model-status', 'prepare')
MANAGEMENT_COMMAND_ROUTES['download-observe']=('GET','/observe')
MANAGEMENT_COMMAND_ROUTES['download-status']=('GET','/status')
MANAGEMENT_COMMAND_ROUTES['download-inventory']=('GET','/inventory')

MANAGEMENT_SERVICE_ROUTES['wan22-animate2']='/wan22-animate2'
MANAGEMENT_SERVICE_COMMANDS['wan22-animate2']=('history-delete','resume','generate','prepare','status','logs','history','active','model-status','cancel','history-reset')
MANAGEMENT_SERVICE_ROUTES['wan22-fun-control']='/wan22-fun-control'
MANAGEMENT_SERVICE_COMMANDS['wan22-fun-control']=('history-delete','resume','generate','prepare','status','logs','history','active','model-status','cancel','history-reset')
MANAGEMENT_SERVICE_ROUTES['dwpose']='/dwpose'
MANAGEMENT_SERVICE_COMMANDS['dwpose']=('history-delete','resume','generate','prepare','status','logs','history','active','model-status','cancel','history-reset')
MANAGEMENT_SERVICE_ROUTES['kimodo']='/kimodo'
MANAGEMENT_SERVICE_COMMANDS['kimodo']=('history-delete','resume','generate','status','logs','history','active','model-status','cancel','history-reset')
MANAGEMENT_SERVICE_COMMANDS['kimodo'] += ('prepare','keyframe-source-review','keyframe-save-reviewed','keyframe-save','keyframe-list','keyframe-preview','keyframe-replace','keyframe-retire')
MANAGEMENT_SERVICE_COMMANDS['kimodo'] += ('migraphx-build', 'migraphx-build-status', 'migraphx-build-observe')
MANAGEMENT_SERVICE_COMMANDS['kimodo'] += ('active-observe',)
MANAGEMENT_COMMAND_ROUTES['active-observe']=('GET','/active-observe')
MANAGEMENT_COMMAND_ROUTES.update({'migraphx-build': ('POST', '/migraphx-build'), 'migraphx-build-status': ('GET', '/migraphx-build-status'), 'migraphx-build-observe': ('GET', '/migraphx-build-observe')})
MANAGEMENT_COMMAND_ROUTES['keyframe-source-review'] = ('POST','/keyframes/source-review')
MANAGEMENT_COMMAND_ROUTES['keyframe-save-reviewed'] = ('POST','/keyframes/save-reviewed')
MANAGEMENT_COMMAND_ROUTES['keyframe-save'] = ('POST','/keyframes/save')
MANAGEMENT_COMMAND_ROUTES['keyframe-list'] = ('POST','/keyframes/list')
MANAGEMENT_COMMAND_ROUTES['keyframe-preview'] = ('POST','/keyframes/preview')
MANAGEMENT_COMMAND_ROUTES['keyframe-replace'] = ('POST','/keyframes/replace')
MANAGEMENT_COMMAND_ROUTES['keyframe-retire'] = ('POST','/keyframes/retire')
MANAGEMENT_SERVICE_ROUTES['wan22-vace']='/wan22-vace'
MANAGEMENT_SERVICE_COMMANDS['wan22-vace']=('history-delete','resume','generate','prepare','status','logs','history','active','model-status','cancel','history-reset')

MANAGEMENT_COMMAND_ROUTES['sheet-auto'] = ('POST', '/sheet/auto')
MANAGEMENT_COMMAND_ROUTES['sheet-export'] = ('POST', '/sheet/export')
MANAGEMENT_COMMAND_ROUTES['sheet-gif'] = ('POST', '/sheet/gif')
MANAGEMENT_SERVICE_COMMANDS['character-animation'] += ('sheet-auto','sheet-export','sheet-gif','sheet-search','sheet-image','sheet-update')
MANAGEMENT_COMMAND_ROUTES.update({'sheet-update':('POST','/sheet/update'),'sheet-search':('POST','/sheet/search'),'sheet-image':('POST','/sheet/image')})

WRITER_PAYLOAD_COMMAND_NAMES = ('writer-index-status', 'writer-search-paths', 'writer-material-page', 'writer-detail', 'writer-submit', 'writer-submit-bound', 'writer-apply', 'writer-history', 'writer-history-observe', 'writer-delete', 'writer-cancel')
TRANSLATION_PAYLOAD_COMMAND_NAMES = ('translation-submit', 'translation-status', 'translation-cancel', 'translation-history', 'translation-rag')
HERMES_PAYLOAD_COMMAND_NAMES = ('hermes-video-form-save', 'hermes-video-form-read', 'hermes-video-form-submit', 'hermes-video-form-status', 'hermes-workflow-list', 'hermes-workflow-catalog', 'hermes-workflow-review', 'hermes-workflow-register', 'hermes-workflow-view', 'hermes-workflow-cancel', 'hermes-workflow-select', 'hermes-workflow-retry', 'hermes-workflow-draft-read', 'hermes-workflow-draft-save', 'hermes-form-list', 'hermes-form-read', 'hermes-form-save', 'hermes-workflow-image-preview', 'hermes-workflow-audio-preview', 'hermes-anchor-history-observe', 'hermes-generator-reservation-recover', 'hermes-generator-reservation-receipt', 'hermes-generator-reservation-inspect', 'hermes-submit', 'hermes-detail', 'hermes-history', 'hermes-diff', 'hermes-cancel', 'hermes-session-archived', 'hermes-session-archive', 'hermes-session-restore', 'hermes-session-delete', 'hermes-session-create', 'hermes-session-read', 'hermes-session-list', 'hermes-session-submit', 'hermes-session-view', 'hermes-management-status', 'hermes-priority-preview', 'hermes-priority-submit', 'hermes-priority-receipt', 'hermes-service-receipt', 'hermes-capture-status', 'hermes-capture-proposal', 'hermes-expression-catalog', 'hermes-model-inventory', 'hermes-model-download-status', 'hermes-content-database-status', 'hermes-map-database-receipt', 'hermes-kimodo-build-status', 'hermes-model-readiness', 'hermes-model-prepare', 'hermes-model-prepare-status', 'hermes-model-prepare-history', 'hermes-billboard-catalog', 'hermes-billboard-proposal', 'hermes-billboard-load', 'hermes-billboard-preview', 'hermes-billboard-save', 'hermes-billboard-receipt', 'hermes-building-catalog', 'hermes-building-preview', 'hermes-building-save', 'hermes-building-receipt', 'hermes-sprite-pending-status', 'hermes-sprite-clip-playback', 'hermes-sprite-playback', 'hermes-sprite-proposal', 'hermes-sprite-preview', 'hermes-sprite-save', 'hermes-sprite-receipt', 'hermes-sprite-catalog', 'hermes-sprite-detail', 'hermes-effect-catalog', 'hermes-effect-detail', 'hermes-effect-proposal', 'hermes-effect-preview', 'hermes-effect-save', 'hermes-effect-receipt', 'hermes-effect-register-preview', 'hermes-effect-register', 'hermes-effect-register-receipt', 'hermes-waypoint-preview', 'hermes-waypoint-replace', 'hermes-waypoint-receipt', 'hermes-world-map', 'hermes-field-load', 'hermes-field-region', 'hermes-field-preview', 'hermes-field-save', 'hermes-field-receipt', 'hermes-field-history', 'hermes-city-load', 'hermes-city-preview', 'hermes-city-save', 'hermes-city-receipt', 'hermes-city-history', 'hermes-service-registration', 'hermes-delegate-writer', 'hermes-writer-proposal', 'hermes-writer-index-status', 'hermes-writer-search-paths', 'hermes-writer-status', 'hermes-writer-history', 'hermes-writer-cancel', 'hermes-writer-reservation-preview', 'hermes-writer-reservation-recover', 'hermes-writer-reservation-receipt', 'hermes-writer-apply', 'hermes-writer-apply-status', 'hermes-writer-apply-history', 'hermes-delegate-translation', 'hermes-translation-proposal', 'hermes-translation-evidence', 'hermes-translation-status', 'hermes-translation-history', 'hermes-translation-cancel', 'hermes-delegate-video', 'hermes-video-proposal', 'hermes-video-status', 'hermes-video-history', 'hermes-video-cancel', 'hermes-delegate-audio', 'hermes-audio-proposal', 'hermes-audio-status', 'hermes-audio-history', 'hermes-audio-source-history', 'hermes-generator-source-history', 'hermes-audio-cancel', 'hermes-delegate-flux-profile', 'hermes-flux-profile-status', 'hermes-flux-profile-history', 'hermes-flux-profile-cancel', 'hermes-delegate-flux-image', 'hermes-flux-delegation-history', 'hermes-flux-delegation-status', 'hermes-flux-delegation-cancel', 'hermes-delegate-kimodo', 'hermes-kimodo-proposal', 'hermes-kimodo-keyframes', 'hermes-kimodo-keyframe-preview', 'hermes-kimodo-keyframe-validate', 'hermes-flux-proposal', 'hermes-field-proposal', 'hermes-delegation-status', 'hermes-delegation-cancel', 'hermes-delegation-job-status', 'hermes-delegation-history', 'hermes-capabilities')
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-writer-job-search-paths','hermes-writer-job-review','hermes-writer-job-material',)
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-session-context-settings', 'hermes-session-context-compress')
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-chat-queue-update', 'hermes-live-instruction', 'hermes-live-instruction-recover')
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-audio-source-status',)
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-video-source-status','hermes-flux-source-status','hermes-image-source-status','hermes-character-source-status','hermes-kimodo-source-frame',)
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-kimodo-keyframe-source-review','hermes-kimodo-keyframe-save','hermes-kimodo-keyframe-receipt',)
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-city-source',)
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-city-proposal','hermes-building-proposal')
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-audio-resume-preview','hermes-audio-resume-submit','hermes-audio-resume-receipt')
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-translation-resume-preview','hermes-translation-resume-submit','hermes-translation-resume-receipt')
MANAGEMENT_SERVICE_ROUTES['hermes-agent'] = '/hermes-agent'
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-model-preparation-proposal',)
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-kimodo-resume-preview','hermes-kimodo-resume-submit','hermes-kimodo-resume-receipt','hermes-kimodo-resume-proposal')
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-cleanup-preview',)
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-video-resume-preview','hermes-video-resume-submit','hermes-video-resume-receipt','hermes-video-resume-proposal')
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-flux-resume-preview','hermes-flux-resume-submit','hermes-flux-resume-receipt','hermes-flux-resume-proposal')
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-resident-start','hermes-resident-status','hermes-resident-release','hermes-gpu-handoff-preview','hermes-gpu-handoff-approve','hermes-gpu-handoff-status','hermes-gpu-handoff-list','hermes-gpu-handoff-withdraw','hermes-gpu-handoff-writer-context','hermes-gpu-handoff-recover-release','hermes-gpu-handoff-recover-submission','hermes-gpu-handoff-recover-reload','hermes-gpu-handoff-cancel')
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-writer-proposal-submit','hermes-writer-proposal-receipt')
HERMES_PAYLOAD_COMMAND_NAMES += ('hermes-gpu-handoff-retry-reload',)
MANAGEMENT_SERVICE_COMMANDS['hermes-agent'] = HERMES_PAYLOAD_COMMAND_NAMES
MANAGEMENT_COMMAND_ROUTES.update({current_command_name: ('POST', '/' + current_command_name) for current_command_name in HERMES_PAYLOAD_COMMAND_NAMES})
MANAGEMENT_SERVICE_ROUTES['prompt-translation'] = '/prompt-translation'
MANAGEMENT_SERVICE_COMMANDS['prompt-translation'] = (*TRANSLATION_PAYLOAD_COMMAND_NAMES, 'model-status', 'prepare', 'history', 'status', 'logs', 'cancel', 'resume', 'history-delete', 'history-reset')
MANAGEMENT_COMMAND_ROUTES.update({current_command_name: ('POST', '/' + current_command_name) for current_command_name in TRANSLATION_PAYLOAD_COMMAND_NAMES})
MANAGEMENT_SERVICE_ROUTES['writer-agent'] = '/writer-agent'
MANAGEMENT_SERVICE_COMMANDS['writer-agent'] = ('writer-state', 'writer-token', 'model-status', 'prepare', *WRITER_PAYLOAD_COMMAND_NAMES)
MANAGEMENT_COMMAND_ROUTES.update({'writer-index-status': ('POST', '/api/index-status'), 'writer-state': ('GET', '/api/state'), 'writer-token': ('GET', '/api/token'), 'writer-search-paths': ('POST', '/api/search-paths'), 'writer-material-page': ('POST', '/api/material-page'), 'writer-detail': ('POST', '/api/detail'), 'writer-submit': ('POST', '/api/jobs'), 'writer-submit-bound': ('POST', '/api/jobs-bound'), 'writer-apply': ('POST', '/api/apply'), 'writer-history': ('POST', '/api/history'), 'writer-history-observe': ('POST', '/api/history/observe'), 'writer-delete': ('POST', '/api/history/delete'), 'writer-cancel': ('POST', '/api/cancel')})


MANAGEMENT_SERVICE_ROUTES['map-assets']='/map-assets'
MANAGEMENT_SERVICE_COMMANDS['map-assets']=('resize','map-anchor-save','effect-list','effect-load','effect-save','effect-register','effect-register-check','effect-register-reviewed','effect-replace','asset-list','asset-register','asset-preview','asset-save','asset-save-reviewed','asset-crop-preview','asset-crop','asset-retire-preview','asset-retire','map-edit-load','map-edit-preview','map-edit-save','city-edit-load','city-edit-preview','city-edit-save','building-list','building-save','building-register','building-retire','database-seed','database-status','database-sync','database-snapshot','database-restore')
MANAGEMENT_COMMAND_ROUTES.update({'building-list':('POST','/editor-building-list'),'building-save':('POST','/editor-building-save'),'building-register':('POST','/editor-building-register'),'building-retire':('POST','/editor-building-retire')})
MANAGEMENT_COMMAND_ROUTES.update({current_command_name:('POST','/'+current_command_name) for current_command_name in ('database-seed','database-status','database-sync','database-snapshot','database-restore')})
MANAGEMENT_COMMAND_ROUTES.update({current_command_name:('POST','/editor-'+current_command_name) for current_command_name in ('effect-list','effect-load','effect-save','effect-register','effect-register-check','effect-register-reviewed','effect-replace','map-edit-load','map-edit-preview','map-edit-save','city-edit-load','city-edit-preview','city-edit-save')})
MANAGEMENT_COMMAND_ROUTES.update({'asset-list':('POST','/editor-list'),'asset-preview':('POST','/editor-preview'),'asset-save':('POST','/editor-save'),'asset-save-reviewed':('POST','/editor-save-reviewed'),'asset-retire-preview':('POST','/editor-retire-preview'),'asset-retire':('POST','/editor-retire')})
MANAGEMENT_COMMAND_ROUTES['asset-register']=('POST','/editor-register')
MANAGEMENT_COMMAND_ROUTES['map-anchor-save']=('POST','/anchor-save')
MANAGEMENT_COMMAND_ROUTES.update({'asset-crop-preview':('POST','/editor-crop-preview'),'asset-crop':('POST','/editor-crop')})
MANAGEMENT_COMMAND_ROUTES['resize']=('POST','/resize')
MANAGEMENT_SERVICE_ROUTES['map-review']='/map-review'
MANAGEMENT_SERVICE_COMMANDS['map-review']=('capture',)
MANAGEMENT_SERVICE_ROUTES['character-review']='/character-review'
MANAGEMENT_SERVICE_COMMANDS['character-review']=('capture',)
MANAGEMENT_COMMAND_ROUTES['capture']=('POST','/capture')


from generators.music.service_constants import AUDIO_SERVICE_NAMES, RETIRED_AUDIO_SERVICE_NAMES
for current_service_name in ('billboard-generator','prop-generator', 'vegetation-generator', 'mannequin-generator'):
    MANAGEMENT_SERVICE_ROUTES[current_service_name] = '/' + current_service_name
    MANAGEMENT_SERVICE_COMMANDS[current_service_name] = MANAGEMENT_SERVICE_COMMANDS['qwen-21']

MANAGEMENT_SERVICE_COMMANDS['prop-generator'] += ('prepare',)
MANAGEMENT_SERVICE_ROUTES['expression-lora'] = '/expression-lora'
MANAGEMENT_SERVICE_COMMANDS['expression-lora'] = ('model-status', 'prepare')
MANAGEMENT_SERVICE_ROUTES['flux-expression'] = '/flux-expression-generator'
MANAGEMENT_SERVICE_COMMANDS['flux-expression'] = ('history-delete', 'resume', 'generate', 'status', 'logs', 'history', 'active', 'model-status', 'cancel', 'history-reset')
from workflow.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
for current_flux_profile in FLUX_IMAGE_PROFILE_RECORDS:
    MANAGEMENT_SERVICE_ROUTES[current_flux_profile] = '/' + current_flux_profile + '-generator'
    MANAGEMENT_SERVICE_COMMANDS[current_flux_profile] = MANAGEMENT_SERVICE_COMMANDS['flux-expression']
MANAGEMENT_SERVICE_COMMANDS['flux-image'] += ('prepare',)

MANAGEMENT_SERVICE_ROUTES['building-generator'] = '/building-generator'
MANAGEMENT_SERVICE_COMMANDS['building-generator'] = MANAGEMENT_SERVICE_COMMANDS['qwen-21']

for current_service_name in AUDIO_SERVICE_NAMES:
    MANAGEMENT_SERVICE_ROUTES[current_service_name] = '/' + current_service_name
    MANAGEMENT_SERVICE_COMMANDS[current_service_name] = ('generate','prepare','status','logs','history','history-observe','active','model-status','cancel','resume','history-delete','history-reset')

for current_service_name in ('music-heartmula', 'sfx-dasheng-audiogen'):
    MANAGEMENT_SERVICE_COMMANDS[current_service_name] += ('download-model', 'download-model-status')
MANAGEMENT_COMMAND_ROUTES.update({'download-model': ('POST', '/model-download'), 'download-model-status': ('GET', '/model-download')})

MANAGEMENT_COMMAND_ROUTES['resume-reviewed'] = ('POST', '/resume/reviewed')
MANAGEMENT_SERVICE_COMMANDS['kimodo'] += ('resume-reviewed',)
for current_video_service in ('dwpose','wan22-animate2','wan22-vace','wan22-fun-control'):
    MANAGEMENT_SERVICE_COMMANDS[current_video_service] += ('resume-reviewed',)
for current_flux_profile in FLUX_IMAGE_PROFILE_RECORDS:
    MANAGEMENT_SERVICE_COMMANDS[current_flux_profile] += ('resume-reviewed',)
MANAGEMENT_COMMAND_ROUTES['resume-preview'] = ('POST', '/resume/preview')
for current_service_name in ('music-heartmula','sfx-dasheng-audiogen','prompt-translation','kimodo','dwpose','wan22-animate2','wan22-vace','wan22-fun-control',*FLUX_IMAGE_PROFILE_RECORDS):
    MANAGEMENT_SERVICE_COMMANDS[current_service_name] += ('resume-preview',)

MANAGEMENT_COMMAND_ROUTES['history-observe'] = ('POST', '/history/observe')
MANAGEMENT_COMMAND_ROUTES['history-reset-preview'] = ('GET', '/history/reset-preview')
for current_service_name, current_command_names in tuple(MANAGEMENT_SERVICE_COMMANDS.items()):
    if 'history-reset' in current_command_names and current_service_name not in ('momask', 'character-animation'):
        MANAGEMENT_SERVICE_COMMANDS[current_service_name] += ('history-reset-preview',)

MANAGEMENT_COMMAND_ROUTES['prioritize'] = ('POST', '/history/{id}/prioritize')
for current_service_name, current_command_names in tuple(MANAGEMENT_SERVICE_COMMANDS.items()):
    if 'resume' in current_command_names:
        MANAGEMENT_SERVICE_COMMANDS[current_service_name] += ('prioritize',)

from workflow.common.source_history_catalog import SOURCE_HISTORY_ARCHIVED_IMAGE_SERVICES, SOURCE_HISTORY_GENERATOR_SERVICES
ARCHIVED_QWEN_IMAGE_SERVICES = frozenset(SOURCE_HISTORY_ARCHIVED_IMAGE_SERVICES)
for current_service_name in SOURCE_HISTORY_GENERATOR_SERVICES:
    if current_service_name != 'writer-agent':
        MANAGEMENT_SERVICE_COMMANDS[current_service_name] += ('history-observe',)


def inspect_management_policy_rejection(service_command_name, operation_command_name):
    """게이트웨이의 명시적 차단 사유만 반환하며 서비스의 실행 가능성을 판정하지 않는다."""
    if service_command_name=='map-assets' and operation_command_name=='database-restore':
        return '폐기된 파일 스냅샷 복구는 지원하지 않습니다. 에셋 원본과 현재 콘텐츠 DB 상태를 확인하세요.'
    if service_command_name in RETIRED_AUDIO_SERVICE_NAMES and operation_command_name == 'prepare':
        return '폐기된 음악 생성기는 모델 준비를 지원하지 않습니다. 기존 이력은 조회할 수 있습니다.'
    if service_command_name == 'expression-lora' and operation_command_name == 'prepare':
        return 'Qwen 2.1 표정 LoRA는 라이선스 사유로 사용과 다운로드가 중단되었습니다.'
    if service_command_name in ARCHIVED_QWEN_IMAGE_SERVICES and operation_command_name in ('generate', 'resume', 'prioritize', 'prepare'):
        return 'Qwen 이미지 생성기는 폐기되어 모델 준비·새 생성·재개·우선 실행을 지원하지 않습니다. 기존 이력과 결과는 조회할 수 있습니다.'
    if service_command_name == 'anny':
        return 'ANNY 속성 렌더러·모델·결과는 폐기되었습니다.'
    if service_command_name == 'anny-landmarks':
        return 'ANNY 해부학 기준점 페이지와 기능은 폐기되었습니다.'
    if service_command_name == 'animation-separation':
        return '캐릭터 레퍼런스 복장 분리 생성기와 이력은 폐기되었습니다.'
    if service_command_name == 'outfit-transfer':
        return '복장 착용 생성기와 이력은 폐기되었습니다.'
    if service_command_name == 'pose-transfer':
        return '포즈 변환 생성기·모델·결과는 폐기되었습니다.'
    if service_command_name == 'wan22-animate':
        return 'Wan2.2 Animate 모델·생성기·결과는 폐기되었습니다.'
    if service_command_name == 'hy-motion':
        return 'HY-Motion 모델·생성기·결과는 폐기되었습니다. Kimodo를 사용하세요.'
    if service_command_name == 'momask':
        return 'MoMask 포즈 생성기와 과거 기록은 폐기되었습니다. Kimodo를 사용하세요.'
    if service_command_name == 'qwen-2511':
        return 'Qwen Image Edit 2511 생성기는 폐기되었습니다. 사용 가능한 FLUX 생성기를 확인하세요.'
    if service_command_name == 'floor-tile' and operation_command_name in ('generate', 'resume', 'prioritize'):
        return '바닥 타일 생성기는 폐기되었습니다. 생성과 재개는 지원하지 않습니다.'
    return None


def resolve_management_command(service_command_name, operation_command_name, command_payload_value):
    current_policy_rejection=inspect_management_policy_rejection(service_command_name,operation_command_name)
    if current_policy_rejection:
        raise ValueError(current_policy_rejection)
    if service_command_name not in MANAGEMENT_SERVICE_COMMANDS or operation_command_name not in MANAGEMENT_SERVICE_COMMANDS[service_command_name]:
        raise ValueError('지원하지 않는 관리 명령')
    if not isinstance(command_payload_value,dict):
        raise ValueError('명령 입력은 JSON 객체여야 합니다.')
    if service_command_name == 'kimodo' and operation_command_name == 'active-observe' and command_payload_value:
        raise ValueError('Kimodo 기록 관측은 입력을 받지 않습니다.')
    if operation_command_name in ('migraphx-build', 'migraphx-build-status', 'migraphx-build-observe') and command_payload_value:
        raise ValueError('MIGraphX 빌드 명령은 입력 필드를 받지 않습니다.')
    if operation_command_name in ('history-reset-preview','writer-state','writer-token','download-status','download-inventory','download-observe','download-model','download-model-status') and command_payload_value:
        raise ValueError('초기화 미리보기는 입력 필드를 받지 않습니다.')
    if service_command_name == 'expression-lora' and operation_command_name == 'prepare' and command_payload_value != {'action': 'prepare'}:
        raise ValueError('표정 LoRA 준비에는 action=prepare만 허용합니다.')
    if service_command_name == 'prop-generator' and operation_command_name == 'prepare' and command_payload_value != {'action': 'prepare'}:
        raise ValueError('소품 모델 준비에는 action=prepare만 허용합니다.')
    if service_command_name == 'wan22-fun-control' and operation_command_name == 'prepare' and command_payload_value not in ({'action': 'prepare'}, {'action': 'prepare', 'model_profile': 'wan21-1.3b'}):
        raise ValueError('Fun Control 준비 프로필이 올바르지 않습니다.')
    if service_command_name in ('wan22-vace', 'writer-agent', 'prompt-translation', 'hermes-model', 'animationgpt', 'dwpose') and operation_command_name == 'prepare' and command_payload_value != {'action': 'prepare'}:
        raise ValueError('모델 준비에는 action=prepare만 허용합니다.')
    if service_command_name in ('hermes-model', 'animationgpt') and operation_command_name == 'model-status' and command_payload_value:
        raise ValueError('모델 상태 조회에는 입력을 전달할 수 없습니다.')
    request_method_value, request_suffix_value = MANAGEMENT_COMMAND_ROUTES[operation_command_name]
    if '{id}' in request_suffix_value:
        generation_job_identifier=command_payload_value.get('id','')
        if not isinstance(generation_job_identifier,str) or not re.fullmatch(r'[a-f0-9]{8}' if service_command_name=='anny' else r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',generation_job_identifier):
            raise ValueError('생성 ID 형식 오류')
        request_suffix_value=request_suffix_value.format(id=generation_job_identifier)
    if operation_command_name=='history' and 'page' in command_payload_value:
        request_suffix_value+='?page='+str(max(1,int(command_payload_value['page'])))
    return request_method_value, MANAGEMENT_SERVICE_ROUTES[service_command_name]+request_suffix_value


def identify_management_command(request_route_value, request_method_value, request_payload_value=None):
    request_url_parts=urlsplit(request_route_value)
    for service_command_name,service_route_prefix in MANAGEMENT_SERVICE_ROUTES.items():
        if not request_url_parts.path.startswith(service_route_prefix+'/'):
            continue
        request_route_suffix=request_url_parts.path[len(service_route_prefix):]
        for operation_command_name in MANAGEMENT_SERVICE_COMMANDS[service_command_name]:
            expected_method_value,expected_route_value=MANAGEMENT_COMMAND_ROUTES[operation_command_name]
            if expected_method_value!=request_method_value:
                continue
            request_match_value=re.fullmatch(re.escape(expected_route_value).replace(r'\{id\}',r'(?P<id>[a-f0-9]{8})' if service_command_name=='anny' else r'(?P<id>\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8})'),request_route_suffix)
            if request_match_value:
                command_payload_value=dict(request_payload_value or {})
                command_payload_value.update(request_match_value.groupdict())
                if operation_command_name=='generate' and command_payload_value.get('action')=='prepare':
                    operation_command_name='prepare'
                if operation_command_name=='history':
                    command_payload_value.update({key:values[0] for key,values in parse_qs(request_url_parts.query).items() if key=='page'})
                return service_command_name,operation_command_name,command_payload_value
    return None


class GatewayRequestAdapter:
    def __init__(self, original_request_handler, request_method_value, request_route_value, request_payload_value):
        self.original_request_handler=original_request_handler
        self.command=request_method_value
        self.path=request_route_value
        self.management_command_payload=request_payload_value
        request_body_bytes=json.dumps(request_payload_value,ensure_ascii=False,allow_nan=False).encode() if request_method_value=='POST' else b''
        self.rfile=io.BytesIO(request_body_bytes)
        self.headers=Message()
        for request_header_name,request_header_value in original_request_handler.headers.items():
            if request_header_name.lower() not in ('content-type','content-length'):
                self.headers[request_header_name]=request_header_value
        self.headers['Content-Type']='application/json'
        self.headers['Content-Length']=str(len(request_body_bytes))

    def __getattr__(self, attribute_name_value):
        return getattr(self.original_request_handler,attribute_name_value)


def parse_management_request_json(current_request_text):
    """중복 필드와 비유한 숫자를 GUI·CLI 입력 경계에서 거절한다."""
    def collect_unique_request_fields(current_field_pairs):
        current_field_values={}
        for current_field_name,current_field_value in current_field_pairs:
            if current_field_name in current_field_values:
                raise ValueError('중복 요청 필드')
            current_field_values[current_field_name]=current_field_value
        return current_field_values
    def reject_nonfinite_request_constant(current_constant_text):
        raise ValueError('유한한 JSON 숫자만 허용합니다: '+current_constant_text)
    def parse_finite_request_float(current_number_text):
        current_number_value=float(current_number_text)
        if not math.isfinite(current_number_value):
            raise ValueError('유한한 JSON 숫자만 허용합니다: '+current_number_text)
        return current_number_value
    return json.loads(current_request_text,object_pairs_hook=collect_unique_request_fields,
                      parse_constant=reject_nonfinite_request_constant,parse_float=parse_finite_request_float)


class ManagementCommandGateway:
    def __init__(self, service_handler_values):
        self.service_handler_values=service_handler_values

    def handle(self, current_http_handler):
        gateway_request_path=urlsplit(current_http_handler.path).path
        gateway_envelope_request=gateway_request_path=='/management/command'
        legacy_command_match=identify_management_command(current_http_handler.path,current_http_handler.command)
        if not gateway_envelope_request and not legacy_command_match:
            return False
        try:
            expected_origin_value=validate_loopback_request_host(current_http_handler)
            request_payload_value={}
            if current_http_handler.command=='POST':
                if current_http_handler.headers.get('Origin')!=expected_origin_value or current_http_handler.headers.get('Content-Type','').split(';')[0]!='application/json':
                    raise ValueError('동일 출처 JSON 요청만 허용합니다.')
                request_body_length=int(current_http_handler.headers.get('Content-Length','0'))
                if not 1<=request_body_length<=40_200_000:
                    raise ValueError('요청 크기 오류')
                request_payload_value=parse_management_request_json(current_http_handler.rfile.read(request_body_length))
            if gateway_envelope_request:
                if current_http_handler.command!='POST' or not isinstance(request_payload_value,dict) or set(request_payload_value)!={'service','command','payload'}:
                    raise ValueError('service·command·payload 명령 형식이 필요합니다.')
                service_command_name=request_payload_value['service'];operation_command_name=request_payload_value['command'];command_payload_value=request_payload_value['payload']
                if not isinstance(service_command_name,str) or not isinstance(operation_command_name,str):raise ValueError('명령 이름 오류')
            else:
                service_command_name,operation_command_name,command_payload_value=identify_management_command(current_http_handler.path,current_http_handler.command,request_payload_value)
            request_method_value,request_route_value=resolve_management_command(service_command_name,operation_command_name,command_payload_value)
            # 작업 파일 조회 이외의 임의 URL·프로그램 실행을 허용하지 않는다.
            execute_management_command(service_command_name,operation_command_name,command_payload_value,gateway_request_handler=current_http_handler,service_handler_values=self.service_handler_values)
        except (ValueError,KeyError,TypeError,OSError) as gateway_error_value:
            response_payload_bytes=json.dumps({'error':str(gateway_error_value)},ensure_ascii=False).encode()
            current_http_handler.send_response(400);current_http_handler.send_header('Content-Type','application/json; charset=utf-8');current_http_handler.send_header('Content-Length',str(len(response_payload_bytes)));current_http_handler.end_headers();current_http_handler.wfile.write(response_payload_bytes)
        return True


MANAGEMENT_COMMAND_DESCRIPTIONS = {'flux-expression': 'FLUX 3 표정 생성 · 얼굴 참조 1장', 'expression-lora': 'Qwen 2.1 표정 LoRA 사용·다운로드 중단 · 기존 모델 상태 조회', 'qwen-21-circular': 'Qwen 2.1 순환 VAE 생성기 아카이브 · 기존 이력 조회', 'qwen-21': 'Qwen Image 2.1 생성기 아카이브 · 기존 이력 조회', 'seamless-tile': 'Qwen 심리스 패턴 생성기 아카이브 · 기존 이력 조회', 'expression': 'Qwen 2.1 표정 생성기 아카이브 · 기존 이력 조회', 'floor-tile': '바닥 타일 생성기 폐기 · 기존 이력 조회·삭제 가능 · 생성·재개 불가', 'character-animation': '생성기 폐기 · 기존 이력·결과 조회·스프라이트 편집 (generate/resume 거절)', 'momask': '폐기된 MoMask 도구 · 모든 명령 거절 · Kimodo 사용', 'qwen-2511': 'Qwen Image Edit 2511 생성기 폐기 · 모든 관리 명령 거부 · 사용 가능한 FLUX 생성기 확인'}

MANAGEMENT_COMMAND_DESCRIPTIONS['model-downloads']='공유 모델 다운로드 상태 조회'
MANAGEMENT_COMMAND_DESCRIPTIONS['hermes-model']='Hermes 코딩 모델 다운로드와 SHA-256 검증'
MANAGEMENT_COMMAND_DESCRIPTIONS['animationgpt']='AnimationGPT 제3자 FP16 모델 파일 다운로드와 SHA-256 검증'
MANAGEMENT_COMMAND_DESCRIPTIONS['hermes-agent']='격리 Hermes 작업 접수·상태·이력·취소 --payload-file'
for current_flux_profile, current_flux_values in FLUX_IMAGE_PROFILE_RECORDS.items():
    MANAGEMENT_COMMAND_DESCRIPTIONS[current_flux_profile] = 'FLUX 3 ' + current_flux_values[0] + ' 이미지 생성'
MANAGEMENT_COMMAND_DESCRIPTIONS['writer-agent']='작가 문서 학습·제안·조회·해시 확인 적용 · --payload-file · 기존 문서/기록 경로 유지'
MANAGEMENT_COMMAND_DESCRIPTIONS['prompt-translation']='한국어 프롬프트 번역 · 요청·상태·취소·이력 --payload-file'
MANAGEMENT_COMMAND_DESCRIPTIONS['map-assets']='맵 PNG 축소·투명 여백 크롭(asset-crop-preview / asset-crop)·빌보드 속성·야외·도시 맵 편집 · map-edit-load / map-edit-preview / map-edit-save / city-edit-load / city-edit-preview / city-edit-save / asset-list(category: vegetation·herbaceous·large-trees·rocks-minerals·props) / asset-preview / asset-save / asset-retire-preview / asset-retire / building-list / building-save / building-register / building-retire / database-seed / database-status / database-sync / database-restore(폐기) --payload-file'
MANAGEMENT_COMMAND_DESCRIPTIONS['map-review']='전체 맵 헤드리스 Chrome PNG 캡처 · --payload-file 설정'
MANAGEMENT_COMMAND_DESCRIPTIONS['character-review']='캐릭터 검수 렌더링 PNG 캡처 · --payload-file 설정'
MANAGEMENT_COMMAND_DESCRIPTIONS['billboard-generator'] = 'Qwen 가이드 빌보드 생성 · 독립 대기열·이력'
MANAGEMENT_COMMAND_DESCRIPTIONS['prop-generator'] = 'Qwen 소품 생성 · 독립 대기열·이력 · 참조 선택'
MANAGEMENT_COMMAND_DESCRIPTIONS['mannequin-generator'] = 'Qwen 마네킨 생성 · 전용 이력 · 공용 GPU 대기열'
MANAGEMENT_COMMAND_DESCRIPTIONS['vegetation-generator'] = 'Qwen 자연물 생성 · 독립 대기열·이력 · 참조 선택'
MANAGEMENT_COMMAND_DESCRIPTIONS['building-generator'] = '빌보드·건물 통합 생성기의 호환 명령 · 공용 대기열·이력'

for current_archived_service in ARCHIVED_QWEN_IMAGE_SERVICES:
    MANAGEMENT_COMMAND_DESCRIPTIONS[current_archived_service] = 'Qwen 이미지 생성기 폐기 · 생성·재개·모델 준비 차단 · 기존 이력 조회'

for current_service_name in AUDIO_SERVICE_NAMES:
    MANAGEMENT_COMMAND_DESCRIPTIONS[current_service_name] = '음악생성 · 고정 로컬 모델 · ROCm GPU · WAV · 실측 검증 필요'

MANAGEMENT_COMMAND_DESCRIPTIONS['music-minimax']='폐기 · 기존 결과와 로그 조회 · 신규 생성·준비·재개 차단'
MANAGEMENT_COMMAND_DESCRIPTIONS['music-heartmula']='HeartMuLa 3B · 음악 생성·모델 준비·기존 이력 · GPU 실행은 별도 확인'
MANAGEMENT_COMMAND_DESCRIPTIONS['music-magenta']='폐기 · 기존 결과와 로그 조회 · 신규 생성·준비·재개 차단'
MANAGEMENT_COMMAND_DESCRIPTIONS['sfx-dasheng-audiogen']='효과음 생성 · Dasheng-AudioGen · ROCm GPU · 길이 자동 예측 · 16kHz mono WAV'


MANAGEMENT_COMMAND_DESCRIPTIONS['wan22-animate2']='Animate-2 · RGB 동작 영상과 캐릭터 참조 · --payload-file'
MANAGEMENT_COMMAND_DESCRIPTIONS['wan22-fun-control']='Wan2.2 Fun Control BF16 · 참조/포즈 영상 · --payload-file'
MANAGEMENT_COMMAND_DESCRIPTIONS['dwpose']='단일 832×480 PNG DWPose 추출 · ROCm MIGraphX · --payload-file'
MANAGEMENT_COMMAND_DESCRIPTIONS['kimodo']='Kimodo SOMA v1.2 · 비양자화 BF16 텍스트 인코더 · 원본 관절 모션·미리보기 · --payload-file'
MANAGEMENT_COMMAND_DESCRIPTIONS['wan22-vace']='Wan2.2 VACE-Fun A14B BF16 · 텍스트·외형 참조·첫 프레임·DWPose·부분 편집·영상 전체 조건 실험 · --payload-file'

def execute_management_command(service_command_name, operation_command_name, command_payload_value, server_base_address=None, *, gateway_request_handler=None, service_handler_values=None):
    request_method_value,request_route_value=resolve_management_command(service_command_name,operation_command_name,command_payload_value)
    if gateway_request_handler is not None:
        if service_command_name == 'animationgpt':
            from workflow.common.animationgpt_model_download import WORKFLOW_ROOT_DIRECTORY, inspect_animationgpt_model_files
            from workflow.common.model_prepare_process import inspect_registered_preparation_strict, start_registered_preparation
            from workflow.common.management_transport import send_management_json_response
            try:
                preparation = inspect_registered_preparation_strict(WORKFLOW_ROOT_DIRECTORY, 'animationgpt')
            except (OSError, ValueError, TypeError, UnicodeError):
                preparation = 'unknown'
            ready = inspect_animationgpt_model_files()
            if operation_command_name == 'prepare' and preparation == 'unknown':
                raise ValueError('AnimationGPT 모델 준비 상태를 확인할 수 없습니다.')
            if operation_command_name == 'prepare' and preparation != 'running' and not ready:
                preparation = start_registered_preparation(WORKFLOW_ROOT_DIRECTORY, 'animationgpt')['preparation_status']
            return send_management_json_response(gateway_request_handler, 200, {'ready': ready, 'preparation_status': preparation, 'can_prepare': preparation != 'unknown', 'message': 'FP16 가중치·토크나이저·정규화 파일 해시 검증 완료 · 생성기 연결은 별도' if ready else '가중치·토크나이저·정규화 파일 준비 필요 · 생성기 연결은 별도'})
        if service_command_name == 'hermes-model':
            from workflow.common.hermes_model_download import WORKFLOW_ROOT_DIRECTORY, inspect_hermes_model_files
            from workflow.common.model_prepare_process import inspect_registered_preparation_strict, start_registered_preparation
            from workflow.common.management_transport import send_management_json_response
            try:
                current_preparation_status = inspect_registered_preparation_strict(WORKFLOW_ROOT_DIRECTORY, 'hermes-model')
            except (OSError, ValueError, TypeError, UnicodeError):
                current_preparation_status = 'unknown'
            current_model_ready = inspect_hermes_model_files()
            if operation_command_name == 'prepare' and current_preparation_status == 'unknown':
                raise ValueError('Hermes 모델 준비 상태를 확인할 수 없어 준비 요청을 보류합니다.')
            if operation_command_name == 'prepare' and current_preparation_status != 'running' and not current_model_ready:
                current_preparation_status = start_registered_preparation(WORKFLOW_ROOT_DIRECTORY, 'hermes-model')['preparation_status']
            from workflow.domains.hermes_agent.management_observer import inspect_hermes_model_status
            current_model_status = inspect_hermes_model_status(current_model_ready, current_preparation_status)
            return send_management_json_response(gateway_request_handler, 200, current_model_status)
        if service_command_name == 'prompt-translation' and operation_command_name in ('model-status', 'prepare'):
            if operation_command_name == 'model-status' and command_payload_value:
                raise ValueError('모델 상태 조회에는 입력을 전달할 수 없습니다.')
            from generators.prompt_translation.prepare import inspect_translation_model_files, WORKFLOW_ROOT_DIRECTORY
            from workflow.domains.translation.service import TRANSLATION_PYTHON_PATH
            from workflow.common.model_prepare_process import inspect_registered_preparation, start_registered_preparation
            from workflow.common.management_transport import send_management_json_response
            current_preparation_status = inspect_registered_preparation(WORKFLOW_ROOT_DIRECTORY, 'prompt-translation-model')
            current_models_ready = inspect_translation_model_files()
            if operation_command_name == 'prepare' and current_preparation_status != 'running' and not current_models_ready:
                current_preparation_status = start_registered_preparation(WORKFLOW_ROOT_DIRECTORY, 'prompt-translation-model')['preparation_status']
            current_status_message = '모델 파일 준비 완료 · 해시와 GPU 추론은 실행 시 확인' if current_models_ready else '모델 준비 필요 · Hugging Face 로그인 및 Gemma 약관 동의 확인'
            if current_preparation_status == 'failed':
                current_status_message += ' · 다운로드 실패: 모델 관리 로그 확인 후 다시 시도'
            if current_models_ready and not TRANSLATION_PYTHON_PATH.is_file():
                current_status_message += ' · ROCm 실행 환경 준비 필요'
            return send_management_json_response(gateway_request_handler, 200, {'ready': current_models_ready, 'generation_ready': current_models_ready and TRANSLATION_PYTHON_PATH.is_file(), 'message': current_status_message, 'preparation_status': current_preparation_status})
        if service_command_name == 'model-downloads':
            from workflow.common.management_transport import send_management_json_response
            if operation_command_name == 'download-inventory':
                from workflow.common.model_file_inventory import list_model_inventory_files
                return send_management_json_response(gateway_request_handler, 200, {'models': list_model_inventory_files()})
            if operation_command_name == 'download-observe':
                from workflow.common.model_download_records import observe_model_download_records
                current_issue_counts={'unavailable_count':0}
                current_observed_records=observe_model_download_records(current_issue_counts=current_issue_counts)
                return send_management_json_response(gateway_request_handler, 200, {'records':current_observed_records,**current_issue_counts})
            from workflow.common.model_download_records import list_model_download_records
            return send_management_json_response(gateway_request_handler, 200, {'records': list_model_download_records()})
        if service_command_name == 'expression-lora':
            from workflow.domains.image.expression_generation import validate_expression_adapter, WORKFLOW_ROOT_PATH
            from workflow.common.model_prepare_process import inspect_registered_preparation, start_registered_preparation
            from workflow.common.management_transport import send_management_json_response
            current_status_value = inspect_registered_preparation(WORKFLOW_ROOT_PATH, 'expression-lora')
            try:
                validate_expression_adapter()
                current_ready_value = True
                current_message_text = '표정 LoRA 파일과 SHA-256 검증 완료'
            except (OSError, ValueError) as current_validation_error:
                current_ready_value = False
                current_message_text = f'표정 LoRA 준비 필요: {current_validation_error}'
            if operation_command_name == 'prepare' and current_status_value != 'running' and not current_ready_value:
                current_status_value = start_registered_preparation(WORKFLOW_ROOT_PATH, 'expression-lora')['preparation_status']
            return send_management_json_response(gateway_request_handler, 200, {'ready': current_ready_value, 'message': current_message_text, 'preparation_status': current_status_value})
        if service_command_name == 'writer-agent' and operation_command_name in ('model-status', 'prepare'):
            from generators.writer_agent.prepare import WORKFLOW_REPOSITORY_ROOT, inspect_writer_model_files
            from workflow.common.model_prepare_process import inspect_detached_preparation, inspect_registered_preparation, start_registered_preparation
            from workflow.common.management_transport import send_management_json_response
            current_preparation_status = inspect_registered_preparation(WORKFLOW_REPOSITORY_ROOT, 'writer-model')
            if current_preparation_status != 'running' and inspect_detached_preparation(WORKFLOW_REPOSITORY_ROOT/'.local/model-preparation/writer-agent') == 'running':
                current_preparation_status = 'running'
            current_models_ready = inspect_writer_model_files()
            if operation_command_name == 'prepare' and current_preparation_status != 'running' and not current_models_ready:
                current_preparation_status = start_registered_preparation(WORKFLOW_REPOSITORY_ROOT, 'writer-model')['preparation_status']
            current_status_message = ('작가 AI 모델 파일 검증 완료 · 실행 환경은 별도 준비' if current_models_ready else
                                      '작가 AI 모델 파일 준비 필요 · 실행 환경은 별도 준비')
            if current_preparation_status == 'failed':
                current_status_message += ' · 이전 준비 실패, 작업 로그 확인 후 다시 시도하세요.'
            return send_management_json_response(gateway_request_handler, 200, {'ready': current_models_ready, 'message': current_status_message, 'preparation_status': current_preparation_status})
        if service_command_name in ('music-heartmula', 'sfx-dasheng-audiogen') and operation_command_name in ('download-model', 'download-model-status'):
            from workflow.common.audio_model_download import AUDIO_DOWNLOAD_PROFILES, WORKFLOW_ROOT_DIRECTORY, inspect_audio_download_files
            from workflow.common.model_prepare_process import inspect_registered_preparation, start_registered_preparation
            from workflow.common.management_transport import send_management_json_response
            current_profile_name = AUDIO_DOWNLOAD_PROFILES[service_command_name]
            if operation_command_name == 'download-model':
                from workflow.domains.music.generation import MusicGenerationManager
                current_music_manager = MusicGenerationManager(service_command_name)
                with current_music_manager.hold_music_lock():
                    current_preparation_status = inspect_registered_preparation(WORKFLOW_ROOT_DIRECTORY, current_profile_name)
                    current_models_ready = inspect_audio_download_files(service_command_name)
                    if current_preparation_status != 'running' and not current_models_ready:
                        current_music_manager.ensure_no_active_music_preparation(current_check_all_actions=True)
                        current_preparation_status = start_registered_preparation(WORKFLOW_ROOT_DIRECTORY, current_profile_name)['preparation_status']
            else:
                current_preparation_status = inspect_registered_preparation(WORKFLOW_ROOT_DIRECTORY, current_profile_name)
                current_models_ready = inspect_audio_download_files(service_command_name)
            current_status_message = '모델 파일 다운로드 완료 · 실행 환경과 GPU 검증은 별도 준비' if current_models_ready else '모델 파일 다운로드 필요 · 실행 환경은 별도 준비'
            if current_preparation_status == 'running':
                current_status_message = '모델 파일 다운로드 중 · 실행 환경과 GPU 검증은 별도 준비'
            if current_preparation_status == 'failed':
                current_status_message += ' · 이전 다운로드 실패, 로그 확인 후 다시 시도하세요.'
            return send_management_json_response(gateway_request_handler, 200, {'ready': current_models_ready, 'message': current_status_message, 'preparation_status': current_preparation_status})
        if operation_command_name == 'prioritize':
            from workflow.common.gpu_job_queue import prioritize_waiting_generation
            from workflow.common.management_transport import send_management_json_response
            return send_management_json_response(gateway_request_handler, 200, prioritize_waiting_generation(command_payload_value['id'],service_command_name))
        return service_handler_values[service_command_name](GatewayRequestAdapter(gateway_request_handler,request_method_value,request_route_value,command_payload_value))
    if service_command_name=='character-animation' and server_base_address is None:
        from workflow.domains.character_animation.character_animation_jobs import execute_animation_command
        return execute_animation_command(operation_command_name,command_payload_value)
    server_base_address=server_base_address or DEFAULT_GATEWAY_ADDRESS
    return call_management_api(server_base_address,request_route_value,command_payload_value if request_method_value=='POST' else None,operation_command_name!='logs')


def execute_gateway_arguments(service_command_name, command_argument_list):
    if service_command_name not in MANAGEMENT_COMMAND_DESCRIPTIONS:
        raise ValueError('알 수 없는 관리 서비스입니다.')
    command_argument_parser=argparse.ArgumentParser(prog=f'python3 tools/manager.py command {service_command_name}',description=MANAGEMENT_COMMAND_DESCRIPTIONS[service_command_name])
    command_argument_parser.add_argument('--server-url',default=os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS),help='독립 HTTP 게이트웨이 주소 (기본: 127.0.0.1:8771)')
    command_subparser_group=command_argument_parser.add_subparsers(dest='command',required=True)
    for operation_command_name in MANAGEMENT_SERVICE_COMMANDS[service_command_name]:
        operation_argument_parser=command_subparser_group.add_parser(operation_command_name)
        if operation_command_name == 'resume-reviewed':
            operation_argument_parser.add_argument('--payload-file',type=Path,required=True,help='검토한 작업 ID와 두 확인값 JSON')
        if operation_command_name in ('keyframe-save','keyframe-source-review','keyframe-save-reviewed'):
            operation_argument_parser.add_argument('--payload-file',type=Path,required=True,help='생성 ID·시도 ID·원본 프레임 번호·태그 JSON')
        if operation_command_name == 'keyframe-preview':
            operation_argument_parser.add_argument('id',help='저장된 키프레임 ID')
        if operation_command_name == 'keyframe-replace':
            operation_argument_parser.add_argument('--payload-file',type=Path,required=True,help='교체할 old_id와 사용할 new_id JSON')
        if operation_command_name == 'keyframe-retire':
            operation_argument_parser.add_argument('--payload-file',type=Path,required=True,help='폐기할 키프레임 ID 배열을 담은 JSON')
        if service_command_name=='momask' and operation_command_name=='generate':
            operation_argument_parser.add_argument('--face',action=argparse.BooleanOptionalAction,default=False,help='ANNY 얼굴 5점 포함')
        if operation_command_name in WRITER_PAYLOAD_COMMAND_NAMES + TRANSLATION_PAYLOAD_COMMAND_NAMES + HERMES_PAYLOAD_COMMAND_NAMES or operation_command_name in ('sheet-auto','sheet-export','sheet-gif','sheet-search','sheet-image','sheet-update','capture','export-vnccs','resize','map-anchor-save','effect-list','effect-load','effect-save','effect-register','effect-register-check','effect-register-reviewed','effect-replace','asset-list','asset-register','asset-preview','asset-save','asset-save-reviewed','asset-crop-preview','asset-crop','asset-retire-preview','asset-retire','map-edit-load','map-edit-preview','map-edit-save','city-edit-load','city-edit-preview','city-edit-save','building-list','building-save','building-register','building-retire','database-seed','database-status','database-sync','database-snapshot','database-restore'):
            operation_argument_parser.add_argument('--payload-file',type=Path,required=True,help='GUI와 동일한 명령 JSON 입력 파일')
        if operation_command_name=='anchor-save':operation_argument_parser.add_argument('--document-file',type=Path,required=True)
        if operation_command_name=='anchor-load':operation_argument_parser.add_argument('id')
        if operation_command_name in ('anchor-history','anchor-history-reset'):
            operation_argument_parser.add_argument('--animation-id',required=True)
            operation_argument_parser.add_argument('--animation-version',required=True)
        if operation_command_name in ('sprite-source','sprite-save','sprite-load','sprite-history','sprite-history-reset','sprite-history-delete'):
            operation_argument_parser.add_argument('id')
            if operation_command_name=='sprite-history-delete':operation_argument_parser.add_argument('--revision',required=True)
            if operation_command_name=='sprite-save':operation_argument_parser.add_argument('--document-file',type=Path,required=True)
        if operation_command_name in ('status','logs','cancel','resume','resume-preview','pause','history-delete','prioritize'):
            operation_argument_parser.add_argument('id')
        if operation_command_name in ('generate','export-vnccs'):
            operation_argument_parser.add_argument('--detach',action='store_true',help='작업 ID 출력 후 반환')
        if operation_command_name in ('generate','queue'):
            operation_argument_parser.add_argument('--tag',default='',help='생성 이력 구분 태그, 최대 80자')
            if service_command_name in AUDIO_SERVICE_NAMES:
                try:
                    from generators.music.contracts import load_music_defaults
                    current_music_defaults = load_music_defaults(service_command_name)
                except ModuleNotFoundError:
                    if '--help' not in command_argument_list and '-h' not in command_argument_list:
                        raise
                    current_music_defaults = {'duration_seconds': None, 'seed': None, 'loop_request': None}
                    operation_argument_parser.description = '기본 설정은 관리 환경을 준비한 후 확인할 수 있습니다.'
                current_prompt_group = operation_argument_parser.add_mutually_exclusive_group(required=True)
                current_prompt_group.add_argument('--prompt')
                current_prompt_group.add_argument('--prompt-file',type=Path)
                if service_command_name == 'sfx-dasheng-audiogen':
                    operation_argument_parser.set_defaults(duration_seconds=None)
                elif service_command_name == 'music-heartmula':
                    operation_argument_parser.add_argument('--lyrics',help='가사·구간 태그; 반주 입력 방식은 검증 전')
                    operation_argument_parser.add_argument('--duration-seconds',type=float,default=current_music_defaults['duration_seconds'],help='최대 출력 시간(초), max_audio_length_ms로 환산 예정')
                elif service_command_name == 'music-magenta':
                    operation_argument_parser.add_argument('--duration-seconds',type=float,default=current_music_defaults['duration_seconds'],help='실험 길이(초); GPU 경로 검증 전 실행 차단')
                else:
                    current_lyrics_group = operation_argument_parser.add_mutually_exclusive_group()
                    current_lyrics_group.add_argument('--lyrics',help='별도 가사 입력; 지정 시 반주 문구 자동 추가 해제')
                    current_lyrics_group.add_argument('--lyrics-file',type=Path,help='UTF-8 가사 파일')
                    operation_argument_parser.add_argument('--min-duration-seconds',type=float,default=0,help='실험: 이 길이까지 종료 토큰 억제; 0은 해제, 품질 보장 없음')
                    current_duration_group = operation_argument_parser.add_mutually_exclusive_group()
                    current_duration_group.add_argument('--duration-seconds',type=float,default=current_music_defaults['duration_seconds'],help='최대 길이(초); 조기 종료 가능')
                    current_duration_group.add_argument('--max-new-tokens',type=int,help='MiniMax 오디오 프레임 상한 125~3000; 25개≈1초, 조기 종료 가능')
                operation_argument_parser.add_argument('--seed',type=int,default=current_music_defaults['seed'])
                operation_argument_parser.add_argument('--loop-request',action=argparse.BooleanOptionalAction,default=current_music_defaults['loop_request'],help='반복 구조 요청; 심리스 연결 보장 없음')
            elif service_command_name in ('wan22-fun-control','wan22-vace','kimodo','wan22-animate2','dwpose'):
                operation_argument_parser.add_argument('--payload-file',type=Path,required=True,help='action=generate, images=[PNG base64], pose_include_hands/pose_include_face bool JSON' if service_command_name=='dwpose' else 'Kimodo 텍스트·프레임·샘플링·키프레임 배치 JSON 요청' if service_command_name=='kimodo' else 'images PNG base64와 driving_video MP4 base64, prompt, frames, steps, seed, width, height JSON 요청' if service_command_name=='wan22-animate2' else 'images PNG base64와 frame_entries를 포함한 JSON 요청')
            elif service_command_name=='character-animation':
                operation_argument_parser.add_argument('--steps',type=int,choices=(4,30),default=None,help='4: Lightning, 30: 표준 생성 (기본 4)')
                operation_argument_parser.add_argument('--resolution',type=int,choices=(512,768,1024,1280),default=512)
                operation_argument_parser.add_argument('--speed',type=float,choices=(1,2,4),help='원본 프레임 선택 간격. 기본 2, 2는 1·3·5… 프레임 선택')
                operation_argument_parser.add_argument('--target-fps',type=int,choices=(8,),help='초당 생성 장수. 8만 지원 (기본 8, 생성 배속 기본 2)')
                operation_argument_parser.add_argument('--start-frame',type=int,help='생성할 시작 프레임 (기본 1)')
                operation_argument_parser.add_argument('--end-frame',type=int,help='생성할 종료 프레임 (기본 모션 마지막)')
                operation_argument_parser.add_argument('--motion',required=True,help='catalog의 모션 ID')
                current_reference_group=operation_argument_parser.add_mutually_exclusive_group(required=True)
                current_reference_group.add_argument('--character',help='기존 등록 캐릭터 ID · 호환용')
                current_reference_group.add_argument('--reference',type=Path,help='캐릭터 참조 PNG 한 장 · 단일 방향 생성')
                operation_argument_parser.add_argument('--source',choices=('openpose','anny'),default='anny')
                operation_argument_parser.add_argument('--directions',nargs='+',choices=('down_left','down_right','up_left','up_right'),default=['down_left'],help='생성 방향 (기본: 전방 좌측만)')
            elif service_command_name=='momask':
                operation_argument_parser.add_argument('--action',choices=('standing','walking','resting','custom'),required=True)
                operation_argument_parser.add_argument('--prompt',help='커스텀 포즈의 모션 스크립트')
                operation_argument_parser.add_argument('--frames',type=int,help='원본 모션 프레임 길이 · 8 이상 4의 배수')
                operation_argument_parser.add_argument('--directions',nargs='+',choices=('down_left','down_right','up_left','up_right'),default=['down_left','down_right','up_left','up_right'])
            else:
                prompt_argument_group=operation_argument_parser.add_mutually_exclusive_group(required=service_command_name not in ('outfit-transfer',))
                if service_command_name in ('expression', 'flux-expression'):
                    try:
                        from workflow.domains.image.expression_generation import load_expression_configuration
                        current_expression_choices = [current_expression_record['id'] for current_expression_record in load_expression_configuration()['expressions']]
                        current_expression_help = '표정 프리셋 ID (AU 참고 기반)'
                    except ModuleNotFoundError:
                        if '--help' not in command_argument_list and '-h' not in command_argument_list:
                            raise
                        current_expression_choices = None
                        current_expression_help = '표정 프리셋 ID; 목록은 관리 환경을 준비한 후 확인'
                    prompt_argument_group.add_argument('--expression','--prompt',dest='prompt',choices=current_expression_choices,help=current_expression_help)
                else:
                    if service_command_name in ('outfit-transfer',):
                        operation_argument_parser.add_argument('--resolution',type=int,choices=(512,768),default=768,help='정사각형 해상도 (기본 768)')
                    prompt_argument_group.add_argument('--prompt')
                prompt_argument_group.add_argument('--prompt-file',type=Path,help='UTF-8 프롬프트 파일')
                if service_command_name == 'flux-building':
                    prompt_argument_group.add_argument('--design-ko',help='번역 대기열에 보낼 한국어 건물 디자인')
                if service_command_name in FLUX_IMAGE_PROFILE_RECORDS and service_command_name != 'flux-building' or service_command_name == 'flux-expression':
                    operation_argument_parser.add_argument('--translation-ko',help='영어 준비 문구에 결합할 한국어 설명')
                operation_argument_parser.add_argument('--width',type=int,default=768 if service_command_name=='flux-expression' else FLUX_IMAGE_PROFILE_RECORDS[service_command_name][2] if service_command_name in FLUX_IMAGE_PROFILE_RECORDS else None if service_command_name=='seamless-tile' else 512 if service_command_name=='qwen-21-circular' else 768 if service_command_name in ('mannequin-generator','billboard-generator','prop-generator','vegetation-generator','building-generator','qwen-21','outfit-transfer') else 512 if service_command_name in ('qwen-2511','expression','floor-tile') else 1024)
                operation_argument_parser.add_argument('--height',type=int,default=512 if service_command_name=='flux-expression' else FLUX_IMAGE_PROFILE_RECORDS[service_command_name][3] if service_command_name in FLUX_IMAGE_PROFILE_RECORDS else None if service_command_name=='seamless-tile' else 512 if service_command_name=='qwen-21-circular' else 768 if service_command_name in ('mannequin-generator','billboard-generator','prop-generator','vegetation-generator','building-generator','qwen-21','outfit-transfer') else 512 if service_command_name in ('qwen-2511','expression','floor-tile') else 1024)
                operation_argument_parser.add_argument('--steps',type=int,choices=range(1,51) if service_command_name=='flux-character' else (16,) if service_command_name=='flux-expression' or service_command_name in FLUX_IMAGE_PROFILE_RECORDS else (20,30,40,50) if service_command_name in ('mannequin-generator','billboard-generator','prop-generator','vegetation-generator','building-generator','qwen-21','qwen-21-circular','outfit-transfer','expression') else (40,) if service_command_name=='seamless-tile' else (4,) if service_command_name=='floor-tile' else (4,30),default=16 if service_command_name=='flux-expression' or service_command_name in FLUX_IMAGE_PROFILE_RECORDS else 40 if service_command_name in ('mannequin-generator','seamless-tile','billboard-generator','prop-generator','vegetation-generator','building-generator','qwen-21','qwen-21-circular','outfit-transfer','expression') else 4)
                if service_command_name == 'flux-seamless':
                    operation_argument_parser.add_argument('--seamless-method', choices=('global-periodic-v1',), default='global-periodic-v1', help='심리스 처리 방식 (전역 주기 어텐션 + 순환 VAE)')
                if service_command_name in ('mannequin-generator','billboard-generator','prop-generator','vegetation-generator','building-generator','qwen-21'):
                    operation_argument_parser.add_argument('--transparent-background', action=argparse.BooleanOptionalAction, default=False, help='네이티브 RGBA 투명 배경 요청')
                if service_command_name == 'mannequin-generator':
                    operation_argument_parser.add_argument('--reference-resolution', type=int, choices=(992, 1024, 1056), default=None, help='실험용 참조 처리 해상도')
                    operation_argument_parser.add_argument('--diagnostic-vae-roundtrip', action='store_true', help='실험용 참조 VAE 왕복 비교 기록')
                if service_command_name == 'qwen-21-circular':
                    operation_argument_parser.add_argument('--baseline-decode', action=argparse.BooleanOptionalAction, default=False, help='일반 VAE 비교 생성 · 기본 OFF')
                    operation_argument_parser.add_argument('--pattern-view', action=argparse.BooleanOptionalAction, default=True, help='Top view. Repeat pattern. Close-up 추가')
                    operation_argument_parser.add_argument('--soft-shading', action=argparse.BooleanOptionalAction, default=False, help='부드러운 음영 일러스트 영문 지시 추가')
                    operation_argument_parser.add_argument('--circular-radius', type=int, choices=(4,8,12,16,24), default=12, help='순환 참조 반경 · 토큰')
                operation_argument_parser.add_argument('--seed',type=int,default=10107 if service_command_name in ('mannequin-generator','qwen-2511','expression','seamless-tile','billboard-generator','prop-generator','vegetation-generator','building-generator','qwen-21','qwen-21-circular','outfit-transfer') else 251204)
                if service_command_name=='floor-tile':
                    operation_argument_parser.add_argument('--add-margins',action=argparse.BooleanOptionalAction,default=None,help='빈 여백 추가 ON/OFF (--no-add-margins로 OFF, 생략 시 서버 기본값)')
                if service_command_name in FLUX_IMAGE_PROFILE_RECORDS or service_command_name in ('mannequin-generator','qwen-2511','expression','flux-expression','seamless-tile','billboard-generator','prop-generator','vegetation-generator','building-generator','qwen-21','qwen-21-circular','outfit-transfer'):
                    current_reference_help='새 심리스 작업은 참조 이미지를 지원하지 않습니다.' if service_command_name == 'flux-seamless' else '임의 해상도의 불투명 RGB/RGBA PNG, 장당 3MB 이하, 최대 '+('2' if service_command_name in FLUX_IMAGE_PROFILE_RECORDS else '1' if service_command_name == 'flux-expression' else '10' if service_command_name in ('mannequin-generator','billboard-generator','prop-generator','vegetation-generator','building-generator','qwen-21','qwen-21-circular','outfit-transfer') else '3')+'장'
                    operation_argument_parser.add_argument('--reference',type=Path,action='append',default=[],help=current_reference_help)
    command_argument_values=command_argument_parser.parse_args(command_argument_list)
    server_base_address=command_argument_values.server_url
    if server_base_address is not None:
        server_base_address=server_base_address.rstrip('/')
        server_address_parts=urlsplit(server_base_address)
        if server_address_parts.scheme!='http' or server_address_parts.hostname not in ('127.0.0.1','localhost') or server_address_parts.username or server_address_parts.password or server_address_parts.path or server_address_parts.query or server_address_parts.fragment:
            raise ValueError('관리도구 주소는 http://127.0.0.1:포트 또는 http://localhost:포트 형식이어야 합니다.')
    operation_command_name=command_argument_values.command
    command_payload_value={}
    if operation_command_name in ('keyframe-save','keyframe-source-review','keyframe-save-reviewed','resume-reviewed'):
        command_payload_value=parse_management_request_json(command_argument_values.payload_file.read_text())
    if operation_command_name in ('keyframe-replace','keyframe-retire'):
        command_payload_value=parse_management_request_json(command_argument_values.payload_file.read_text())
    if hasattr(command_argument_values,'face'):command_payload_value['face']=command_argument_values.face
    if hasattr(command_argument_values,'id'):
        command_payload_value['id']=command_argument_values.id
    if operation_command_name in ('sprite-source','sprite-save','sprite-load','sprite-history','sprite-history-reset','sprite-history-delete'):
        command_payload_value={'id':command_argument_values.id}
        if operation_command_name=='sprite-history-delete':command_payload_value['revision']=command_argument_values.revision
        if operation_command_name=='sprite-save':command_payload_value['document']=parse_management_request_json(command_argument_values.document_file.read_text())
    if operation_command_name in WRITER_PAYLOAD_COMMAND_NAMES + TRANSLATION_PAYLOAD_COMMAND_NAMES + HERMES_PAYLOAD_COMMAND_NAMES or operation_command_name in ('sheet-auto','sheet-export','sheet-gif','sheet-search','sheet-image','sheet-update','capture','export-vnccs','resize','map-anchor-save','effect-list','effect-load','effect-save','effect-register','effect-register-check','effect-register-reviewed','effect-replace','asset-list','asset-register','asset-preview','asset-save','asset-save-reviewed','asset-crop-preview','asset-crop','asset-retire-preview','asset-retire','map-edit-load','map-edit-preview','map-edit-save','city-edit-load','city-edit-preview','city-edit-save','building-list','building-save','building-register','building-retire','database-seed','database-status','database-sync','database-snapshot','database-restore'):command_payload_value=parse_management_request_json(command_argument_values.payload_file.read_text())
    if operation_command_name=='anchor-save':command_payload_value={'document':parse_management_request_json(command_argument_values.document_file.read_text())}
    if operation_command_name in ('anchor-history','anchor-history-reset'):command_payload_value={'animation_id':command_argument_values.animation_id,'animation_version':command_argument_values.animation_version}
    if operation_command_name=='history-reset':command_payload_value={'action':'reset'}
    if operation_command_name=='prepare':command_payload_value={'action':'prepare'}
    if operation_command_name in ('generate','queue'):
        if service_command_name in AUDIO_SERVICE_NAMES:
            command_payload_value = {'action':'generate','prompt':command_argument_values.prompt if command_argument_values.prompt is not None else command_argument_values.prompt_file.read_text(),
                'duration_seconds':command_argument_values.duration_seconds,'seed':command_argument_values.seed,'loop_request':command_argument_values.loop_request,'tag':command_argument_values.tag}
            if getattr(command_argument_values,'lyrics',None) is not None:
                command_payload_value['lyrics'] = command_argument_values.lyrics
            elif getattr(command_argument_values,'lyrics_file',None) is not None:
                command_payload_value['lyrics'] = command_argument_values.lyrics_file.read_text(encoding='utf-8')
            if getattr(command_argument_values,'min_duration_seconds',0):
                command_payload_value['min_duration_seconds'] = command_argument_values.min_duration_seconds
            if getattr(command_argument_values,'max_new_tokens',None) is not None:
                command_payload_value.pop('duration_seconds')
                command_payload_value['max_new_tokens'] = command_argument_values.max_new_tokens
        elif service_command_name in ('wan22-fun-control','wan22-vace','kimodo','wan22-animate2','dwpose'):
            command_payload_value=parse_management_request_json(command_argument_values.payload_file.read_text())
        elif service_command_name=='character-animation':
            command_payload_value={'motion':command_argument_values.motion,'character':command_argument_values.character,'source':command_argument_values.source,'directions':command_argument_values.directions}
            if command_argument_values.reference:
                if command_argument_values.reference.stat().st_size>8_000_000:raise ValueError('캐릭터 참조는 8MB 이하여야 합니다.')
                command_payload_value.pop('character')
                command_payload_value['character_image']=base64.b64encode(command_argument_values.reference.read_bytes()).decode()
            if command_argument_values.tag:command_payload_value['tag']=command_argument_values.tag
            command_payload_value['resolution']=command_argument_values.resolution
            if command_argument_values.steps is not None:command_payload_value['steps']=command_argument_values.steps
            if command_argument_values.speed is not None:command_payload_value['speed']=command_argument_values.speed
            if command_argument_values.target_fps is not None:command_payload_value['target_fps']=command_argument_values.target_fps
            if command_argument_values.start_frame is not None:command_payload_value['start_frame']=command_argument_values.start_frame
            if command_argument_values.end_frame is not None:command_payload_value['end_frame']=command_argument_values.end_frame
        elif service_command_name=='momask':
            command_payload_value={'action':command_argument_values.action,'directions':command_argument_values.directions,'face':command_argument_values.face}
            if command_argument_values.frames is not None:command_payload_value['frames']=command_argument_values.frames
            if command_argument_values.prompt is not None:command_payload_value['prompt']=command_argument_values.prompt
            if command_argument_values.tag:command_payload_value['tag']=command_argument_values.tag
        else:
            current_design_text=getattr(command_argument_values,'design_ko',None)
            command_payload_value={'action':'generate','prompt':command_argument_values.prompt if command_argument_values.prompt is not None else command_argument_values.prompt_file.read_text(encoding='utf-8') if command_argument_values.prompt_file else current_design_text if current_design_text is not None else (__import__('workflow.domains.image.outfit_transfer_generation',fromlist=['load_outfit_transfer_prompt']).load_outfit_transfer_prompt()),'width':command_argument_values.width,'height':command_argument_values.height,'steps':command_argument_values.steps,'seed':command_argument_values.seed}
            if current_design_text is not None: command_payload_value['building_design_ko']=current_design_text
            if getattr(command_argument_values,'translation_ko',None): command_payload_value['translation_source_ko']=command_argument_values.translation_ko
            if service_command_name == 'flux-seamless': command_payload_value['seamless_method']=command_argument_values.seamless_method
            if service_command_name in ('outfit-transfer',):
                command_payload_value['width']=command_argument_values.resolution
                command_payload_value['height']=command_argument_values.resolution
            if service_command_name=='seamless-tile':
                for current_size_key in ('width','height'):
                    if command_payload_value[current_size_key] is None:
                        command_payload_value[current_size_key]=768
            if command_argument_values.tag:command_payload_value['tag']=command_argument_values.tag
            if service_command_name=='floor-tile':
                command_payload_value['user_prompt']=command_payload_value.pop('prompt')
                if command_argument_values.add_margins is not None:
                    command_payload_value['add_margins']=command_argument_values.add_margins
            if service_command_name in ('mannequin-generator','billboard-generator','prop-generator','vegetation-generator','building-generator','qwen-21'):
                command_payload_value['transparent_background'] = command_argument_values.transparent_background
            if service_command_name == 'mannequin-generator' and command_argument_values.reference_resolution is not None:
                command_payload_value['reference_resolution'] = command_argument_values.reference_resolution
            if service_command_name == 'mannequin-generator' and command_argument_values.diagnostic_vae_roundtrip:
                command_payload_value['vae_roundtrip_diagnostic'] = True
            if service_command_name == 'qwen-21-circular':
                command_payload_value['circular_radius'] = command_argument_values.circular_radius
                command_payload_value['soft_shading'] = command_argument_values.soft_shading
                command_payload_value['pattern_view'] = command_argument_values.pattern_view
                command_payload_value['baseline_decode'] = command_argument_values.baseline_decode
            if service_command_name in FLUX_IMAGE_PROFILE_RECORDS or service_command_name in ('mannequin-generator','qwen-2511','expression','flux-expression','seamless-tile','billboard-generator','prop-generator','vegetation-generator','building-generator','qwen-21','qwen-21-circular','outfit-transfer'):
                if service_command_name in ('outfit-transfer',) and len(command_argument_values.reference) != 2:
                    raise ValueError('바디 이미지와 아웃핏 이미지를 --reference로 순서대로 지정하세요.' if service_command_name == 'outfit-transfer' else '아이덴티티 이미지 1장과 포즈 이미지 1장이 필요합니다. --reference를 순서대로 두 번 지정하세요.')
                maximum_reference_count = 2 if service_command_name in FLUX_IMAGE_PROFILE_RECORDS else 1 if service_command_name == 'flux-expression' else 10 if service_command_name in ('mannequin-generator','billboard-generator','prop-generator','vegetation-generator','building-generator','qwen-21','qwen-21-circular','outfit-transfer') else 3
                if len(command_argument_values.reference) > maximum_reference_count:
                    raise ValueError(f'참조 이미지는 최대 {maximum_reference_count}장입니다.')
                command_payload_value['images']=[]
                for reference_image_path in command_argument_values.reference:
                    if reference_image_path.stat().st_size>3_000_000:raise ValueError('참조 이미지 크기 제한 초과')
                    command_payload_value['images'].append(base64.b64encode(reference_image_path.read_bytes()).decode())
    command_response_value=execute_management_command(service_command_name,operation_command_name,command_payload_value,server_base_address)
    print(command_response_value if isinstance(command_response_value,str) else json.dumps(command_response_value,ensure_ascii=False,indent=2),flush=True)
    if operation_command_name not in ('generate','export-vnccs') or command_argument_values.detach:return 0
    generation_job_identifier=command_response_value['id']
    previous_status_text=None
    try:
        while True:
            generation_status_value=execute_management_command(service_command_name,'status',{'id':generation_job_identifier},server_base_address)
            current_status_text=json.dumps(generation_status_value,ensure_ascii=False)
            if current_status_text!=previous_status_text:
                print(current_status_text,flush=True)
                previous_status_text=current_status_text
            if generation_status_value['status'] not in ('running','queued'):
                return 0 if generation_status_value['status'] in ('completed','paused') else 1
            time.sleep(1)
    except KeyboardInterrupt:
        execute_management_command(service_command_name,'cancel',{'id':generation_job_identifier},server_base_address)
        print('취소 요청을 전달했습니다.',flush=True)
        return 130


def inspect_registered_model_operation(current_service_name, current_command_names, current_action_name):
    """등록된 명령과 실제 게이트웨이 정책이 모두 허용하는 모델 동작만 표시한다."""
    current_candidates_list = (('download-model-status', 'model-status') if current_action_name == 'status' else ('download-model', 'prepare'))
    for current_operation_name in current_candidates_list:
        if current_operation_name not in current_command_names:
            continue
        current_payload_record = {'action': 'prepare'} if current_operation_name == 'prepare' else {}
        try:
            resolve_management_command(current_service_name, current_operation_name, current_payload_record)
        except ValueError:
            continue
        return current_operation_name
    return None


def execute_gateway_cli(command_argument_list=None):
    management_argument_parser = argparse.ArgumentParser(description=__doc__)
    management_subparser_group = management_argument_parser.add_subparsers(dest='tool', required=True)
    command_argument_parser = management_subparser_group.add_parser('command', help='관리 명령 실행')
    command_argument_parser.add_argument('service', choices=MANAGEMENT_SERVICE_COMMANDS)
    command_argument_parser.add_argument('arguments', nargs=argparse.REMAINDER)
    help_argument_parser = management_subparser_group.add_parser('help', help='지원 명령과 사용법 조회')
    help_argument_parser.add_argument('service', nargs='?', choices=MANAGEMENT_SERVICE_COMMANDS)
    help_argument_parser.add_argument('arguments', nargs=argparse.REMAINDER)
    model_argument_parser = management_subparser_group.add_parser('model', help='등록된 서비스의 모델 상태와 준비')
    model_argument_parser.add_argument('action', choices=('list', 'status', 'prepare'))
    model_argument_parser.add_argument('service', nargs='?')
    model_argument_parser.add_argument('--server-url', default=None)
    management_argument_values = management_argument_parser.parse_args(command_argument_list)
    if management_argument_values.tool == 'model':
        current_model_services = {current_service_name: current_command_names for current_service_name, current_command_names in MANAGEMENT_SERVICE_COMMANDS.items()
                                  if 'model-status' in current_command_names or 'download-model-status' in current_command_names}
        if management_argument_values.action == 'list':
            if management_argument_values.service or management_argument_values.server_url:
                model_argument_parser.error('model list는 서비스나 서버 주소를 받지 않습니다.')
            print(json.dumps({current_service_name: {'status': inspect_registered_model_operation(current_service_name, current_command_names, 'status'),
                  'prepare': inspect_registered_model_operation(current_service_name, current_command_names, 'prepare'),
                  'qwen_archived': current_service_name in ARCHIVED_QWEN_IMAGE_SERVICES,
                  'retired': current_service_name in ARCHIVED_QWEN_IMAGE_SERVICES or current_service_name in RETIRED_AUDIO_SERVICE_NAMES or current_service_name in ('qwen-2511', 'floor-tile', 'expression-lora')}
                for current_service_name, current_command_names in current_model_services.items()}, ensure_ascii=False, indent=2))
            return 0
        current_service_name = management_argument_values.service
        if current_service_name not in current_model_services:
            model_argument_parser.error('모델 상태 명령이 등록된 서비스를 지정하세요. model list로 확인할 수 있습니다.')
        current_command_names = current_model_services[current_service_name]
        current_operation_name = inspect_registered_model_operation(current_service_name, current_command_names, management_argument_values.action)
        if current_operation_name is None:
            model_argument_parser.error('현재 서비스 정책에서 해당 모델 명령을 지원하지 않습니다. model list로 확인하세요.')
        current_forward_arguments = (['--server-url', management_argument_values.server_url] if management_argument_values.server_url else []) + [current_operation_name]
        return execute_gateway_arguments(current_service_name, current_forward_arguments)
    if management_argument_values.tool == 'help':
        if not management_argument_values.service:
            management_argument_parser.print_help()
            for service_command_name, service_description_text in MANAGEMENT_COMMAND_DESCRIPTIONS.items():
                print(f'  {service_command_name}: {service_description_text}')
            print('\n예: python3 tools/manager.py help kimodo generate')
            return 0
        return execute_gateway_arguments(management_argument_values.service,management_argument_values.arguments+['--help'])
    return execute_gateway_arguments(management_argument_values.service,management_argument_values.arguments)


def call_management_api(server_base_address, request_route_path, request_body_value=None, expect_json_response=True):
    request_header_values = {'Origin':server_base_address}
    request_body_bytes = None
    if request_body_value is not None:
        request_body_bytes = json.dumps(request_body_value,ensure_ascii=False,allow_nan=False).encode()
        request_header_values['Content-Type']='application/json'
    command_envelope_parts=identify_management_command(request_route_path,'POST' if request_body_value is not None else 'GET',request_body_value)
    if command_envelope_parts is None:raise ValueError('지원하지 않는 관리 명령 경로')
    service_command_name,operation_command_name,command_payload_value=command_envelope_parts
    if service_command_name=='writer-agent' and operation_command_name in WRITER_PAYLOAD_COMMAND_NAMES:
        current_token_command='writer-token' if operation_command_name in ('writer-history-observe','writer-cancel','writer-material-page') else 'writer-state'
        current_writer_state=execute_management_command('writer-agent',current_token_command,{},server_base_address)
        request_header_values['X-Writer-Token']=current_writer_state['csrf_token']
    request_route_path='/management/command'
    request_body_bytes=json.dumps({'service':service_command_name,'command':operation_command_name,'payload':command_payload_value},ensure_ascii=False,allow_nan=False).encode()
    request_header_values['Content-Type']='application/json'
    management_request_value = urllib.request.Request(server_base_address+request_route_path, data=request_body_bytes, headers=request_header_values)
    current_request_started = time.monotonic()
    try:
        with urllib.request.urlopen(management_request_value, timeout=180 if operation_command_name=='capture' else 30) as management_response_handle:
            response_body_text = management_response_handle.read().decode()
        return json.loads(response_body_text) if expect_json_response else response_body_text
    except urllib.error.HTTPError as management_http_error:
        with management_http_error:
            current_error_bytes = management_http_error.read(16001)
        current_error_truncated = len(current_error_bytes) > 16000
        response_error_text = current_error_bytes[:16000].decode(errors='replace')
        if not current_error_truncated:
            try:
                current_error_document = json.loads(response_error_text)
                if isinstance(current_error_document,dict):response_error_text=current_error_document.get('error',response_error_text)
            except ValueError:
                pass
        if current_error_truncated:response_error_text += ' … (오류 응답 일부만 표시)'
        raise ValueError(f'관리 API 오류 ({management_http_error.code}): {response_error_text}') from None
    except (urllib.error.URLError, TimeoutError, ConnectionError) as management_connection_error:
        current_failure_reason = getattr(management_connection_error, 'reason', management_connection_error)
        current_connection_record = {
            'service': service_command_name, 'command': operation_command_name,
            'gateway': server_base_address, 'method': 'POST', 'route': request_route_path,
            'elapsed_seconds': round(time.monotonic() - current_request_started, 3),
            'error_type': type(current_failure_reason).__name__, 'reason': str(current_failure_reason),
        }
        # 요청 본문·인증 헤더는 기록하지 않는다. GUI/CLI 실행 로그에 같은 진단을 남긴다.
        print(f'{datetime.now().astimezone().isoformat()}/management-client/connection-failed '
              + json.dumps(current_connection_record, ensure_ascii=False), file=sys.stderr, flush=True)
        raise ValueError(
            f'관리 게이트웨이 연결 실패: {server_base_address} · {service_command_name}/{operation_command_name} · '
            f'{type(current_failure_reason).__name__}: {current_failure_reason}. '
            'GUI 서버와 별도로 게이트웨이 실행·포트를 확인하세요. '
            '실행: scripts/run_management_gateway.sh --watch · 로그: .tmp/gateway-server-logs/. '
            '요청은 자동 재전송하지 않았습니다. 생성 요청이었다면 이력을 확인한 뒤 재시도하세요.'
        ) from management_connection_error

"""Prepare forms for newly completed conversation proposals, including after restart."""
import json
import logging
from pathlib import Path
import re

from workflow.domains.hermes_agent.delegation_proposal import parse_hermes_image_proposal, parse_hermes_video_proposal
from workflow.domains.hermes_agent.image_selection import select_image_proposal
from workflow.domains.hermes_agent.video_selection import select_video_proposal


def advance_form_marker(path, dispatch):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024:
        raise ValueError('폼 준비 기록 오류')
    marker = json.loads(path.read_text(encoding='utf-8'))
    session, job = marker.get('session_id'), marker.get('job_id')
    if set(marker) != {'session_id', 'job_id'} or not isinstance(session, str) or not re.fullmatch(r'[a-f0-9]{32}', session) or not isinstance(job, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}', job) or path.parent.name != job:
        raise ValueError('폼 준비 원본 오류')
    detail = dispatch('hermes-detail', {'id':job})
    state = detail.get('status', {}).get('status')
    if state in ('queued', 'running', 'unknown'):
        return 'waiting'
    if state != 'completed':
        if state not in ('failed', 'cancelled', 'canceled'):
            return 'waiting'
        path.unlink()
        return 'skipped'
    answer, request = detail.get('final_response'), detail.get('request')
    if detail.get('final_response_truncated') or not isinstance(answer, str) or not isinstance(request, dict):
        return 'waiting'
    # Other tools and incomplete/ambiguous proposals do not create instances.
    service = None
    try:
        if any(marker in answer for marker in ('HERMES_IMAGE_PROPOSAL', 'HERMES_FLUX_PROPOSAL')):
            value = select_image_proposal(parse_hermes_image_proposal(answer), request)
            if value.get('service') == 'minimax-h3-image': service = value['service']
        elif 'HERMES_VIDEO_PROPOSAL' in answer:
            value = select_video_proposal(parse_hermes_video_proposal(answer), request)
            if value.get('service') == 'minimax-h3-i2v': service = value['service']
    except ValueError:
        path.unlink()
        return 'skipped'
    if not service:
        path.unlink()
        return 'skipped'
    # The gateway validates the completed job and session again.  An interrupted
    # prepare is idempotent and the marker remains until it succeeds.
    dispatch('hermes-minimax-form-prepare', {'session_id':session, 'proposal_job_id':job, 'service':service})
    path.unlink()
    return 'prepared'


def watch_form_markers(root, stop, dispatch, interval=5):
    root = Path(root) / '.tmp/test/hermes-agent/jobs'
    logger = logging.getLogger(__name__)
    while not stop.is_set():
        if root.is_dir() and not root.is_symlink():
            for marker in root.glob('*/minimax-form-pending.json'):
                if stop.is_set(): return
                if marker.parent.is_symlink(): continue
                try:
                    advance_form_marker(marker, dispatch)
                except (OSError, RuntimeError, ValueError, TypeError, KeyError):
                    logger.warning('MiniMax 폼 준비를 확인할 수 없습니다 (%s)', marker.parent.name)
        stop.wait(interval)

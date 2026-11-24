"""Create a read-only relocation assessment; it does not approve a move."""
import os
import posixpath
import stat
from pathlib import Path, PurePosixPath

from workflow.common.model_catalog import validate_catalog


def assess_relocation(catalog, survey, component_id, destination):
    validate_catalog(catalog)
    if survey.get('version') != 1 or not isinstance(survey.get('entries'), list):
        raise ValueError('조사 결과를 확인할 수 없습니다.')
    component = next((item for item in catalog['components'] if item['id'] == component_id), None)
    if component is None:
        raise ValueError('등록된 구성요소가 아닙니다.')
    if not isinstance(destination, str) or not destination or '\\' in destination or '\x00' in destination:
        raise ValueError('대상 경로가 올바르지 않습니다.')
    target = PurePosixPath(destination)
    source = PurePosixPath(component['path'])
    if (target.is_absolute() or '..' in target.parts or target.as_posix() != destination or destination == '.'
            or target == source or target in source.parents or source in target.parents):
        raise ValueError('서로 겹치지 않는 모델 루트 상대 경로가 필요합니다.')
    entry = next((item for item in survey['entries'] if item.get('path') == component['path']), None)
    links = survey.get('links', [])
    related_links = []
    for link in links:
        link_path = PurePosixPath(link['path'])
        raw_target = link.get('target', '')
        # Lexical normalization only: never dereference links in this assessment.
        resolved = posixpath.normpath(posixpath.join(str(link_path.parent), raw_target))
        if (link_path == source or source in link_path.parents or resolved == str(source)
                or resolved.startswith(str(source) + '/')):
            related_links.append(link)
    root = Path(survey.get('root', ''))
    destination_ancestor = 'unknown'
    try:
        if not root.is_absolute() or not root.is_dir():
            destination_exists = None
        else:
            destination_ancestor = 'clear'
            ancestor = root
            for segment in target.parts[:-1]:
                ancestor /= segment
                try:
                    info = os.lstat(ancestor)
                except FileNotFoundError:
                    break
                if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                    destination_ancestor = 'unsafe'
                    break
            try:
                os.lstat(root / destination)
                destination_exists = True
            except FileNotFoundError:
                destination_exists = False
    except OSError:
        destination_exists = None
    return {'component_id': component_id, 'source': str(source), 'destination': destination,
            'survey_finished_at': survey.get('finished_at'), 'source_observation': entry,
            'destination_exists': destination_exists, 'destination_ancestor': destination_ancestor,
            'declared_services': component['services'],
            'related_links': related_links,
            'survey_changed_paths': survey.get('changed_paths'),
            'blockers': ['사용 중인 프로세스와 다운로드·백업 작업을 별도로 확인해야 합니다.',
                         '코드와 설정의 모든 소비 경로, 백업 매핑 및 롤백을 별도로 확인해야 합니다.',
                         '조사 중 파일 변경과 백업 무결성은 확인하지 않았습니다.'],
            'ready_to_move': False}

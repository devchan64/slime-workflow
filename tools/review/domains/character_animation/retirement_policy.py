"""캐릭터 애니메이션의 폐기된 생성 명령 정책."""


def inspect_animation_retirement_policy(current_command_name):
    current_rejection_reasons={
        'generate':'AnyPose 기반 캐릭터 애니메이션 생성기는 폐기되었습니다. 사용 가능한 동작 생성기를 확인하세요.',
        'resume':'폐기된 AnyPose 애니메이션 작업은 재개할 수 없습니다. 기존 결과·로그 조회만 지원합니다.',
        'record-alpha-vnccs':'폐기된 애니메이션 생성기의 과거 기록은 다시 가져올 수 없습니다.',
    }
    return current_rejection_reasons.get(current_command_name)

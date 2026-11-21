"""폐기된 AnyPose 진입점. 모델 다운로드·검증을 실행하지 않는다."""


def validate_adapter_files(**retired_adapter_options):
    raise ValueError('AnyPose LoRA는 폐기되었습니다. Lightning은 lightning 모듈을 사용하세요.')


def prepare_anypose_models():
    raise ValueError('AnyPose LoRA는 폐기되어 다운로드·준비를 지원하지 않습니다.')


if __name__ == '__main__':
    prepare_anypose_models()

"""대화 입력폼과 단계 연결 검사가 공유하는 생성기 계약."""
from copy import deepcopy


WORKFLOW_GENERATOR_COMMANDS = {
    "kimodo": {"submit": "hermes-delegate-kimodo", "status": "hermes-delegation-job-status", "cancel": "hermes-delegation-cancel"},
    "sfx-dasheng-audiogen": {
        "submit": "hermes-delegate-audio", "status": "hermes-audio-status", "cancel": "hermes-audio-cancel",
    },
    "prompt-translation": {
        "submit": "hermes-delegate-translation", "status": "hermes-translation-status", "cancel": "hermes-translation-cancel",
    },
    "flux-image": {
        "submit": "hermes-delegate-flux-image", "status": "hermes-flux-delegation-status", "cancel": "hermes-flux-delegation-cancel",
    },
}


def read_workflow_generator_catalog():
    from generators.kimodo.contracts import KIMODO_DEFAULT_SETTINGS, KIMODO_MAXIMUM_SEED_VALUE
    return {
        "kimodo": {
            "commands": dict(WORKFLOW_GENERATOR_COMMANDS["kimodo"]),
            "category": "motion", "version": 1, "template_version": 1, "label": "Kimodo 모션",
            "inputs": {
                "prompt": {"type": "text", "required": True, "max_length": 2000, "label": "동작 설명"},
                **{key: {"type": "integer", "required": True, "min": low, "max": high,
                         "default": KIMODO_DEFAULT_SETTINGS[key], "label": label}
                   for key, low, high, label in (("frames", 30, 300, "프레임 수"), ("steps", 2, 100, "생성 단계"),
                                                 ("seed", 0, KIMODO_MAXIMUM_SEED_VALUE, "시드"))},
            },
            "outputs": {"images": {"type": "png_list", "label": "첫 원본 포즈 프레임", "media_type": "image/png"}},
        },
        "sfx-dasheng-audiogen": {
            "commands": dict(WORKFLOW_GENERATOR_COMMANDS["sfx-dasheng-audiogen"]),
            "category": "audio", "version": 1, "template_version": 1, "label": "Dasheng 효과음",
            "inputs": {
                "prompt": {"type": "text", "help": "생성할 내용을 입력하거나 선행 단계의 번역문을 연결하세요.", "required": True, "label": "효과음 설명", "max_length": 4000},
                "seed": {"type": "integer", "help": "동일한 설정으로 결과를 비교하려면 같은 시드를 사용하세요.", "required": True, "min": 0, "max": 4294967295, "default": 42},
            },
            "outputs": {"audio": {"type": "wav", "label": "생성 효과음", "media_type": "audio/wav"}},
        },
        "prompt-translation": {
            "commands": dict(WORKFLOW_GENERATOR_COMMANDS["prompt-translation"]),
            "category": "translation", "version": 1, "template_version": 1,
            "label": "프롬프트 번역",
            "inputs": {
                "text": {"type": "text", "help": "번역할 원문을 입력하세요.", "required": True, "label": "원문", "max_length": 6000},
                "target_language": {"type": "text", "help": "번역 결과의 언어를 선택하세요.", "required": True, "label": "목표 언어",
                                    "choices": ["en", "zh-CN"], "default": "en"},
                "glossary": {"type": "glossary", "help": "번역에 사용할 원문과 번역어 쌍을 입력하세요.", "required": False, "label": "용어 목록"},
            },
            "outputs": {"text": {"type": "text", "label": "번역 결과", "media_type": "text/plain; charset=utf-8"}},
        },
        "flux-image": {
            "commands": dict(WORKFLOW_GENERATOR_COMMANDS["flux-image"]),
            "category": "image", "version": 1, "template_version": 1, "label": "FLUX 이미지",
            "inputs": {
                "action": {"type": "text", "help": "이미지 생성 요청에는 generate를 사용합니다.", "required": True, "choices": ["generate"], "default": "generate"},
                "prompt": {"type": "text", "help": "생성할 내용을 입력하거나 선행 단계의 번역문을 연결하세요.", "required": True, "label": "프롬프트", "max_length": 8000},
                "images": {"type": "png_list", "help": "참조 PNG를 지정하거나 선행 이미지 단계의 출력을 연결하세요.", "required": True, "default": [], "max_items": 2},
                "width": {"type": "integer", "help": "출력 이미지의 가로 크기를 픽셀로 지정하세요.", "required": True, "min": 256, "max": 1664, "step": 16, "default": 512},
                "height": {"type": "integer", "help": "출력 이미지의 세로 크기를 픽셀로 지정하세요.", "required": True, "min": 256, "max": 1664, "step": 16, "default": 512},
                "steps": {"type": "integer", "help": "이미지 생성에 사용할 추론 단계 수입니다.", "required": True, "choices": [16], "default": 16},
                "seed": {"type": "integer", "help": "동일한 설정으로 결과를 비교하려면 같은 시드를 사용하세요.", "required": True, "min": 0, "max": 4294967295, "default": 10107},
            },
            "outputs": {"images": {"type": "png_list", "label": "생성 이미지", "media_type": "image/png"}},
        },
    }


def create_workflow_step_draft(current_step_identifier, current_generator_name, supplied_input_values):
    current_generator_catalog = read_workflow_generator_catalog()
    if current_generator_name not in current_generator_catalog:
        raise ValueError("지원하지 않는 생성기입니다.")
    current_field_contracts = current_generator_catalog[current_generator_name]["inputs"]
    if supplied_input_values.keys() - current_field_contracts.keys():
        raise ValueError("등록되지 않은 입력 필드입니다.")
    default_input_values = {
        current_field_name: current_field_spec["default"]
        for current_field_name, current_field_spec in current_field_contracts.items()
        if "default" in current_field_spec
    }
    return {"id": current_step_identifier, "generator": current_generator_name,
            "generator_version": current_generator_catalog[current_generator_name]["version"],
            "template_version": current_generator_catalog[current_generator_name]["template_version"],
            "inputs": deepcopy(default_input_values | supplied_input_values), "bindings": {}}

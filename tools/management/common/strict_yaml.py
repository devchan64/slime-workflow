"""중복 키를 거절하는 공용 YAML 로더."""
import yaml

def load_unique_mapping(current_yaml_loader, current_mapping_node):
    current_mapping_values = {}
    for current_key_node, current_value_node in current_mapping_node.value:
        current_field_name = current_yaml_loader.construct_object(current_key_node)
        if current_field_name in current_mapping_values:
            raise ValueError(f'중복 YAML 필드: {current_field_name}')
        current_mapping_values[current_field_name] = current_yaml_loader.construct_object(current_value_node)
    return current_mapping_values


class UniqueConfigLoader(yaml.SafeLoader):
    """중복 키를 거절한다."""


UniqueConfigLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, load_unique_mapping)

#!/usr/bin/env python3
"""맵 빌보드·건물 원본의 크기 계약을 적용하고 등록 해시를 동기화한다."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import yaml
from PIL import Image

MAXIMUM_SOURCE_DIMENSION = 512
TREE_BILLBOARD_DIMENSION = 256
VEGETATION_BILLBOARD_DIMENSION = 128
MAP_SPRITE_PREFIXES = ('assets/billboards/', 'assets/sprites/structures/')


def read_yaml_document(document_path: Path) -> dict:
    with document_path.open(encoding='utf-8') as document_file:
        return yaml.safe_load(document_file)


def create_billboard_category_map(catalog_record: dict) -> dict[str, str]:
    family_records = catalog_record.get('families')
    billboard_records = catalog_record.get('billboards')
    if not isinstance(family_records, dict) or not isinstance(billboard_records, list):
        raise ValueError('빌보드 카탈로그 계약 오류')
    resolved_categories = {}
    for billboard_record in billboard_records:
        texture_key = billboard_record.get('texture_key')
        family_name = billboard_record.get('family')
        family_record = family_records.get(family_name)
        if not isinstance(texture_key, str) or not isinstance(family_record, dict) or not isinstance(family_record.get('category'), str):
            raise ValueError('빌보드 카탈로그 항목 계약 오류')
        resolved_categories[texture_key] = family_record['category']
    return resolved_categories


def select_target_dimensions(asset_relative_path: str, source_width: int, source_height: int, category_by_texture: dict[str, str]) -> tuple[int, int]:
    texture_key = Path(asset_relative_path).stem
    category_name = category_by_texture.get(texture_key)
    if asset_relative_path.startswith('assets/billboards/') and category_name == 'tree':
        return TREE_BILLBOARD_DIMENSION, TREE_BILLBOARD_DIMENSION
    if asset_relative_path.startswith('assets/billboards/') and category_name == 'vegetation':
        return VEGETATION_BILLBOARD_DIMENSION, VEGETATION_BILLBOARD_DIMENSION
    current_largest_dimension = max(source_width, source_height)
    if current_largest_dimension <= MAXIMUM_SOURCE_DIMENSION:
        return source_width, source_height
    scale_ratio = MAXIMUM_SOURCE_DIMENSION / current_largest_dimension
    return max(1, round(source_width * scale_ratio)), max(1, round(source_height * scale_ratio))


def calculate_file_digest(asset_path: Path) -> str:
    return hashlib.sha256(asset_path.read_bytes()).hexdigest()


def replace_registry_entry(registry_text: str, asset_relative_path: str, image_width: int, image_height: int, asset_digest: str) -> str:
    entry_pattern = re.compile(r'(?ms)^- managementId: .*?(?=^- managementId:|\Z)')
    for entry_match in entry_pattern.finditer(registry_text):
        entry_text = entry_match.group(0)
        if f'  path: {asset_relative_path}\n' not in entry_text:
            continue
        updated_entry = re.sub(r'(?m)^  width: \d+$', f'  width: {image_width}', entry_text, count=1)
        if updated_entry == entry_text:
            updated_entry = re.sub(r'(?m)^(  sha256: )', f'  width: {image_width}\n  height: {image_height}\n\\1', entry_text, count=1)
        else:
            updated_entry = re.sub(r'(?m)^  height: \d+$', f'  height: {image_height}', updated_entry, count=1)
        updated_entry = re.sub(r'(?m)^  sha256: [a-f0-9]{64}$', f'  sha256: {asset_digest}', updated_entry, count=1)
        if updated_entry == entry_text or f'  width: {image_width}' not in updated_entry or f'  height: {image_height}' not in updated_entry or f'  sha256: {asset_digest}' not in updated_entry:
            raise ValueError(f'에셋 등록부 크기·해시 필드 오류: {asset_relative_path}')
        return registry_text[:entry_match.start()] + updated_entry + registry_text[entry_match.end():]
    raise ValueError(f'에셋 등록부 원본이 없습니다: {asset_relative_path}')


def replace_sprite_lock_digest(lock_text: str, asset_relative_path: str, asset_digest: str) -> str:
    entry_pattern = re.compile(rf'(?m)(^  source_path: {re.escape(asset_relative_path)}\n  sha256: )[a-f0-9]{{64}}$')
    return entry_pattern.sub(rf'\g<1>{asset_digest}', lock_text)


def resize_registered_sources(asset_root_path: Path, frontend_root_path: Path) -> None:
    registry_path = asset_root_path / 'asset-registry.yaml'
    catalog_path = asset_root_path / 'assets/billboards/catalog.yaml'
    sprite_lock_path = frontend_root_path / 'sprite-assets.lock.yaml'
    registry_record = read_yaml_document(registry_path)
    category_by_texture = create_billboard_category_map(read_yaml_document(catalog_path))
    registry_asset_paths = {asset_record.get('path') for asset_record in registry_record.get('assets', []) if isinstance(asset_record, dict)}
    image_paths = sorted(
        image_path.relative_to(asset_root_path).as_posix()
        for source_prefix in MAP_SPRITE_PREFIXES
        for image_path in (asset_root_path / source_prefix).glob('*.png')
    )
    registry_text = registry_path.read_text(encoding='utf-8')
    sprite_lock_text = sprite_lock_path.read_text(encoding='utf-8')
    resized_count = 0
    for asset_relative_path in image_paths:
        if asset_relative_path not in registry_asset_paths:
            raise ValueError(f'등록되지 않은 맵 빌보드·건물 원본: {asset_relative_path}')
        source_image_path = asset_root_path / asset_relative_path
        with Image.open(source_image_path) as source_image:
            target_width, target_height = select_target_dimensions(asset_relative_path, source_image.width, source_image.height, category_by_texture)
            if (source_image.width, source_image.height) != (target_width, target_height):
                resized_image = source_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
                resized_image.save(source_image_path)
                resized_count += 1
        with Image.open(source_image_path) as verified_image:
            image_width, image_height = verified_image.size
        if image_width > MAXIMUM_SOURCE_DIMENSION or image_height > MAXIMUM_SOURCE_DIMENSION:
            raise ValueError(f'512px 초과 원본 축소 실패: {asset_relative_path}')
        asset_digest = calculate_file_digest(source_image_path)
        registry_text = replace_registry_entry(registry_text, asset_relative_path, image_width, image_height, asset_digest)
        sprite_lock_text = replace_sprite_lock_digest(sprite_lock_text, asset_relative_path, asset_digest)
    registry_path.write_text(registry_text, encoding='utf-8')
    sprite_lock_path.write_text(sprite_lock_text, encoding='utf-8')
    print(f'크기 계약 적용 완료: 원본 {len(image_paths)}개, 축소 {resized_count}개')


def parse_command_arguments() -> argparse.Namespace:
    argument_parser = argparse.ArgumentParser(description='맵 빌보드·건물 원본을 크기 계약에 맞춰 축소합니다.')
    argument_parser.add_argument('--asset-root', type=Path, required=True)
    argument_parser.add_argument('--frontend-root', type=Path, required=True)
    return argument_parser.parse_args()


if __name__ == '__main__':
    command_arguments = parse_command_arguments()
    resize_registered_sources(command_arguments.asset_root.resolve(), command_arguments.frontend_root.resolve())

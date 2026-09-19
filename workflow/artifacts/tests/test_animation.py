"""실제 합성 PNG와 네 방향 클립의 범위·시간·공개 계약을 확인한다."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from zipfile import ZipFile
from PIL import Image
import yaml
import test_sidecar as fixtures
from workflow.artifacts.animation import validate_animation
from workflow.artifacts.sidecar import validate_metadata, validate_pair
from workflow.artifacts.contracts import register_contract
from workflow.artifacts.registry import archive_register
from workflow.artifacts.reviews import record_review
from workflow.artifacts.exporter import export_asset, export_pack

DIRECTIONS = ('down_left','down_right','up_left','up_right')


class AnimationTests(unittest.TestCase):
    def setUp(self):
        fixtures.PairTests.setUp(self)
        self.db = self.root.parent/'registry.sqlite'
        Image.new('RGBA', (4,2), (0,0,0,0)).save(self.image)
        self.data.update(schemaVersion=2, artifactId='sprite.test', artifactType='SPRITE_SHEET',
                         sha256=sha256(self.image.read_bytes()).hexdigest(),
                         contractRefs=[dict(contractId='cell.animation',version='1')])
        self.data['animation'] = dict(animationId='unit.test',version='1',sheet=dict(width=4,height=2),
            frames=[dict(frameId=f'frame.{i}',rect=dict(x=i,y=0,width=1,height=2),anchor=dict(x=0.5,y=2)) for i in range(4)],
            clips=[dict(clipId=f'idle.{direction}',action='idle',direction=direction,
                        frames=[dict(frameId=f'frame.{i}',durationMs=100)],loop=True,nextClipId=None)
                   for i,direction in enumerate(DIRECTIONS)])
        self.write()
        contract = self.contract_dir/'animation.yaml'
        contract.write_text(yaml.safe_dump(dict(managementId='contract.cell.animation.v1',schemaVersion=1,
            contractId='cell.animation',version='1',artifactTypes=['SPRITE_SHEET'],description='합성 셀 애니메이션 계약')))
        register_contract(self.db,contract)

    write = fixtures.PairTests.write

    def approve(self):
        self.data['license'].update(licenseId='CC-BY-4.0',modificationAllowed=True,redistributionAllowed=True)
        self.write()
        entry = archive_register(self.db,self.root,self.sidecar)
        record_review(self.db,self.data['artifactId'],self.data['version'],review_id='review.'+self.data['artifactId'],
            decision='APPROVED',reviewer='test',evidence_ref='PRIVATE_REVIEW',
            content_hash=entry['content_hash'],metadata_hash=entry['metadata_hash'])
        return entry

    def test_valid_sheet_preserves_explicit_frame_order_and_bottom_anchor(self):
        animation = self.data['animation']
        for clip in animation['clips']:
            clip['frames'].append(dict(clip['frames'][0],durationMs=250))
        self.write()
        actual = validate_pair(self.root,self.sidecar)
        self.assertEqual(actual['animation'],animation)
        self.assertEqual(actual['animation']['frames'][0]['anchor'],dict(x=0.5,y=2))

    def test_frame_bounds_anchor_and_duration_rejected(self):
        for mutate in [lambda d:d['frames'][0]['rect'].update(x=4),
                       lambda d:d['frames'][0]['rect'].update(width=0),
                       lambda d:d['frames'][0]['rect'].update(y=-1),
                       lambda d:d['frames'][0]['anchor'].update(y=2.1),
                       lambda d:d['frames'][0]['anchor'].update(x=float('nan')),
                       lambda d:d['frames'][0]['anchor'].update(x=True),
                       lambda d:d['frames'][0]['anchor'].update(x=10**400),
                       lambda d:d['clips'][0]['frames'][0].update(durationMs=0),
                       lambda d:d['clips'][0]['frames'][0].update(durationMs=True),
                       lambda d:d['clips'][0]['frames'][0].update(durationMs=2**53)]:
            data = deepcopy(self.data['animation']);mutate(data)
            with self.subTest(data=data), self.assertRaises(ValueError): validate_animation(data)

    def test_missing_direction_unknown_frame_and_ambiguous_clips_rejected(self):
        for mutate in [lambda d:d['clips'].pop(),
                       lambda d:d['clips'][0].update(direction='north'),
                       lambda d:d['clips'][0]['frames'][0].update(frameId='missing'),
                       lambda d:d['clips'][0].update(frames=[]),
                       lambda d:d['clips'].append(deepcopy(d['clips'][0])),
                       lambda d:d['frames'].append(deepcopy(d['frames'][0])),
                       lambda d:d['clips'][0].update(loop=1),
                       lambda d:d['frames'][0].update(extra='invalid')]:
            data = deepcopy(self.data['animation']);mutate(data)
            with self.subTest(data=data), self.assertRaises(ValueError): validate_animation(data)

    def test_nonloop_completion_keeps_direction_and_requires_existing_clip(self):
        animation = self.data['animation']
        for clip in list(animation['clips']):
            attack = dict(deepcopy(clip),clipId='attack.'+clip['direction'],action='attack',loop=False,nextClipId=clip['clipId'])
            animation['clips'].append(attack)
        validate_animation(animation)
        for changes in [dict(nextClipId='missing'),dict(nextClipId='idle.up_right'),dict(loop=True)]:
            data=deepcopy(animation);data['clips'][4].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError): validate_animation(data)
        animation['clips'][4]['nextClipId']=None
        validate_animation(animation)

    def test_png_dimensions_truncation_and_fake_png_rejected(self):
        original = self.image.read_bytes()
        for content in [original[:40],b'not-a-png']:
            self.image.write_bytes(content)
            self.data['sha256']=sha256(content).hexdigest();self.write()
            with self.assertRaises(ValueError): validate_pair(self.root,self.sidecar)
        Image.new('RGBA',(5,2)).save(self.image)
        self.data['sha256']=sha256(self.image.read_bytes()).hexdigest();self.write()
        with self.assertRaisesRegex(ValueError,'크기'): validate_pair(self.root,self.sidecar)

    def test_animated_png_is_not_silently_treated_as_a_sheet(self):
        first=Image.new('RGBA',(4,2),(0,0,0,0))
        second=Image.new('RGBA',(4,2),(255,0,0,255))
        first.save(self.image,save_all=True,append_images=[second],duration=100,loop=0)
        self.data['sha256']=sha256(self.image.read_bytes()).hexdigest();self.write()
        with self.assertRaisesRegex(ValueError,'단일 PNG'): validate_pair(self.root,self.sidecar)

    def test_v2_requires_animation_and_sprite_type_but_v1_stays_strict(self):
        for mutate in [lambda d:d.pop('animation'),lambda d:d.update(artifactType='TERRAIN_TILE'),
                       lambda d:d.update(schemaVersion=1)]:
            data=deepcopy(self.data);mutate(data)
            with self.assertRaises(ValueError): validate_metadata(data)
        legacy=dict(self.data,schemaVersion=1);legacy.pop('animation')
        validate_metadata(legacy)

    def test_approved_animation_exports_only_public_playback_metadata(self):
        self.data['generation']['modelPreparationRef']='PRIVATE_MODEL'
        self.approve()
        result=export_asset(self.db,'sprite.test','1.0.0',self.root.parent/'releases')
        with ZipFile(result['archive']) as pack:
            manifest=json.loads(pack.read('manifest.json'))
            self.assertEqual(manifest['compatibleSchemaVersion'],2)
            self.assertEqual(manifest['animation'],self.data['animation'])
            self.assertNotIn(b'PRIVATE_',pack.read('manifest.json'))
            self.assertNotIn(b'contractRefs',pack.read('manifest.json'))
            self.assertEqual(sha256(pack.read(manifest['files'][0])).hexdigest(),self.data['sha256'])

    def test_legacy_sprite_without_animation_cannot_be_publicly_exported(self):
        self.data.update(schemaVersion=1);self.data.pop('animation');self.approve()
        with self.assertRaisesRegex(ValueError,'v2 셀 애니메이션'):
            export_asset(self.db,'sprite.test','1.0.0',self.root.parent/'releases')
        self.assertFalse((self.root.parent/'releases').exists())

    def test_mixed_pack_advertises_required_v2_without_changing_static_entry(self):
        self.approve()
        self.data.update(schemaVersion=1,artifactType='TERRAIN_TILE',artifactId='terrain.static',
                         contractRefs=[dict(contractId='terrain',version='1')])
        self.data.pop('animation');self.approve()
        result=export_pack(self.db,'pack.mixed','1',[('sprite.test','1.0.0'),('terrain.static','1.0.0')],self.root.parent/'releases')
        manifest=result['manifest']
        self.assertEqual(manifest['compatibleSchemaVersion'],2)
        self.assertEqual(manifest['assets'][0]['compatibleSchemaVersion'],2)
        self.assertEqual(manifest['assets'][1]['compatibleSchemaVersion'],1)
        self.assertNotIn('animation',manifest['assets'][1])

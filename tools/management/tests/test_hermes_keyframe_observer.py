"""Kimodo 키프레임 검색의 입력·출력 경계를 검증한다."""
import unittest
from unittest.mock import patch
from tools.management.domains.hermes_agent.keyframe_observer import read_hermes_kimodo_keyframe_catalog


class HermesKeyframeObserverTests(unittest.TestCase):
    @patch('tools.management.domains.hermes_agent.keyframe_observer.execute_management_command')
    def test_search_pages_and_hide_private_fields(self,current_gateway_mock):
        current_gateway_mock.return_value={'records':[{'id':'a'*32,'tag':'걷기','source_frame':12,'files':{'preview.png':'secret'},'source_job':'private'},{'id':'b'*32,'tag':'걷기 빠르게','source_frame':14}]}
        current_result_value=read_hermes_kimodo_keyframe_catalog({'query':'걷기','limit':1})
        self.assertEqual(current_result_value['total'],2)
        self.assertEqual(current_result_value['next_offset'],1)
        current_snapshot_value=current_result_value['snapshot']
        self.assertEqual(read_hermes_kimodo_keyframe_catalog({'query':'걷기','offset':1,'snapshot':current_snapshot_value})['items'][0]['id'],'b'*32)
        current_gateway_mock.return_value['records'].append({'id':'c'*32,'tag':'걷기 느리게','source_frame':15})
        with self.assertRaisesRegex(ValueError,'변경'):
            read_hermes_kimodo_keyframe_catalog({'query':'걷기','offset':1,'snapshot':current_snapshot_value})
        self.assertEqual(current_result_value['items'][0],{'id':'a'*32,'tag':'걷기','source_frame':12})
        self.assertNotIn('secret',str(current_result_value))
        current_unverified_page=read_hermes_kimodo_keyframe_catalog({'query':'걷기','offset':1})
        self.assertEqual(current_unverified_page['items'][0]['id'],'b'*32)
        self.assertIn('변경 여부를 확인하지 못했습니다',current_unverified_page['note'])
        self.assertNotIn('변경 여부를 확인하지 못했습니다',current_result_value['note'])
        for current_bad_request in ({'limit':31},{'offset':True},{'query':'a\nb'},{'unexpected':1}):
            with self.subTest(request=current_bad_request),self.assertRaises(ValueError):
                read_hermes_kimodo_keyframe_catalog(current_bad_request)
        current_gateway_mock.return_value={'records':[{'id':'a'*32,'tag':'x','source_frame':1}]*2}
        with self.assertRaises(ValueError):
            read_hermes_kimodo_keyframe_catalog({})

    @patch('tools.management.domains.hermes_agent.keyframe_observer.execute_management_command')
    def test_preview_verifies_returned_id_and_image_hash(self,current_gateway_mock):
        import base64
        import hashlib
        import io
        from PIL import Image
        from tools.management.domains.hermes_agent.keyframe_observer import read_hermes_kimodo_keyframe_preview
        current_buffer_value=io.BytesIO()
        Image.new('RGB',(4,4),'white').save(current_buffer_value,format='PNG')
        current_image_bytes=current_buffer_value.getvalue()
        current_image_hash=hashlib.sha256(current_image_bytes).hexdigest()
        current_gateway_mock.return_value={'record':{'id':'a'*32,'files':{'preview.png':current_image_hash,'motion.npz':'d'*64,'skeleton.json':'e'*64}},'image_base64':base64.b64encode(current_image_bytes).decode(),'skeleton_signature_sha256':'c'*64}
        self.assertEqual(read_hermes_kimodo_keyframe_preview('a'*32)['sha256'],current_image_hash)
        current_gateway_mock.return_value['record']['files']['preview.png']='b'*64
        with self.assertRaises(ValueError):
            read_hermes_kimodo_keyframe_preview('a'*32)
        with self.assertRaises(ValueError):
            read_hermes_kimodo_keyframe_preview('invalid')

    @patch('tools.management.domains.hermes_agent.keyframe_observer.read_hermes_kimodo_keyframe_preview')
    def test_batch_compares_skeleton_and_deduplicates_sources(self,current_preview_mock):
        from tools.management.domains.hermes_agent.keyframe_observer import validate_hermes_kimodo_keyframe_batch
        current_preview_mock.return_value={'sha256':'b'*64,'skeleton_signature_sha256':'c'*64,'source_sha256':'f'*64}
        current_request_value={'frames':30,'keyframes':[{'id':'a'*32,'frame':20},{'id':'a'*32,'frame':1}]}
        current_result_value=validate_hermes_kimodo_keyframe_batch(current_request_value)
        self.assertEqual([item['frame'] for item in current_result_value['placements']],[1,20])
        self.assertEqual(len(current_result_value['sources']),1)
        current_preview_mock.assert_called_once()
        current_preview_mock.side_effect=[{'sha256':'b'*64,'skeleton_signature_sha256':'c'*64,'source_sha256':'f'*64},{'sha256':'d'*64,'skeleton_signature_sha256':'e'*64,'source_sha256':'f'*64}]
        with self.assertRaisesRegex(ValueError,'골격 구조'):
            validate_hermes_kimodo_keyframe_batch({'frames':30,'keyframes':[{'id':'a'*32,'frame':1},{'id':'f'*32,'frame':20}]})

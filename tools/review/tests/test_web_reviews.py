"""기존 웹 검수의 스냅샷 통합과 제공 파일 경계를 확인한다."""
from pathlib import Path
import tempfile
import unittest
from tools.review.collect_web_reviews import collect_web_reviews


class WebReviewCollectionTests(unittest.TestCase):
    def test_existing_pages_and_nested_images_are_collected(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            workflow_repo_root=Path(temporary_directory_name)
            source_review_root=workflow_repo_root/'.tmp'/'source'
            source_review_root.mkdir(parents=True)
            (source_review_root/'frames').mkdir()
            (source_review_root/'preview.html').write_text('<title>리그 · Depth 검수</title><img src="frames/one.png">')
            (source_review_root/'overlay.html').write_text('<title>오버레이</title>')
            (source_review_root/'frames/one.png').write_bytes(b'image')
            (source_review_root/'prompt.txt').write_text('비공개 프롬프트')
            (source_review_root/'execution.log').write_text('실행 로그')
            (source_review_root/'.hidden.json').write_text('{}')
            (source_review_root/'external.png').symlink_to(workflow_repo_root/'secret.png')
            (workflow_repo_root/'secret.png').write_bytes(b'secret')
            existing_manager_root=workflow_repo_root/'.tmp'/'manager'
            existing_manager_root.mkdir()
            (existing_manager_root/'manager-source.json').write_text('{}')
            (existing_manager_root/'preview.html').write_text('<title>중복 관리도구</title>')
            output_review_directory=workflow_repo_root/'.tmp'/'output'
            output_review_directory.mkdir()
            (output_review_directory/'preview.html').write_text('<title>현재 관리도구</title>')
            result_page_records=collect_web_reviews(workflow_repo_root,output_review_directory,lambda trace_stage_name,trace_message_text: None)
            self.assertEqual(len(result_page_records),2)
            self.assertTrue(all(current_page_record['category']=='web-review' for current_page_record in result_page_records))
            copied_review_directory=(output_review_directory/result_page_records[0]['path']).parent
            self.assertTrue((copied_review_directory/'frames/one.png').exists())
            for denied_file_name in ('prompt.txt','execution.log','.hidden.json','external.png'):
                self.assertFalse((copied_review_directory/denied_file_name).exists())
            self.assertEqual(len({Path(current_page_record['path']).parent for current_page_record in result_page_records}),1)

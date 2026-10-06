import json
import tempfile
import unittest
from pathlib import Path

from tools.review.serve import load_static_review_route_identifiers
from tools.review.ui.gradio.static_review_app import build_static_review_interface, create_static_review_loader, load_static_review_paths


class StaticReviewGradioTest(unittest.TestCase):
    def test_loads_only_declared_static_review_paths(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            source_file_path=Path(temporary_directory_name)/'manager-source.json'
            source_file_path.write_text(json.dumps({'pages':[
                {'id':'walk-review','path':'animation/anchors.html','uiMode':'gradio-static'},
                {'id':'momask','path':'/momask-generator/','uiMode':'gradio'},
            ]}),encoding='utf-8')

            static_review_paths=load_static_review_paths(source_file_path)

        self.assertEqual(static_review_paths,{'walk-review':'animation/anchors.html'})

    def test_collects_direct_static_page_routes(self):
        with tempfile.TemporaryDirectory() as temporary_directory_name:
            source_file_path=Path(temporary_directory_name)/'manager-source.json'
            source_file_path.write_text(json.dumps({'pages':[
                {'id':'walk-review','path':'animation/anchors.html','uiMode':'gradio-static'},
                {'id':'momask','path':'/momask-generator/','uiMode':'gradio'},
            ]}),encoding='utf-8')

            static_review_routes=load_static_review_route_identifiers(source_file_path)

        self.assertEqual(static_review_routes,{'/animation/anchors.html':'walk-review'})

    def test_component_uses_allowlisted_page_and_isolates_game_design(self):
        loader_script_value=create_static_review_loader(8770,{'walk-review':'animation/anchors.html'})
        interface_blocks_value=build_static_review_interface({'walk-review':'animation/anchors.html'})

        self.assertIn('staticReviewPaths',loader_script_value)
        self.assertIn('selectedReviewPath',loader_script_value)
        self.assertIn("searchParams.set('embedded','gradio-static')",loader_script_value)
        self.assertIn('resolveStaticReviewAssetUrl',loader_script_value)
        self.assertIn("rel='modulepreload'",loader_script_value)
        self.assertIn('await import(',loader_script_value)
        self.assertIn("setAttribute('aria-busy','false')",loader_script_value)
        self.assertIn("if(selectedReviewPath.startsWith('ui-'))",loader_script_value)
        self.assertIn("document.createElement('iframe')",loader_script_value)
        self.assertIn('currentReviewFrame.src=currentPreviewLocation.href',loader_script_value)
        self.assertIn("new URL('terrain-preview.html',staticReviewPageUrl)",loader_script_value)
        self.assertLess(loader_script_value.index("document.createElement('iframe')"),loader_script_value.index('window.fetch='))
        current_terrain_events=[current_event_record for current_event_record in interface_blocks_value.get_config_file()['dependencies'] if 'window.terrainReviewControls' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_terrain_events),6)
        self.assertTrue(all(not current_event_record['backend_fn'] and not current_event_record['queue'] for current_event_record in current_terrain_events))
        self.assertFalse(interface_blocks_value.css)
        self.assertIn('static-review-root',str(interface_blocks_value.get_config_file()))
        self.assertIn('aria-busy="true"',str(interface_blocks_value.get_config_file()))

if __name__=='__main__':
    unittest.main()

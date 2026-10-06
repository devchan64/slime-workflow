import json
import sys
import tempfile
import subprocess
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
        self.assertNotIn('window.fetch=',loader_script_value)
        self.assertNotIn('document.head.append',loader_script_value)
        self.assertIn("document.createElement('iframe')",loader_script_value)
        self.assertIn('currentReviewFrame.src=currentPreviewLocation.href',loader_script_value)
        self.assertIn("new URL('terrain-preview.html',staticReviewPageUrl)",loader_script_value)
        self.assertIn('contentWindow.anchorReviewPlayback',loader_script_value)
        self.assertIn('contentWindow.anchorReviewSeekFrame',loader_script_value)
        current_terrain_events=[current_event_record for current_event_record in interface_blocks_value.get_config_file()['dependencies'] if 'window.terrainReviewControls' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_terrain_events),6)
        self.assertTrue(all(not current_event_record['backend_fn'] and not current_event_record['queue'] for current_event_record in current_terrain_events))
        self.assertFalse(interface_blocks_value.css)
        self.assertIn('static-review-root',str(interface_blocks_value.get_config_file()))
        self.assertIn('aria-busy="true"',str(interface_blocks_value.get_config_file()))

    def test_anchor_history_omits_unsupported_generation_actions(self):
        current_interface_blocks=build_static_review_interface({'walk-review':'animation/anchors.html'})
        current_config_record=current_interface_blocks.get_config_file()
        current_button_labels=[current_component_record['props'].get('value') for current_component_record in current_config_record['components'] if current_component_record['type']=='button']
        for current_button_label in ['좌표 저장','결과 조회','입력값 불러오기','이력 목록 초기화']:
            self.assertIn(current_button_label,current_button_labels)
        for current_button_label in ['생성 재개','작업 중지','로그 조회','선택 이력 삭제']:
            self.assertNotIn(current_button_label,current_button_labels)

    def test_output_settings_reject_invalid_values_without_partial_updates(self):
        current_editor_source=(Path(__file__).parents[1]/'ui/shared/animation-anchor-editor/editor.js').read_text()
        current_bridge_source=current_editor_source.split('window.anchorReviewOutputSettings=',1)[1].split('// 표시 선택은',1)[0]
        current_script_source="""
const assert=require('node:assert/strict');global.window={};
const currentMapInput={value:'field',onchange:()=>{}};
const gameOutputScaleToggleElement={checked:true},actorSizeChoiceElement={value:'medium'},bodyHeightInputElement={value:'80'},previewTileWidthElement={value:'240'};
const gameRenderMetrics={tileWidth:80,tileHeight:40,townTileWidth:64,townTileHeight:32};
const GAME_SIZE_PRESETS={small:{},medium:{},large:{},huge:{}};
const PREVIEW_TILE_MINIMUM_WIDTH=32,PREVIEW_TILE_MAXIMUM_WIDTH=600;
global.document={querySelector:name=>name==='#mapScaleChoice'?currentMapInput:{textContent:'크기 기준'}};
window.anchorReviewOutputSettings="""+current_bridge_source+"""
const currentInitialValues=window.anchorReviewOutputSettings(null);
assert.throws(()=>window.anchorReviewOutputSettings([false,'town','large',120,241]));
assert.deepEqual(window.anchorReviewOutputSettings(null),currentInitialValues);
assert.throws(()=>window.anchorReviewOutputSettings([false,'town','large',0,240]));
assert.deepEqual(window.anchorReviewOutputSettings(null),currentInitialValues);
assert.deepEqual(window.anchorReviewOutputSettings([false,'town','large',120,320]).slice(0,5),[false,'town','large',120,320]);
"""
        current_node_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True)
        self.assertEqual(current_node_result.returncode,0,current_node_result.stderr)

    def test_display_settings_validate_before_applying(self):
        current_editor_source=(Path(__file__).parents[1]/'ui/shared/animation-anchor-editor/editor.js').read_text()
        current_bridge_source=current_editor_source.split('window.anchorReviewDisplay=',1)[1].split('// 좌표 조작은',1)[0]
        current_script_source="""
const assert=require('node:assert/strict');global.window={};
const guideToggleElement={checked:true},rigMiniMapToggleElement={checked:true,onchange:()=>{}};
const currentTileInput={checked:true},currentShadowInput={checked:true};
global.document={querySelector:name=>name==='#tilePreviewToggle'?currentTileInput:currentShadowInput};
window.anchorReviewDisplay="""+current_bridge_source+"""
assert.deepEqual(window.anchorReviewDisplay(null).slice(0,4),[true,true,true,true]);
assert.deepEqual(window.anchorReviewDisplay([false,false,true,false]).slice(0,4),[false,false,true,false]);
assert.throws(()=>window.anchorReviewDisplay([true,true,false,1]));
assert.deepEqual(window.anchorReviewDisplay(null).slice(0,4),[false,false,true,false]);
"""
        current_node_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True)
        self.assertEqual(current_node_result.returncode,0,current_node_result.stderr)

    def test_anchor_coordinates_use_position_only_shared_joypad(self):
        current_interface_blocks=build_static_review_interface({'walk-review':'animation/anchors.html'})
        current_config_record=current_interface_blocks.get_config_file()
        current_button_labels=[current_component_record['props'].get('value') for current_component_record in current_config_record['components'] if current_component_record['type']=='button']
        self.assertIn('X 적용',current_button_labels)
        self.assertIn('Y 적용',current_button_labels)
        self.assertIn('선택 목록 읽기',current_button_labels)
        self.assertNotIn('배율 적용',current_button_labels)
        self.assertNotIn('배율 늘리기 +',current_button_labels)
        current_coordinate_events=[current_event_record for current_event_record in current_config_record['dependencies'] if 'anchorReviewCoordinates' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_coordinate_events),7)
        self.assertTrue(all(not current_event_record['backend_fn'] and not current_event_record['queue'] for current_event_record in current_coordinate_events))

    def test_direct_entrypoint_loads_shared_components(self):
        current_entrypoint_path=Path(__file__).parents[1]/'ui/gradio/static_review_app.py'
        current_process_result=subprocess.run([sys.executable,str(current_entrypoint_path),'--help'],capture_output=True,text=True)
        self.assertEqual(current_process_result.returncode,0,current_process_result.stderr)
        self.assertIn('--source-file',current_process_result.stdout)

    def test_anchor_navigation_preserves_frames_on_invalid_seek(self):
        current_editor_source=(Path(__file__).parents[1]/'ui/shared/animation-anchor-editor/editor.js').read_text()
        current_bridge_source=current_editor_source.split('// 공용 Gradio 탐색기',1)[1].split('if(window.parent!==window',1)[0]
        current_bridge_source=current_bridge_source[current_bridge_source.index('window.anchorReviewPlayback='):]
        current_script_source="""
const assert=require('node:assert/strict');
global.window={};global.document={querySelector:()=>({textContent:''})};
const frameChoiceElement={value:'0'},REVIEW_FRAME_COUNT=8,REVIEW_FRAME_DURATION=125;
let animationPlaybackActive=false,animationStartedTime=0;
function pauseFramePlayback(){animationPlaybackActive=false;}
function moveFrameSelection(delta){pauseFramePlayback();frameChoiceElement.value=String((Number(frameChoiceElement.value)+delta+REVIEW_FRAME_COUNT)%REVIEW_FRAME_COUNT);}
"""+current_bridge_source+"""
assert.equal(window.anchorReviewPlayback('next'),'2 / 8 · 정지');
assert.equal(window.anchorReviewSeekFrame(8),'8 / 8 · 정지');
assert.equal(window.anchorReviewPlayback('next'),'1 / 8 · 정지');
assert.equal(window.anchorReviewPlayback('play'),'1 / 8 · 재생 중');
assert.throws(()=>window.anchorReviewSeekFrame(9));
assert.equal(animationPlaybackActive,true);assert.equal(frameChoiceElement.value,'0');
assert.equal(window.anchorReviewPlayback('stop'),'1 / 8 · 정지');
"""
        current_node_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True)
        self.assertEqual(current_node_result.returncode,0,current_node_result.stderr)

if __name__=='__main__':
    unittest.main()

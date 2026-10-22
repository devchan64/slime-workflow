"""반복 도구의 초안 누적·되돌리기 및 잘못된 입력 검증."""
import copy
import unittest
from unittest.mock import patch
from tools.review.common.gradio_map_brushes import apply_map_brush_batch

class MapBrushToolTests(unittest.TestCase):
    def setUp(self):
        self.current_editor_state={'snapshot':{'codes':{'K':'stone','R':'road'},'terrain':{'columns':2,'rows':2,'elevations':[[1,1],[1,1]],'blocked':[]},'tiles':{'rows':['KK','KK']}},'draft':{'map':'sample','revision':'test','cells':[],'objects':[{'id':'one','position':{'column':0,'row':0}},{'id':'two','position':{'column':0,'row':0}},{'id':'other','position':{'column':1,'row':1}}]},'history':[]}
        self.current_preview_patch=patch('tools.review.common.gradio_map_editor.preview_map_edit_draft',return_value=({}, {},'검증 완료',{}))
        self.current_preview_patch.start();self.addCleanup(self.current_preview_patch.stop)
    def test_floor_stroke_preserves_height_and_one_undo(self):
        current_original_state=copy.deepcopy(self.current_editor_state)
        current_result_state=apply_map_brush_batch('sample',self.current_editor_state,[{'tool':'floor','column':0,'row':0,'tile':'R'},{'tool':'floor','column':1,'row':0,'tile':'R'}])[0]
        self.assertEqual(len(current_result_state['history']),1)
        self.assertEqual([current_cell_record['height'] for current_cell_record in current_result_state['draft']['cells']],[1,1])
        self.assertEqual(self.current_editor_state,current_original_state)
    def test_height_repeated_operations_and_bounds(self):
        current_result_state=apply_map_brush_batch('sample',self.current_editor_state,[{'tool':'raise','column':0,'row':0}])[0]
        current_result_state=apply_map_brush_batch('sample',current_result_state,[{'tool':'lower','column':0,'row':0}])[0]
        self.assertEqual(current_result_state['draft']['cells'][0]['height'],1)
        with self.assertRaisesRegex(ValueError,'0~20'):apply_map_brush_batch('sample',current_result_state,[{'tool':'lower','column':0,'row':0}]*2)
    def test_delete_one_and_cell_are_separate(self):
        current_one_state=apply_map_brush_batch('sample',self.current_editor_state,[{'tool':'delete','column':0,'row':0,'object':'one'}])[0]
        self.assertEqual([current_object_record['id'] for current_object_record in current_one_state['draft']['objects']],['two','other'])
        current_cell_state=apply_map_brush_batch('sample',self.current_editor_state,[{'tool':'delete-cell','column':0,'row':0}])[0]
        self.assertEqual([current_object_record['id'] for current_object_record in current_cell_state['draft']['objects']],['other'])
    def test_place_stroke_shares_one_history_and_unique_ids(self):
        from tools.review.common.gradio_map_editor import change_map_edit_draft
        self.current_editor_state['snapshot']['textures']=['quartz']
        current_original_draft=copy.deepcopy(self.current_editor_state['draft'])
        current_result_state=apply_map_brush_batch('sample',self.current_editor_state,[{'tool':'place','column':0,'row':0,'texture':'quartz'},{'tool':'place','column':1,'row':0,'texture':'quartz'}])[0]
        self.assertEqual(current_result_state['draft']['cells'],[])
        self.assertEqual(len(current_result_state['history']),1)
        current_added_records=current_result_state['draft']['objects'][-2:]
        self.assertEqual(len({current_record['id'] for current_record in current_added_records}),2)
        self.assertEqual([current_record['position']['column'] for current_record in current_added_records],[0,1])
        current_undone_state=change_map_edit_draft(current_result_state,'undo',None,None,None,None,False,None,None)[0]
        self.assertEqual(current_undone_state['draft'],current_original_draft)
        current_redone_state=change_map_edit_draft(current_undone_state,'redo',None,None,None,None,False,None,None)[0]
        self.assertEqual(current_redone_state['draft'],current_result_state['draft'])
        with self.assertRaisesRegex(Exception,'빌보드'):apply_map_brush_batch('sample',self.current_editor_state,[{'tool':'place','column':0,'row':0,'texture':'invalid'}])
        self.assertEqual(self.current_editor_state['draft'],current_original_draft)
    def test_wall_paint_keeps_floor(self):
        with patch('tools.review.common.map_asset_sources.validate_map_cliff_texture',return_value='cliff-wall'):
            current_result_state=apply_map_brush_batch('sample',self.current_editor_state,[{'tool':'wall','column':0,'row':0,'wall':'cliff-wall'}])[0]
        self.assertEqual(current_result_state['draft']['cells'][0]['tile'],'K')
        self.assertEqual(current_result_state['draft']['cells'][0]['wall'],'cliff-wall')
    def test_invalid_input_does_not_mutate_state(self):
        current_original_state=copy.deepcopy(self.current_editor_state)
        with self.assertRaisesRegex(ValueError,'타일'):apply_map_brush_batch('sample',self.current_editor_state,[{'tool':'floor','column':0,'row':0,'tile':'unknown'}])
        with self.assertRaisesRegex(ValueError,'맵'):apply_map_brush_batch('other',self.current_editor_state,[])
        self.assertEqual(current_original_state,self.current_editor_state)
    def test_canvas_event_uses_client_json_not_server_state(self):
        from tools.review.ui.gradio.map_review_app import build_map_review_interface
        current_interface_config=build_map_review_interface(8770).get_config_file()
        current_component_records={current_record['id']:current_record for current_record in current_interface_config['components']}
        current_brush_events=[current_dependency for current_dependency in current_interface_config['dependencies'] if current_dependency.get('backend_fn') and 'mapReviewBrushQueue' in (current_dependency.get('js') or '')]
        self.assertEqual(len(current_brush_events),1)
        self.assertEqual(current_component_records[current_brush_events[0]['inputs'][2]]['type'],'json')
    def test_detail_edit_preserves_painted_wall(self):
        from tools.review.common.gradio_map_editor import change_map_edit_draft
        self.current_editor_state['draft']['cells']=[{'column':0,'row':0,'tile':'K','height':1,'blocked':False,'wall':'cliff-wall'}]
        current_result_state=change_map_edit_draft(self.current_editor_state,'cell',0,0,'R',2,False,None,None)[0]
        self.assertEqual(current_result_state['draft']['cells'][0]['wall'],'cliff-wall')
    def test_undo_redo_restores_exact_draft(self):
        from tools.review.common.gradio_map_editor import change_map_edit_draft,describe_map_editor_history
        current_painted_state=apply_map_brush_batch('sample',self.current_editor_state,[{'tool':'raise','column':0,'row':0}])[0]
        current_undone_state=change_map_edit_draft(current_painted_state,'undo',None,None,None,None,None,None,None)[0]
        self.assertEqual(current_undone_state['draft'],self.current_editor_state['draft'])
        self.assertTrue(describe_map_editor_history(current_undone_state)[1]['interactive'])
        current_redone_state=change_map_edit_draft(current_undone_state,'redo',None,None,None,None,None,None,None)[0]
        self.assertEqual(current_redone_state['draft'],current_painted_state['draft'])
        self.assertFalse(describe_map_editor_history(current_redone_state)[1]['interactive'])
    def test_new_edit_clears_redo_but_noop_keeps_it(self):
        from tools.review.common.gradio_map_editor import change_map_edit_draft
        current_painted_state=apply_map_brush_batch('sample',self.current_editor_state,[{'tool':'raise','column':0,'row':0}])[0]
        current_undone_state=change_map_edit_draft(current_painted_state,'undo',None,None,None,None,None,None,None)[0]
        current_noop_state=apply_map_brush_batch('sample',current_undone_state,[{'tool':'delete','column':0,'row':0,'object':'missing'}])[0]
        self.assertEqual(len(current_noop_state['future']),1)
        for current_new_state in [apply_map_brush_batch('sample',current_undone_state,[{'tool':'lower','column':0,'row':0}])[0],change_map_edit_draft(current_undone_state,'delete',None,None,None,None,None,'one',None)[0]]:
            self.assertEqual(current_new_state['future'],[])

class MapAutosaveRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.current_fresh_state={'snapshot':{'fresh':True},'draft':{'map':'sample','revision':'one','cells':[],'objects':[]},'history':[],'future':[]}
    def restore_saved_record(self,current_saved_record):
        from tools.review.common.gradio_map_autosave import restore_map_autosave_state
        return restore_map_autosave_state('sample',{},current_saved_record,lambda current_map_identifier,current_live_state:(copy.deepcopy(self.current_fresh_state),))
    def test_restore_draft_and_history_with_fresh_snapshot(self):
        current_saved_state=copy.deepcopy(self.current_fresh_state)
        current_saved_state['history']=[copy.deepcopy(current_saved_state['draft'])]
        current_saved_state['future']=[copy.deepcopy(current_saved_state['draft'])]
        current_saved_state['snapshot']={'stale':True}
        current_saved_state['draft']['cells']=[{'column':0,'row':0,'tile':'K','height':2,'blocked':False}]
        current_restored_state=self.restore_saved_record({'version':1,'state':current_saved_state})
        self.assertEqual(current_restored_state['snapshot'],{'fresh':True})
        self.assertEqual(current_restored_state['draft'],current_saved_state['draft'])
        self.assertEqual(current_restored_state['history'],current_saved_state['history'])
        self.assertEqual(current_restored_state['future'],current_saved_state['future'])
        self.assertEqual(current_saved_state['snapshot'],{'stale':True})
    def test_changed_source_and_invalid_history_rejected(self):
        current_saved_state=copy.deepcopy(self.current_fresh_state)
        current_saved_state['draft']['revision']='old'
        with self.assertRaisesRegex(ValueError,'원본이 변경'):self.restore_saved_record({'version':1,'state':current_saved_state})
        current_saved_state['draft']['revision']='one'
        current_saved_state['future']={}
        with self.assertRaisesRegex(ValueError,'형식'):self.restore_saved_record({'version':1,'state':current_saved_state})
    def test_absent_record_loads_clean_state(self):
        self.assertEqual(self.restore_saved_record(None),self.current_fresh_state)

class MapAssetPickerTests(unittest.TestCase):
    def setUp(self):
        current_thumbnail_patch=patch('tools.review.common.gradio_map_picker.load_map_picker_thumbnail',side_effect=lambda current_image_path:current_image_path)
        current_thumbnail_patch.start();self.addCleanup(current_thumbnail_patch.stop)
    def test_search_pagination_and_empty_result(self):
        from tools.review.common.gradio_map_picker import paginate_map_picker_records
        current_asset_records=[{'value':f'rock-{current_record_index}','name':'석영 암석','image':'sample.png'} for current_record_index in range(19)]
        current_page_result=paginate_map_picker_records(current_asset_records,'석영',2)
        self.assertEqual(len(current_page_result[1]),5)
        self.assertEqual(current_page_result[1][0]['value'],'rock-5')
        self.assertEqual(paginate_map_picker_records(current_asset_records,'ROCK-18',1)[1],[current_asset_records[18]])
        self.assertEqual(paginate_map_picker_records(current_asset_records,'missing',9)[1],[])
        self.assertFalse(paginate_map_picker_records(current_asset_records,'',4)[5]['interactive'])
    def test_placed_picker_excludes_deleted_objects(self):
        from tools.review.common.gradio_map_picker import load_map_picker_records
        current_editor_state={'snapshot':{'textures':['rock']},'draft':{'objects':[{'id':'remaining','textureKey':'rock','position':{'column':1,'row':2}}]}}
        with patch('tools.review.common.gradio_map_picker.execute_remote_management_command',return_value={'assets':[{'texture':'rock','name':'석영','image':'sample.png'}]}):
            current_asset_records=load_map_picker_records(current_editor_state,'placed',{})
        self.assertEqual([current_asset_record['value'] for current_asset_record in current_asset_records],['remaining'])
    def test_picker_requires_edit_state(self):
        from tools.review.common.gradio_map_picker import load_map_picker_records
        with self.assertRaisesRegex(Exception,'편집 모드'):load_map_picker_records({},'floor',{})

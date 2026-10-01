"""바닥 타일 프롬프트·공용 명령·원근 보정 계약을 검증한다."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import cv2
import numpy as np
from tools.review.domains.tile.floor_generation import prepare_floor_request, load_floor_configuration, FloorGenerationManager
from tools.review.domains.tile.floor_results import detect_floor_quadrilateral, save_floor_rectification
from tools.review.common import management_gateway

class FloorGenerationTests(unittest.TestCase):
    def create_floor_request(self):
        return dict(action='generate',user_prompt='잔디밭',width=1024,height=1024,steps=4,seed=251204)
    def test_fixed_prompt_and_validation(self):
        prepared_request_value = prepare_floor_request(self.create_floor_request())
        self.assertEqual(prepared_request_value['prompt'],'잔디밭. 분리된 정사각형 9개. 3행 3열. 아주 얇은 검은 테두리. 검은 배경. 탑뷰. 컬러 일러스트.')
        for invalid_field_values in ({'base_prompt':'override'},{'user_prompt':''},{'width':1008,'height':1008},{'seed':True},{'width':512},{'images':[]}):
            with self.subTest(invalid=invalid_field_values),self.assertRaises(ValueError):
                prepare_floor_request(self.create_floor_request()|invalid_field_values)
    def test_cli_contract(self):
        with patch.object(management_gateway,'execute_management_command',return_value={'id':'queued'}) as command_call_handle:
            management_gateway.execute_gateway_arguments('floor-tile',['generate','--prompt','잔디밭','--detach'])
        self.assertEqual(prepare_floor_request(command_call_handle.call_args.args[2]),prepare_floor_request(self.create_floor_request()|{'tag':''}))
        self.assertEqual(management_gateway.resolve_management_command('floor-tile','catalog',{}),('GET','/floor-tile-generator/catalog'))
    def test_gui_build(self):
        from tools.review.ui.gradio.floor_tile_app import build_floor_interface
        with patch('tools.review.ui.gradio.floor_tile_app.execute_floor_gateway',return_value=load_floor_configuration()):
            interface_block_value = build_floor_interface('http://127.0.0.1:8770')
        self.assertIn('사용자 프롬프트 · 바닥 표면',[component_record_value.get('props',{}).get('label') for component_record_value in interface_block_value.config['components']])
        interface_block_value.close()
    def test_perspective_and_failed_detection(self):
        original_image_value = np.zeros((512,512,3),dtype='uint8')
        expected_corner_values = np.array([[95,50],[420,95],[455,430],[55,450]],dtype='int32')
        cv2.fillConvexPoly(original_image_value,expected_corner_values,(65,190,70))
        detected_corner_values = detect_floor_quadrilateral(original_image_value)
        np.testing.assert_allclose(detected_corner_values,expected_corner_values,atol=2)
        with tempfile.TemporaryDirectory() as temporary_directory_value:
            current_job_root = Path(temporary_directory_value)
            cv2.imwrite(str(current_job_root/'result.png'),original_image_value)
            (current_job_root/'result.json').write_text('{}')
            prepared_request_value = {'floor_rectify':{'version':1,'output_size':1024}}
            save_floor_rectification(current_job_root,prepared_request_value)
            corrected_image_value = cv2.imread(str(current_job_root/'square-crop.png'))
            self.assertEqual(corrected_image_value.shape,(1024,1024,3))
            self.assertGreater(float(corrected_image_value[5:-5,5:-5,1].mean()),185)
            cv2.imwrite(str(current_job_root/'result.png'),np.zeros_like(original_image_value))
            with self.assertRaises(ValueError): save_floor_rectification(current_job_root,prepared_request_value)
            self.assertTrue((current_job_root/'result.png').exists())
            self.assertFalse((current_job_root/'square-crop.png').exists())
            self.assertEqual(json.loads((current_job_root/'square-crop.json').read_text())['status'],'failed')
        cv2.circle(original_image_value := np.zeros_like(original_image_value),(256,256),210,(65,190,70),-1)
        with self.assertRaises(ValueError): detect_floor_quadrilateral(original_image_value)
    def test_shared_history_and_outputs(self):
        with tempfile.TemporaryDirectory() as temporary_directory_value:
            current_job_root = Path(temporary_directory_value)
            generation_job_identifier = '2026-09-30_00-00-00-12345678'
            selected_job_path = current_job_root/generation_job_identifier
            selected_job_path.mkdir()
            (selected_job_path/'request.json').write_text(json.dumps(prepare_floor_request(self.create_floor_request())))
            (selected_job_path/'status.json').write_text('{"status":"completed"}')
            (selected_job_path/'square-crop.png').touch()
            floor_service_value = FloorGenerationManager()
            floor_service_value.job_storage_root = current_job_root
            with patch.object(floor_service_value,'history_storage_path',return_value=current_job_root/'history'):
                self.assertEqual(floor_service_value.list_generation_history()[0]['id'],generation_job_identifier)
                self.assertTrue(floor_service_value.enrich_generation_status(selected_job_path,{'status':'completed'})['rectified_image'].endswith('/square-crop.png'))
                floor_service_value.delete_generation_history(generation_job_identifier)
                self.assertEqual(floor_service_value.list_generation_history(),[])
                self.assertTrue((selected_job_path/'square-crop.png').exists())

    def test_center_tile_preserves_pixels_and_rejects_incomplete_grid(self):
        from tools.review.domains.tile.floor_results import extract_center_tile
        original_image_value = np.zeros((1024,1024,3),dtype='uint8')
        for row_index_value in range(3):
            for column_index_value in range(3):
                cv2.rectangle(original_image_value,(30+column_index_value*330,30+row_index_value*330),(310+column_index_value*330,310+row_index_value*330),(40+row_index_value*50,100+column_index_value*50,80),-1)
        extracted_image_value,_,extraction_record_value = extract_center_tile(original_image_value)
        crop_left_value,crop_top_value,crop_right_value,crop_bottom_value = extraction_record_value['crop_box']
        np.testing.assert_array_equal(extracted_image_value,original_image_value[crop_top_value:crop_bottom_value,crop_left_value:crop_right_value])
        self.assertEqual(extraction_record_value['selected_row'],2)
        self.assertEqual(extraction_record_value['selected_column'],2)
        self.assertEqual(len(extraction_record_value['detected_cells']),9)
        with tempfile.TemporaryDirectory() as temporary_directory_value:
            current_job_root = Path(temporary_directory_value)
            cv2.imwrite(str(current_job_root/'result.png'),original_image_value)
            (current_job_root/'result.json').write_text('{}')
            save_floor_rectification(current_job_root,{'floor_rectify':{'version':2,'grid_rows':3,'grid_columns':3,'selected_row':2,'selected_column':2}})
            corrected_image_value = cv2.imread(str(current_job_root/'square-crop.png'))
            np.testing.assert_array_equal(corrected_image_value[100,100],[90,150,80])
            self.assertEqual(corrected_image_value.shape,(280,280,3))
        original_image_value[20:320,20:320] = 0
        with self.assertRaisesRegex(ValueError,'9개'): extract_center_tile(original_image_value)
        with self.assertRaises(ValueError): extract_center_tile(np.zeros((1280,1280,3),dtype='uint8'))

    def test_three_stage_failure_resume_and_integrity(self):
        from PIL import Image
        from tools.review.domains.tile.floor_pipeline import execute_floor_pipeline
        from tools.review.common.gpu_memory_history import build_image_memory_identity
        with tempfile.TemporaryDirectory() as temporary_directory_value:
            current_job_root = Path(temporary_directory_value)
            prepared_request_value = prepare_floor_request(self.create_floor_request())
            (current_job_root/'request.json').write_text(json.dumps(prepared_request_value))
            self.assertEqual(prepare_floor_request(self.create_floor_request()|{'user_prompt':'돌 바닥'})['floor_separation']['prompt'],'돌 바닥')
            self.assertNotIn('floor_rectify',prepared_request_value)
            self.assertEqual(prepared_request_value['floor_separation']['prompt'],'잔디밭')
            self.assertIn('floor-three-stage-v10',build_image_memory_identity('run_qwen_2512.py',current_job_root))
            launched_stage_names = []
            def simulate_stage_process(command_argument_values, **process_keyword_values):
                stage_output_directory = Path(command_argument_values[-1])
                launched_stage_names.append(stage_output_directory.name)
                self.assertNotIn('start_new_session',process_keyword_values)
                if stage_output_directory.name == 'stage-3-redraw' and launched_stage_names.count('stage-3-redraw') == 1:
                    (stage_output_directory/'execution.log').write_text('중단 기록')
                    raise RuntimeError('3단계 추론 실패')
                stage_request_record = json.loads((stage_output_directory/'request.json').read_text())
                if stage_output_directory.name == 'stage-1-grid':
                    cv2.imwrite(str(stage_output_directory/'result.png'),self.create_molding_fixture())
                else:
                    self.assertEqual(stage_request_record['prompt'],'잔디밭')
                    Image.new('RGB',(512,512),'green').save(stage_output_directory/'result.png')
                (stage_output_directory/'result.json').write_text('{"elapsed_seconds":10}')
                (stage_output_directory/'status.json').write_text('{"status":"completed"}')
                from unittest.mock import Mock
                return Mock(wait=lambda timeout:0)
            with patch('tools.review.domains.tile.floor_pipeline.subprocess.Popen',side_effect=simulate_stage_process):
                with self.assertRaisesRegex(RuntimeError,'3단계 추론 실패'):
                    execute_floor_pipeline(current_job_root,prepared_request_value)
                self.assertTrue((current_job_root/'result.png').exists())
                self.assertEqual(json.loads((current_job_root/'status.json').read_text())['status'],'failed')
                execute_floor_pipeline(current_job_root,prepared_request_value)
                self.assertEqual(launched_stage_names,['stage-1-grid','stage-3-redraw','stage-3-redraw'])
                self.assertTrue(list((current_job_root/'stage-3-redraw').glob('attempt-*/execution.log')))
                self.assertTrue((current_job_root/'single-tile.png').exists())
                self.assertTrue((current_job_root/'center-tile.png').exists())
                self.assertEqual(len(json.loads((current_job_root/'result.json').read_text())['stages']),3)
                with Image.open(current_job_root/'reference-1.png') as reference_image_value:
                    self.assertEqual(reference_image_value.size,(512,512))
                self.assertEqual(json.loads((current_job_root/'status.json').read_text())['status'],'completed')
                execute_floor_pipeline(current_job_root,prepared_request_value)
                self.assertEqual(len(launched_stage_names),3)
                (current_job_root/'stage-1-grid/result.png').write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'무결성'):
                    execute_floor_pipeline(current_job_root,prepared_request_value)

    def create_molding_fixture(self):
        source_image_value = np.zeros((1024,1024,3),dtype='uint8')
        for current_row_index in range(3):
            for current_column_index in range(3):
                left_pixel_value = 30+current_column_index*330
                top_pixel_value = 30+current_row_index*330
                cv2.rectangle(source_image_value,(left_pixel_value,top_pixel_value),(left_pixel_value+305,top_pixel_value+305),(4,4,4),-1)
                cv2.rectangle(source_image_value,(left_pixel_value+3,top_pixel_value+3),(left_pixel_value+302,top_pixel_value+302),(65,65,65),-1)
                cv2.rectangle(source_image_value,(left_pixel_value+15,top_pixel_value+15),(left_pixel_value+290,top_pixel_value+290),(40,150,40),-1)
        return source_image_value

    def test_shared_outer_frame_retains_nine_cells(self):
        from tools.review.domains.tile.floor_crop import extract_molding_center
        source_image_value = self.create_molding_fixture()
        cv2.rectangle(source_image_value,(34,34),(992,992),(65,65,65),6)
        cropped_image_value,_,crop_record_value = extract_molding_center(source_image_value,8)
        self.assertEqual(len(crop_record_value['detected_cells']),9)
        crop_left_value,crop_top_value,crop_right_value,crop_bottom_value = crop_record_value['crop_box']
        np.testing.assert_array_equal(cropped_image_value,source_image_value[crop_top_value:crop_bottom_value,crop_left_value:crop_right_value])

    def test_thin_connections_between_cells_are_separated(self):
        from tools.review.domains.tile.floor_crop import extract_molding_center
        source_image_value=self.create_molding_fixture()
        for current_row_index in range(3):
            cv2.line(source_image_value,(100,100+330*current_row_index),(900,100+330*current_row_index),(90,150,180),1)
        cropped_image_value,_,crop_record_value=extract_molding_center(source_image_value,7)
        self.assertEqual(len(crop_record_value['detected_cells']),9)
        crop_left_value,crop_top_value,crop_right_value,crop_bottom_value=crop_record_value['crop_box']
        np.testing.assert_array_equal(cropped_image_value,source_image_value[crop_top_value:crop_bottom_value,crop_left_value:crop_right_value])

    def test_mechanical_crop_pixels_and_detection_failure(self):
        from tools.review.domains.tile.floor_crop import extract_molding_center
        source_image_value = self.create_molding_fixture()
        cropped_image_value,_,crop_record_value = extract_molding_center(source_image_value)
        crop_left_value,crop_top_value,crop_right_value,crop_bottom_value = crop_record_value['crop_box']
        np.testing.assert_array_equal(cropped_image_value,source_image_value[crop_top_value:crop_bottom_value,crop_left_value:crop_right_value])
        self.assertTrue(355<=crop_left_value<=365)
        self.assertTrue(660<=crop_right_value<=670)
        with self.assertRaises(ValueError): extract_molding_center(np.full((1024,1024,3),(40,150,40),dtype='uint8'))

    def test_exterior_crop_retains_frame_despite_inner_dark_lines(self):
        from tools.review.domains.tile.floor_crop import extract_molding_center
        source_image_value=self.create_molding_fixture()
        original_crop_value,_,original_crop_record=extract_molding_center(source_image_value)
        cv2.line(source_image_value,(381,380),(642,380),(0,0,0),3)
        cv2.line(source_image_value,(640,383),(640,640),(0,0,0),3)
        cropped_image_value,_,crop_record_value=extract_molding_center(source_image_value)
        self.assertEqual(crop_record_value['crop_box'],original_crop_record['crop_box'])
        self.assertEqual(cropped_image_value.shape,original_crop_value.shape)
        self.assertEqual(crop_record_value['version'],9)
        self.assertEqual(len(crop_record_value['detected_cells']),9)
        selected_cell_bounds=next(record_value['bounds'] for record_value in crop_record_value['detected_cells'] if record_value['row']==2 and record_value['column']==2)
        self.assertEqual(crop_record_value['crop_box'],[selected_cell_bounds[0]-2,selected_cell_bounds[1]-2,selected_cell_bounds[2]+2,selected_cell_bounds[3]+2])
        cv2.rectangle(source_image_value,(330,400),(370,420),(65,65,65),-1)
        with self.assertRaises(ValueError): extract_molding_center(source_image_value)

    def test_crop_measures_dim_background_without_merging_blocks(self):
        from tools.review.domains.tile.floor_crop import extract_molding_center
        source_image_value = self.create_molding_fixture()
        source_image_value[np.all(source_image_value == 0, axis=2)] = (18,18,18)
        with self.assertRaises(ValueError):
            extract_molding_center(source_image_value,2)
        cropped_image_value,_,crop_record_value = extract_molding_center(source_image_value)
        self.assertEqual(crop_record_value['parameters']['background_threshold'],26)
        self.assertEqual(len(crop_record_value['detected_cells']),9)
        self.assertEqual(crop_record_value['crop_box'],[361,361,665,665])
        np.testing.assert_array_equal(cropped_image_value,source_image_value[361:665,361:665])
        with self.assertRaisesRegex(ValueError,'배경 조건'):
            extract_molding_center(np.full((1024,1024,3),60,dtype='uint8'))

    def test_particle_bridges_do_not_expand_or_merge_tile_bounds(self):
        from tools.review.domains.tile.floor_crop import extract_molding_center
        source_image_value = self.create_molding_fixture()
        _,_,expected_crop_record = extract_molding_center(source_image_value)
        # 외곽에 붙은 입자와 옆 타일까지 이어지는 가는 입자 연결.
        cv2.line(source_image_value,(330,420),(370,420),(180,180,180),2)
        cv2.line(source_image_value,(480,345),(480,365),(180,180,180),2)
        with self.assertRaises(ValueError):
            extract_molding_center(source_image_value,3)
        cropped_image_value,_,crop_record_value = extract_molding_center(source_image_value)
        self.assertEqual(crop_record_value['crop_box'],expected_crop_record['crop_box'])
        crop_left_value,crop_top_value,crop_right_value,crop_bottom_value = crop_record_value['crop_box']
        np.testing.assert_array_equal(cropped_image_value,source_image_value[crop_top_value:crop_bottom_value,crop_left_value:crop_right_value])
        # 실제 넓은 연결은 입자로 간주하지 않고 실패해야 한다.
        cv2.rectangle(source_image_value,(330,400),(370,440),(65,65,65),-1)
        with self.assertRaises(ValueError):
            extract_molding_center(source_image_value)

    def test_particle_removal_preserves_thin_closed_border(self):
        from tools.review.domains.tile.floor_crop import extract_molding_center
        source_image_value = np.zeros((1024,1024,3),dtype='uint8')
        for current_row_index in range(3):
            for current_column_index in range(3):
                left_pixel_value = 30+current_column_index*330
                top_pixel_value = 30+current_row_index*330
                cv2.rectangle(source_image_value,(left_pixel_value,top_pixel_value),(left_pixel_value+305,top_pixel_value+305),(65,65,65),1)
                cv2.rectangle(source_image_value,(left_pixel_value+15,top_pixel_value+15),(left_pixel_value+290,top_pixel_value+290),(40,150,40),-1)
        _,_,crop_record_value = extract_molding_center(source_image_value)
        self.assertEqual(crop_record_value['crop_box'],[358,358,668,668])

    def test_connected_board_requires_nine_closed_frames(self):
        from tools.review.domains.tile.floor_crop import extract_molding_center
        source_image_value = np.zeros((1024,1024,3),dtype='uint8')
        cv2.rectangle(source_image_value,(50,50),(974,974),(75,75,75),-1)
        for current_row_index in range(3):
            for current_column_index in range(3):
                left_pixel_value = 85+current_column_index*300
                top_pixel_value = 85+current_row_index*300
                cv2.rectangle(source_image_value,(left_pixel_value,top_pixel_value),(left_pixel_value+250,top_pixel_value+250),(0,0,0),-1)
                cv2.rectangle(source_image_value,(left_pixel_value+10,top_pixel_value+10),(left_pixel_value+240,top_pixel_value+240),(150,110,70),-1)
        with self.assertRaises(ValueError): extract_molding_center(source_image_value,4)
        cropped_image_value,_,crop_record_value = extract_molding_center(source_image_value)
        self.assertEqual(crop_record_value['method'],'nine-closed-frames-gap-midpoints')
        self.assertEqual(len(crop_record_value['detected_cells']),9)
        self.assertEqual(crop_record_value['crop_size'],[300,300])
        crop_left_value,crop_top_value,crop_right_value,crop_bottom_value = crop_record_value['crop_box']
        np.testing.assert_array_equal(cropped_image_value,source_image_value[crop_top_value:crop_bottom_value,crop_left_value:crop_right_value])
        # 어두운 내부는 기존 40 기준에서 테두리와 합쳐진다.
        for current_column_index in range(3):
            left_pixel_value = 95+current_column_index*300
            cv2.rectangle(source_image_value,(left_pixel_value,695),(left_pixel_value+230,925),(35,35,35),-1)
        with self.assertRaisesRegex(ValueError,'테두리 9개'):
            extract_molding_center(source_image_value,5)
        _,_,dark_crop_record = extract_molding_center(source_image_value)
        self.assertEqual(dark_crop_record['crop_box'],crop_record_value['crop_box'])
        self.assertGreaterEqual(len(dark_crop_record['parameters']['threshold_consensus']),2)
        cv2.rectangle(source_image_value,(685,685),(935,935),(75,75,75),-1)
        with self.assertRaisesRegex(ValueError,'테두리 9개'):
            extract_molding_center(source_image_value)

    def test_narrow_background_sampling_excludes_marble_frame(self):
        from tools.review.domains.tile.floor_crop import extract_molding_center
        source_image_value = np.zeros((1024,1024,3),dtype='uint8')
        for current_row_index in range(3):
            for current_column_index in range(3):
                left_pixel_value = 12+current_column_index*336
                top_pixel_value = 12+current_row_index*336
                cv2.rectangle(source_image_value,(left_pixel_value,top_pixel_value),(left_pixel_value+320,top_pixel_value+320),(70,70,70),1)
                cv2.rectangle(source_image_value,(left_pixel_value+20,top_pixel_value+20),(left_pixel_value+300,top_pixel_value+300),(180,190,200),-1)
        with self.assertRaisesRegex(ValueError,'배경 조건'):
            extract_molding_center(source_image_value,8)
        cropped_image_value,_,crop_record_value = extract_molding_center(source_image_value,9)
        self.assertEqual(len(crop_record_value['detected_cells']),9)
        self.assertEqual(crop_record_value['parameters']['sample_width'],8)
        crop_left_value,crop_top_value,crop_right_value,crop_bottom_value = crop_record_value['crop_box']
        np.testing.assert_array_equal(cropped_image_value,source_image_value[crop_top_value:crop_bottom_value,crop_left_value:crop_right_value])
        # 한쪽 변이 밝으면 다른 세 변의 검정 배경으로 감추지 않는다.
        source_image_value[:8,:] = 60
        with self.assertRaisesRegex(ValueError,'배경 조건'):
            extract_molding_center(source_image_value,9)

    def test_narrow_background_still_rejects_missing_cell(self):
        from tools.review.domains.tile.floor_crop import extract_molding_center
        source_image_value = self.create_molding_fixture()
        source_image_value[690:996,690:996] = 0
        with self.assertRaisesRegex(ValueError,'9개'):
            extract_molding_center(source_image_value,9)

import unittest

from tools.review.ui.gradio.anny_attributes_app import build_anny_attribute_interface, create_anny_attribute_loader, read_anny_attribute_markup


class AnnyAttributesGradioTest(unittest.TestCase):
    def test_status_view_uses_shared_service_values(self):
        current_interface_value=build_anny_attribute_interface(8770)
        current_status_function=next(current_function for current_function in current_interface_value.fns.values() if current_function.fn and current_function.fn.__name__=='render_anny_generation_status')
        current_display_text=current_status_function.fn({'status':'running','metrics':{'gpu_observations':{'GPU-test':{'process_current_mib':100,'process_peak_mib':200,'scope':'작업 및 자식 프로세스'}}}})
        self.assertIn('200 MiB',current_display_text)
        self.assertIn('계산 중',current_display_text)
        self.assertIn('window.annyGenerationStatus',str(current_interface_value.get_config_file()))

    def test_uses_gradio_custom_component(self):
        interface_blocks_value = build_anny_attribute_interface(8770)
        configuration_value = interface_blocks_value.get_config_file()
        self.assertIn('anny-attribute-root', str(configuration_value))
        self.assertNotIn('<iframe', str(configuration_value))
        self.assertNotIn('<dialog', read_anny_attribute_markup())
        self.assertNotIn('attribute-direct-input-form', read_anny_attribute_markup())
        self.assertIn('속성값 적용', str(configuration_value))
        self.assertIn('## Anny 속성 렌더러', str(configuration_value))
        self.assertNotIn('<h1>', read_anny_attribute_markup())

    def test_actions_are_native_browser_commands(self):
        current_configuration_record=build_anny_attribute_interface(8770).get_config_file()
        current_action_events=[current_event_record for current_event_record in current_configuration_record['dependencies'] if 'annyAttributeActions' in (current_event_record.get('js') or '')]
        self.assertEqual(len(current_action_events),1)
        for current_event_record in current_action_events:
            self.assertFalse(current_event_record['backend_fn'])
        current_markup_text=read_anny_attribute_markup()
        for current_button_identifier in ('reset','generate-preview','retry'):
            self.assertNotIn('id="'+current_button_identifier+'"',current_markup_text)
        self.assertIn('aria-live="polite"',current_markup_text)

    def test_uses_selected_history_actions(self):
        current_configuration_record=build_anny_attribute_interface(8770).get_config_file()
        current_history_events=[current_event_record for current_event_record in current_configuration_record['dependencies'] if 'annyHistoryControls' in (current_event_record.get('js') or '')]
        for current_expected_action in ('list','result','restore','logs','resume','cancel','delete','reset','inspect','prioritize'):
            self.assertTrue(any('\"'+current_expected_action+'\"' in current_event_record['js'] for current_event_record in current_history_events), current_expected_action)
        self.assertTrue(all(not current_event_record['backend_fn'] and not current_event_record['queue'] for current_event_record in current_history_events))
        self.assertNotIn('id="generation-history"',read_anny_attribute_markup())
        self.assertIn('선택한 생성 ID',str(current_configuration_record))
        self.assertIn('이력 수동 정리',str(current_configuration_record))

    def test_only_user_selection_invalidates_file_confirmation(self):
        current_interface_value=build_anny_attribute_interface(8770)
        current_configuration_record=current_interface_value.get_config_file()
        current_selection_identifier=next(current_component['id'] for current_component in current_configuration_record['components'] if current_component['props'].get('label')=='이력 선택 · ID·상태 검색')
        current_selection_events=[current_event for current_event in current_configuration_record['dependencies'] if any(current_target[0]==current_selection_identifier for current_target in current_event['targets'])]
        self.assertTrue(current_selection_events)
        self.assertTrue(all(current_target[1]=='input' for current_event in current_selection_events for current_target in current_event['targets']))

    def test_selected_actions_follow_job_status(self):
        current_interface_value=build_anny_attribute_interface(8770)
        current_callback_value=next(current_function.fn for current_function in current_interface_value.fns.values() if current_function.fn and current_function.fn.__name__=='update_browser_history_actions')
        for current_status_name,current_expected_values in [('queued',[False,True,False,True,True,False]),('running',[False,True,False,False,True,False]),('completed',[True,True,False,False,False,True]),('failed',[False,True,True,False,False,True]),('paused',[False,True,False,False,False,True])]:
            with self.subTest(status=current_status_name):
                current_button_updates=current_callback_value({'status':{'status':current_status_name}})
                self.assertEqual([current_update_record['interactive'] for current_update_record in current_button_updates],current_expected_values)
        self.assertTrue(current_callback_value({'status':{'status':'running'},'preview_ready':True})[0]['interactive'])
        self.assertTrue(all(not current_update_record['interactive'] for current_update_record in current_callback_value(None)))

    def test_loader_preserves_attribute_component_dependencies(self):
        loader_script_text=create_anny_attribute_loader(8770)
        self.assertIn("http://127.0.0.1:8770'+currentPathValue",loader_script_text)
        self.assertIn('/anny-attributes/mesh-viewer.js',loader_script_text)
        self.assertNotIn('/anny-attributes/history-ui.js',loader_script_text)
        self.assertIn('mesh-preview',read_anny_attribute_markup())
        self.assertNotIn('/management/workflow-ui.js',loader_script_text)
        self.assertNotIn('id="baseline-profile"',read_anny_attribute_markup())
        self.assertNotIn('id="render-rotation-y"',read_anny_attribute_markup())


if __name__ == '__main__':
    unittest.main()

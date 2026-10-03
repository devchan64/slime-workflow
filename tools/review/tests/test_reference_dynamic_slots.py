"""공용 참조 입력 추가·삭제·최대 개수·이력 복원 검사."""
import unittest
import gradio as gr
from tools.review.common.gradio_reference_images import build_reference_image_inputs


class ReferenceDynamicSlotTests(unittest.TestCase):
    def setUp(self):
        with gr.Blocks() as current_interface_value:
            self.reference_upload_group,self.reference_image_controls=build_reference_image_inputs(reference_slot_count=10)
        self.current_interface_value=current_interface_value

    def find_callback_function(self, selected_callback_name):
        return next(current_callback_record.fn for current_callback_record in self.current_interface_value.fns.values()
                    if current_callback_record.fn.__name__==selected_callback_name)

    def test_starts_with_one_slot_and_adds_up_to_ten(self):
        current_group_controls=self.reference_upload_group.reference_slot_outputs[1:11]
        self.assertEqual([current_group_value.visible for current_group_value in current_group_controls],[True]+[False]*9)
        current_add_callback=self.find_callback_function('add_reference_slot')
        self.assertEqual(current_add_callback(1,*([None]*10))[0],2)
        maximum_slot_updates=current_add_callback(10,*([None]*10))
        self.assertEqual(maximum_slot_updates[0],10)
        self.assertFalse(maximum_slot_updates[-2]['interactive'])

    def test_delete_shifts_following_references_and_keeps_one_slot(self):
        delete_callback_values=[current_callback_record.fn for current_callback_record in self.current_interface_value.fns.values()
                                if current_callback_record.fn.__name__=='delete_reference_slot']
        current_input_values=['first','second','third']+[None]*7
        current_delete_result=delete_callback_values[1](3,*current_input_values)
        self.assertEqual(current_delete_result[0],2)
        self.assertEqual(list(current_delete_result[-10:]),['first','third']+[None]*8)
        self.assertEqual(delete_callback_values[0](1,*([None]*10))[0],1)

    def test_history_reveals_tenth_image_and_can_reset_to_one(self):
        current_reveal_callback=self.find_callback_function('reveal_loaded_slots')
        self.assertEqual(current_reveal_callback(1,*([None]*9+['last']))[0],10)
        current_restore_updates=self.reference_upload_group.build_reference_updates(1)
        self.assertEqual([current_group_record['visible'] for current_group_record in current_restore_updates[1:11]],[True]+[False]*9)

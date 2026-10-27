"""모델 추론 없이 VACE 조건 텐서와 제작자 Flow 스케줄을 검사한다."""
import unittest
try:
    import torch
    from diffusers import FlowMatchEulerDiscreteScheduler
except ImportError:
    torch = None
from generators.wan_vace.worker import build_vace_conditions
from generators.wan_vace.contracts import locate_expert_switch


@unittest.skipIf(torch is None, '모델 .venv에서 실행하는 텐서 계약 검사')
class VaceSamplingContractTests(unittest.TestCase):
    def test_reference_slot_and_first_frame_mask_are_distinct(self):
        current_reference_tensor=torch.zeros(1,480,832,3)
        current_reference_condition=build_vace_conditions({'mode':'reference','frames':5},current_reference_tensor)
        self.assertEqual(set(current_reference_condition),{'reference_image'})
        self.assertIs(current_reference_condition['reference_image'],current_reference_tensor)
        current_first_condition=build_vace_conditions({'mode':'first_frame','frames':5},current_reference_tensor)
        self.assertEqual(tuple(current_first_condition['control_video'].shape),(5,480,832,3))
        self.assertTrue(torch.all(current_first_condition['control_masks'][0]==0))
        self.assertTrue(torch.all(current_first_condition['control_masks'][1:]==1))
        self.assertTrue(torch.all(current_first_condition['control_video'][0]==0))
        self.assertTrue(torch.all(current_first_condition['control_video'][1:]==0.5))
        self.assertEqual(build_vace_conditions({'mode':'text','frames':5},None),{})

    def test_official_flow_boundary_and_continuous_stage_schedule(self):
        for current_step_count in (2,20,50):
            current_flow_scheduler=FlowMatchEulerDiscreteScheduler(num_train_timesteps=1000,shift=12,use_dynamic_shifting=False)
            current_flow_scheduler.set_timesteps(current_step_count)
            current_sigma_values=current_flow_scheduler.sigmas
            current_switch_index=locate_expert_switch(current_sigma_values)
            self.assertTrue(torch.all(current_flow_scheduler.timesteps[:current_switch_index]>=875))
            self.assertTrue(torch.all(current_flow_scheduler.timesteps[current_switch_index:]<875))
            self.assertEqual(len(current_sigma_values),current_step_count+1)
            self.assertEqual(float(current_sigma_values[-1]),0)
            self.assertTrue(torch.all(current_sigma_values[:-1]>current_sigma_values[1:]))

    def test_pinned_vace_node_reference_trim_and_mask_contract(self):
        import ast
        from types import SimpleNamespace
        from generators.wan_vace.contracts import VACE_RUNTIME_DIRECTORY
        current_source_tree=ast.parse((VACE_RUNTIME_DIRECTORY/'ComfyUI/comfy_extras/nodes_wan.py').read_text())
        current_node_class=next(current_node for current_node in current_source_tree.body if isinstance(current_node,ast.ClassDef) and current_node.name=='WanVaceToVideo')
        current_execute_function=next(current_node for current_node in current_node_class.body if isinstance(current_node,ast.FunctionDef) and current_node.name=='execute')
        current_execute_function.decorator_list=[]
        current_execute_function.returns=None
        current_node_module=ast.fix_missing_locations(ast.Module(body=[current_execute_function],type_ignores=[]))
        current_runtime_globals={'torch':torch,'io':SimpleNamespace(NodeOutput=lambda *current_output_values:current_output_values),
            'comfy':SimpleNamespace(utils=SimpleNamespace(common_upscale=lambda current_tensor_value,*current_extra_values:current_tensor_value),
                latent_formats=SimpleNamespace(Wan21=lambda:SimpleNamespace(process_out=lambda current_tensor_value:current_tensor_value)),
                model_management=SimpleNamespace(intermediate_device=lambda:'cpu')),
            'node_helpers':SimpleNamespace(conditioning_set_values=lambda current_input_value,current_condition_value,**current_extra_values:current_condition_value)}
        exec(compile(current_node_module,'pinned-WanVaceToVideo','exec'),current_runtime_globals)
        current_vae_stub=SimpleNamespace(encode=lambda current_pixels_value:torch.zeros(1,16,(len(current_pixels_value)-1)//4+1,60,104))
        for current_input_mode in ('reference','first_frame','text'):
            current_conditions_value=build_vace_conditions({'mode':current_input_mode,'frames':5},torch.zeros(1,480,832,3))
            current_output_values=current_runtime_globals['execute'](None,[],[],current_vae_stub,832,480,5,1,1,**current_conditions_value)
            current_trim_count=1 if current_input_mode=='reference' else 0
            self.assertEqual(current_output_values[3],current_trim_count)
            self.assertEqual(current_output_values[2]['samples'].shape[2],2+current_trim_count)
            current_mask_tensor=current_output_values[0]['vace_mask'][0]
            self.assertEqual(current_mask_tensor.shape[2],2+current_trim_count)
            if current_input_mode=='reference':self.assertTrue(torch.all(current_mask_tensor[:,:,0]==0))
            if current_input_mode=='first_frame':
                # 제작자도 nearest-exact로 5→2 축소한다. 픽셀 마스크의 첫 값과 잠재 마스크를 혼동하지 않는다.
                expected_latent_mask=torch.nn.functional.interpolate(current_conditions_value['control_masks'].view(5,60,8,104,8).permute(2,4,0,1,3).reshape(1,64,5,60,104),size=(2,60,104),mode='nearest-exact')
                self.assertTrue(torch.equal(current_mask_tensor,expected_latent_mask))
            self.assertTrue(torch.all(current_mask_tensor[:,:,-1]==1))

"""기본 버튼을 유지하며 접근성 설명을 보존하는 공용 연결 계약."""
import subprocess
import unittest

import gradio as gr
from tools.review.common.gradio_button_guidance import BUTTON_GUIDANCE_LINK_SCRIPT, build_button_guidance


class ButtonGuidanceTests(unittest.TestCase):
    def test_native_control_and_existing_identifier_are_preserved(self):
        with gr.Blocks() as current_interface_blocks:
            current_button_control = gr.Button('생성', elem_id='existing-generation-button', interactive=False)
            current_guidance_control = build_button_guidance(current_button_control, '참조를 첨부하세요.')
            current_button_control.click(lambda: '접수', outputs=gr.Textbox())
        self.assertEqual(current_button_control.elem_id, 'existing-generation-button')
        self.assertIsInstance(current_guidance_control, gr.Markdown)
        self.assertEqual(sum(current_component is current_button_control for current_component in current_interface_blocks.blocks.values()), 1)
        self.assertFalse(current_button_control.interactive)
        self.assertTrue(any(current_dependency['targets'] == [(current_button_control._id, 'click')] for current_dependency in current_interface_blocks.config['dependencies']))

    def test_late_children_and_attribute_updates_keep_existing_descriptions(self):
        current_browser_harness = r'''
const assert = require('node:assert/strict');
let currentMutationCallback, currentChildrenReady = false, currentWriteCount = 0;
let currentDescriptionValue = 'existing-description';
const currentButtonElement = {
 getAttribute: () => currentDescriptionValue,
 setAttribute: (currentAttributeName, currentAttributeValue) => {
  assert.equal(currentAttributeName, 'aria-describedby');
  currentDescriptionValue = currentAttributeValue; currentWriteCount++;
 }
};
const element = {querySelector: currentSelectorText => currentChildrenReady ?
 (currentSelectorText === '[id="button"]' ? currentButtonElement : {}) : null};
const props = {value: JSON.stringify({button: 'button', guidance: 'guidance'})};
const MutationObserver = class {
 constructor(currentCallbackValue) { currentMutationCallback = currentCallbackValue; }
 observe(currentTargetElement) { assert.equal(currentTargetElement, element); }
};
SCRIPT
assert.equal(currentWriteCount, 0);
currentChildrenReady = true;
currentMutationCallback();
assert.equal(currentDescriptionValue, 'existing-description guidance');
currentMutationCallback();
assert.equal(currentWriteCount, 1);
currentDescriptionValue = 'updated-description';
currentMutationCallback();
assert.equal(currentDescriptionValue, 'updated-description guidance');
'''.replace('SCRIPT', BUTTON_GUIDANCE_LINK_SCRIPT)
        current_test_result = subprocess.run(['node', '-e', current_browser_harness], capture_output=True, text=True, timeout=10)
        self.assertEqual(current_test_result.returncode, 0, current_test_result.stderr)

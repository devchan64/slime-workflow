"""공용 에셋 수치 정밀도 계약."""
import unittest
from tools.review.common.sprite_display_properties import normalize_sprite_property_precision

class SpritePropertyPrecisionTests(unittest.TestCase):
    def test_all_continuous_fields_round_and_integer_boolean_preserved(self):
        current_input_values = dict(anchorX=-.143505432,anchorY=1.498377,displayHeight=378.652929,groundFootprintColumns=2,groundFootprintRows=1,billboardAnchorMode='tile-intersection',billboardBlocksMovement=False,shadowOffsetColumn=-.555,shadowOffsetRow=.555,shadowScaleX=1.1234,shadowScaleY=.9876)
        current_output_values = normalize_sprite_property_precision(current_input_values)
        self.assertEqual([current_output_values[current_field_name] for current_field_name in ('anchorX','anchorY','displayHeight','shadowOffsetColumn','shadowOffsetRow','shadowScaleX','shadowScaleY')],[-.14,1.5,378.65,-.56,.56,1.12,.99])
        self.assertIs(type(current_output_values['groundFootprintColumns']),int)
        self.assertIs(current_output_values['billboardBlocksMovement'],False)
        self.assertEqual(normalize_sprite_property_precision(current_output_values),current_output_values)

    def test_invalid_values_do_not_round_into_valid_range(self):
        for current_invalid_value in (16.001,float('nan'),True):
            with self.assertRaises(ValueError):normalize_sprite_property_precision(dict(anchorX=current_invalid_value,anchorY=0,billboardAnchorMode='tile-intersection'))

from pathlib import Path
import unittest
from generators.wan21_video_lora import apply_adapter

class Model:
    def __init__(self,patches): self.patches=patches

class AdapterTests(unittest.TestCase):
    def test_direct_deltas_and_lora_are_all_counted(self):
        class Utils:
            @staticmethod
            def load_torch_file(*args,**kwargs): return {'a.lora_down.weight':1,'a.lora_up.weight':1,'b.diff':1,'a.diff_b':1}
        class SD:
            @staticmethod
            def load_lora_for_models(model,*args): return Model({'a.weight':[1], 'a.bias':[1], 'b.weight':[1]}),None
        _,count=apply_adapter(Model({}),Path('adapter'),1,SD,Utils)
        self.assertEqual(count,3)
        class Missing:
            @staticmethod
            def load_lora_for_models(model,*args): return Model({'a.weight':[1]}),None
        with self.assertRaisesRegex(ValueError,'불일치'): apply_adapter(Model({}),Path('adapter'),1,Missing,Utils)

if __name__=='__main__': unittest.main()

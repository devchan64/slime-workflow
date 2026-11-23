"""Experimental Wan 2.2 attack adapters tested for 2.1 I2V patch registration."""
from generators.wan21_i2v.assets import ROOT, DIRECTORY
from generators.wan21_video_assets import inspect_files, prepare_files

FILES=(
 ('action/attack-high.safetensors','Teluv/Wan_Video_Attack_Sprite_Animation','b5bfa96287285c6cf725acf8a17e2e3e864d9434','Wan_i14b_Attack_Sprite_Animation_ver3_high_noise.safetensors',153453600,'9dcaf603a283d3a4161b1456b10db07f66f8475889591b1338da519c7c8096d3'),
 ('action/attack-low.safetensors','Teluv/Wan_Video_Attack_Sprite_Animation','b5bfa96287285c6cf725acf8a17e2e3e864d9434','Wan_i14b_Attack_Sprite_Animation_ver3_low_noise.safetensors',153453600,'1540e1983df386a57808e0ecc1dbd925ad090282c622cfcda6ecd045c89fe21c'),
)

def inspect_assets(): return inspect_files(DIRECTORY,FILES)
def prepare_assets(): prepare_files(DIRECTORY,FILES,'wan21-i2v-attack-lora')

"""Invoke UniRig with experimental ROCm fallbacks in an isolated interpreter."""
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
import transformers  # establish dependency detection before installing shims
from workflow.domains.unirig_experiment.rocm_skin_shims import install
install()
sys.path.insert(0,str(ROOT/'.local/unirig-experiment/source'))
runpy.run_path(str(ROOT/'.local/unirig-experiment/source/run.py'),run_name='__main__')

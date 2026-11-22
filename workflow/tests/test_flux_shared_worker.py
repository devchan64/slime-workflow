import hashlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from generators.image import run_flux_expression, run_flux_image


class FluxSharedWorkerTests(unittest.TestCase):
    def test_expression_entry_preserves_legacy_command(self):
        with patch.object(run_flux_expression, 'execute_flux_image_worker') as worker:
            run_flux_expression.execute_flux_expression_worker()
        worker.assert_called_once_with(expression_mode=True)

    def test_expression_uses_shared_pipeline_and_preserves_result_contract(self):
        with tempfile.TemporaryDirectory() as root:
            job = Path(root) / '.tmp/test/flux-expression-generator/job'
            job.mkdir(parents=True)
            prompt = 'expression prompt'
            request = {'prompt': prompt, 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                       'flux_model_revision': run_flux_image.FLUX_MODEL_REVISION_VALUE, 'references': ['face.png'],
                       'reference_snapshots': [{'sha256': 'reference-hash'}], 'width': 512, 'height': 512,
                       'steps': 16, 'seed': 42}
            (job / 'request.json').write_text(json.dumps(request))
            result_image = MagicMock()
            result_image.save.side_effect = lambda path: Path(path).write_bytes(b'png')
            reference_image = MagicMock()
            reference_image.convert.return_value.copy.return_value = 'rgb-face'
            image_module = types.ModuleType('PIL')
            image_module.Image = MagicMock()
            image_module.Image.open.return_value.__enter__.return_value = reference_image
            pipeline = MagicMock(return_value={'images': [result_image]})
            diffusers = types.ModuleType('diffusers')
            diffusers.ModularPipeline = MagicMock()
            diffusers.ModularPipeline.from_pretrained.return_value.blocks.init_pipeline.return_value = pipeline
            components = types.ModuleType('diffusers.modular_pipelines.components_manager')
            components.ComponentsManager = MagicMock()
            torch = MagicMock()
            torch.__version__ = 'test'
            torch.version.hip = 'test-hip'
            torch.cuda.get_device_name.return_value = 'test-gpu'
            torch.cuda.max_memory_allocated.return_value = 0
            guard = types.ModuleType('generators.common.numerical_guard')
            guard.install_vae_decode_guard = MagicMock()
            guard.require_finite_tensor = MagicMock()
            resident = types.ModuleType('generators.image.flux_gpu_resident')
            resident.load_flux_resident_components = MagicMock()
            modules = {'torch': torch, 'PIL': image_module, 'diffusers': diffusers,
                       'diffusers.modular_pipelines': types.ModuleType('diffusers.modular_pipelines'),
                       'diffusers.modular_pipelines.components_manager': components,
                       'generators.common.numerical_guard': guard, 'generators.image.flux_gpu_resident': resident}
            with patch.object(run_flux_image, 'WORKFLOW_ROOT_DIRECTORY', Path(root)), \
                 patch.object(run_flux_image, 'verify_reference_snapshots'), \
                 patch.dict(sys.modules, modules), patch.object(sys, 'argv', ['worker', '--job-dir', str(job)]):
                run_flux_image.execute_flux_image_worker(expression_mode=True)
            self.assertEqual(pipeline.call_args.kwargs['image'], ['rgb-face'])
            self.assertEqual(json.loads((job / 'result.json').read_text())['reference_sha256'], 'reference-hash')
            self.assertEqual(json.loads((job / 'status.json').read_text())['image'], '/flux-expression-generator/jobs/job/result.png')

    def test_expression_entry_rejects_other_profile_roots(self):
        with tempfile.TemporaryDirectory() as root:
            job = Path(root) / '.tmp/test/flux-image-generator/job'
            job.mkdir(parents=True)
            with patch.object(run_flux_image, 'WORKFLOW_ROOT_DIRECTORY', Path(root)), \
                 patch.object(sys, 'argv', ['worker', '--job-dir', str(job)]):
                with self.assertRaises(ValueError):
                    run_flux_image.execute_flux_image_worker(expression_mode=True)

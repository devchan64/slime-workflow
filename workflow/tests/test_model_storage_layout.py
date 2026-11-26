from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from workflow.common.model_storage_layout import resolve_hermes_model_directory, resolve_huggingface_cache, resolve_minimax_snapshot
from workflow.common.model_storage_move import assess_storage_move, move_storage, move_verified_cache, move_cache_with_queue_guard, rollback_storage


class ModelStorageLayoutTest(unittest.TestCase):
    def test_minimax_video_and_image_consumers_resolve_shared_encoder(self):
        from unittest.mock import patch
        from generators.minimax_h3 import assets
        from generators.minimax_h3_image import contracts
        with TemporaryDirectory() as temporary:
            project = Path(temporary)
            root = project/'.model'
            legacy_root = root/'minimax-h3-i2v'
            old = legacy_root/'text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors'
            old.parent.mkdir(parents=True)
            old.write_bytes(b'weight')
            records = [(old, 6, 'digest')]
            with patch.object(assets, 'ROOT', project), patch.object(assets, 'OLD', legacy_root), \
                 patch.object(contracts, 'ROOT', project), patch.object(contracts, 'ENCODER', old), \
                 patch.object(contracts, 'FILES', ((old, 6),)):
                self.assertEqual(assets.current_files(records)[0][0], old)
                self.assertEqual(contracts.current_files()[0][0], old)
                new = root/'qwen3vl-32b-minimax-h3-int8-convrot'/old.name
                new.parent.mkdir()
                old.rename(new)
                self.assertEqual(assets.current_files(records)[0][0], new)
                self.assertEqual(contracts.current_files()[0][0], new)
                old.write_bytes(b'duplicate')
                with self.assertRaises(ValueError):
                    assets.current_files(records)
                with self.assertRaises(ValueError):
                    contracts.current_files()

    def test_minimax_encoder_variants_resolve_independently_and_reject_conflicts(self):
        from workflow.common.model_storage_layout import resolve_minimax_qwen_encoder
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for variant, filename, directory in (
                ('int8-convrot', 'qwen3vl_32b_minimax_h3_int8_convrot.safetensors', 'qwen3vl-32b-minimax-h3-int8-convrot'),
                ('nvfp4-awq', 'qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors', 'qwen3vl-32b-minimax-h3-nvfp4-awq'),
            ):
                old = root/'minimax-h3-i2v/text_encoders'/filename
                old.parent.mkdir(parents=True, exist_ok=True)
                old.write_bytes(variant.encode())
                self.assertEqual(resolve_minimax_qwen_encoder(root, variant), old)
                new = root/directory/filename
                new.parent.mkdir()
                old.rename(new)
                self.assertEqual(resolve_minimax_qwen_encoder(root, variant), new)
                old.write_bytes(b'duplicate')
                with self.assertRaises(ValueError):
                    resolve_minimax_qwen_encoder(root, variant)
                old.unlink()

    def test_vace_tokenizer_path_tracks_move_and_rejects_conflict(self):
        from workflow.common.model_storage_layout import resolve_vace_tokenizer_directory
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            old = root/'wan22-vace/official-tokenizer'
            new = root/'umt5-xxl-tokenizer-vace'
            old.mkdir(parents=True)
            self.assertEqual(resolve_vace_tokenizer_directory(root), old)
            old.rename(new)
            self.assertEqual(resolve_vace_tokenizer_directory(root), new)
            old.mkdir()
            with self.assertRaises(ValueError):
                resolve_vace_tokenizer_directory(root)

    def test_vace_bf16_encoder_path_tracks_move_and_rejects_conflict(self):
        from workflow.common.model_storage_layout import resolve_vace_bf16_encoder
        from generators.wan_vace.contracts import vace_model_path, vace_model_records
        with TemporaryDirectory() as temporary:
            project = Path(temporary)
            root = project/'.model'
            old = root/'wan22-vace/models_t5_umt5-xxl-enc-bf16.pth'
            old.parent.mkdir(parents=True)
            old.write_bytes(b'encoder')
            self.assertEqual(vace_model_path('encoder', root=project), old)
            new = root/'umt5-xxl-encoder-bf16'/old.name
            new.parent.mkdir()
            old.rename(new)
            self.assertEqual(resolve_vace_bf16_encoder(root), new)
            self.assertEqual(vace_model_path('encoder', root=project), new)
            self.assertEqual(vace_model_records(root=project)['encoder'][0],
                             '.model/umt5-xxl-encoder-bf16/'+old.name)
            old.write_bytes(b'duplicate')
            with self.assertRaises(ValueError):
                vace_model_path('encoder', root=project)

    def test_animate_reference_models_guarded_move_and_rollback(self):
        from workflow.common.model_storage_move import move_flattened_with_queue_guard
        for name, old, new in (
            ('animate-yolov10m-top', 'det', 'yolov10m-animate'),
            ('animate-vitpose-top', 'pose2d/vitpose_h_wholebody.onnx', 'vitpose-h-wholebody-animate'),
        ):
            with self.subTest(name=name), TemporaryDirectory() as temporary:
                project = Path(temporary)
                source = project/'.model/wan22-animate-preprocess/process_checkpoint'/old
                source.mkdir(parents=True)
                (source/'weights').write_bytes(b'known')
                queue = project/'.tmp/gpu-queue'
                (queue/'active').mkdir(parents=True)
                (queue/'execution.lock').touch()
                backup = project/'.local/hermes/model-backup-verification'
                backup.mkdir(parents=True)
                (backup/'worker.lock').touch()
                def reject():
                    raise ValueError('consumer unavailable')
                with self.assertRaisesRegex(ValueError, 'consumer unavailable'):
                    move_flattened_with_queue_guard(project, project/'move.json', name=name, validate=reject)
                self.assertEqual((source/'weights').read_bytes(), b'known')
                self.assertFalse((project/'.model'/new).exists())

    def test_pose_model_files_follow_separate_paths_and_reject_conflicts(self):
        from workflow.common.model_storage_layout import resolve_pose_model_file
        with TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root/'wan22-fun-pose'
            legacy.mkdir()
            for name, target in (('yolox_l.onnx', 'yolox-l'),
                                 ('dw-ll_ucoco_384.cuda.onnx', 'dwpose-ll-ucoco-384')):
                old = legacy/name
                old.write_bytes(b'weight')
                self.assertEqual(resolve_pose_model_file(root, name), old)
                new = root/target/name
                new.parent.mkdir(exist_ok=True)
                old.rename(new)
                self.assertEqual(resolve_pose_model_file(root, name), new)
                old.write_bytes(b'duplicate')
                with self.assertRaises(ValueError):
                    resolve_pose_model_file(root, name)
                old.unlink()
                new.unlink()
                self.assertEqual(resolve_pose_model_file(root, name), new)
            with self.assertRaises(ValueError):
                resolve_pose_model_file(root, '../unknown')

    def test_guarded_flatten_refuses_active_job_and_rolls_back_failed_consumer(self):
        from workflow.common.model_storage_move import move_flattened_with_queue_guard
        with TemporaryDirectory() as temporary:
            project = Path(temporary)
            old = project / '.model/models/qwen3-embedding-0.6b'
            old.mkdir(parents=True)
            (old / 'weights').write_bytes(b'known')
            queue = project / '.tmp/gpu-queue'
            active = queue / 'active'
            active.mkdir(parents=True)
            (queue / 'execution.lock').touch()
            backup = project / '.local/hermes/model-backup-verification'
            backup.mkdir(parents=True)
            (backup / 'worker.lock').touch()
            reservation = active / 'job.json'
            reservation.write_text('{}')
            journal = project / 'move.json'
            with self.assertRaisesRegex(ValueError, '예약'):
                move_flattened_with_queue_guard(project, journal, name='flatten-writer-embedding', validate=lambda: None)
            self.assertFalse(journal.exists())
            reservation.unlink()
            def reject():
                raise ValueError('consumer unavailable')
            with self.assertRaisesRegex(ValueError, 'consumer unavailable'):
                move_flattened_with_queue_guard(project, journal, name='flatten-writer-embedding', validate=reject)
            self.assertEqual((old / 'weights').read_bytes(), b'known')
            self.assertFalse((project / '.model/qwen3-embedding-0.6b').exists())

    def test_vace_lora_moves_require_lightning_first_and_rollback(self):
        from workflow.common.model_storage_move import move_verified_storage
        with TemporaryDirectory() as temporary:
            project = Path(temporary)
            root = project/'.model'
            old = root/'wan22-vace-loras'
            lightning = old/'lightning-t2v-v1.1'
            lightning.mkdir(parents=True)
            (lightning/'high').write_bytes(b'lightning')
            (old/'fighting').write_bytes(b'fighting')
            with self.assertRaisesRegex(ValueError, 'Lightning'):
                assess_storage_move(root, 'vace-fighting-top')
            journal = project/'lightning.json'
            move_verified_storage(root, journal, name='vace-lightning-top')
            fighting_journal = project/'fighting.json'
            move_verified_storage(root, fighting_journal, name='vace-fighting-top')
            self.assertEqual((root/'wan22-fighting-lora-high/fighting').read_bytes(), b'fighting')
            rollback_storage(root, 'vace-fighting-top', fighting_journal)
            rollback_storage(root, 'vace-lightning-top', journal)
            self.assertEqual((lightning/'high').read_bytes(), b'lightning')
            self.assertEqual((old/'fighting').read_bytes(), b'fighting')

    def test_vace_lora_paths_follow_move_and_reject_conflict(self):
        from workflow.common.model_storage_layout import resolve_wan_vace_lora_directory
        for component, old_path, new_path in (
                ('lightning', 'wan22-vace-loras/lightning-t2v-v1.1', 'wan22-lightning-t2v-v11'),
                ('fighting', 'wan22-vace-loras', 'wan22-fighting-lora-high')):
            with self.subTest(component=component), TemporaryDirectory() as temporary:
                root = Path(temporary)/'.model'
                old, new = root/old_path, root/new_path
                old.mkdir(parents=True)
                self.assertEqual(resolve_wan_vace_lora_directory(root, component), old)
                old.rename(new)
                self.assertEqual(resolve_wan_vace_lora_directory(root, component), new)
                old.mkdir(parents=True)
                with self.assertRaises(ValueError):
                    resolve_wan_vace_lora_directory(root, component)

    def test_wan_shared_paths_resolve_before_after_and_reject_conflict(self):
        from workflow.common.model_storage_layout import resolve_wan_shared_model_directory
        for component, old, new in (('umt5', 'text_encoders', 'umt5-xxl-fp16'),
                                    ('vae', 'vae', 'wan-2.1-vae')):
            with self.subTest(component=component), TemporaryDirectory() as temporary:
                root = Path(temporary)/'.model'
                previous = root/'wan22-animate-components/split_files'/old
                current = root/new
                previous.mkdir(parents=True)
                self.assertEqual(resolve_wan_shared_model_directory(root, component), previous)
                previous.rename(current)
                self.assertEqual(resolve_wan_shared_model_directory(root, component), current)
                previous.mkdir()
                with self.assertRaises(ValueError):
                    resolve_wan_shared_model_directory(root, component)

    def test_wan_legacy_cache_move_can_be_rolled_back(self):
        from workflow.common.model_storage_move import move_verified_storage
        with TemporaryDirectory() as temporary:
            project = Path(temporary)
            root = project/'.model'
            old = root/'wan22-animate-components/.cache/huggingface'
            old.mkdir(parents=True)
            (old/'metadata').write_bytes(b'cache metadata')
            (project/'.cache').mkdir()
            journal = project/'move.json'
            move_verified_storage(root, journal, name='wan-components-legacy-cache')
            new = project/'.cache/wan22-animate-components-legacy/.cache/huggingface/metadata'
            self.assertEqual(new.read_bytes(), b'cache metadata')
            rollback_storage(root, 'wan-components-legacy-cache', journal)
            self.assertEqual((old/'metadata').read_bytes(), b'cache metadata')

    def test_i2v_lightning_guarded_move_rolls_back_on_consumer_failure(self):
        from workflow.common.model_storage_move import move_flattened_with_queue_guard
        with TemporaryDirectory() as temporary:
            project = Path(temporary)
            source = project/'.model/wan22-i2v/lightning'
            source.mkdir(parents=True)
            (source/'high.safetensors').write_bytes(b'known')
            queue = project/'.tmp/gpu-queue'
            (queue/'active').mkdir(parents=True)
            (queue/'execution.lock').touch()
            backup = project/'.local/hermes/model-backup-verification'
            backup.mkdir(parents=True)
            (backup/'worker.lock').touch()
            def reject():
                raise ValueError('consumer unavailable')
            with self.assertRaisesRegex(ValueError, 'consumer unavailable'):
                move_flattened_with_queue_guard(project, project/'move.json', name='i2v-lightning-top', validate=reject)
            self.assertEqual((source/'high.safetensors').read_bytes(), b'known')
            self.assertFalse((project/'.model/wan22-lightning-i2v-seko-v1').exists())

    def test_i2v_kungfu_guarded_move_rolls_back_on_consumer_failure(self):
        from workflow.common.model_storage_move import move_flattened_with_queue_guard
        with TemporaryDirectory() as temporary:
            project = Path(temporary)
            source = project/'.model/wan22-i2v/kungfu'
            source.mkdir(parents=True)
            (source/'high.safetensors').write_bytes(b'known')
            queue = project/'.tmp/gpu-queue'
            (queue/'active').mkdir(parents=True)
            (queue/'execution.lock').touch()
            backup = project/'.local/hermes/model-backup-verification'
            backup.mkdir(parents=True)
            (backup/'worker.lock').touch()
            def reject():
                raise ValueError('consumer unavailable')
            with self.assertRaisesRegex(ValueError, 'consumer unavailable'):
                move_flattened_with_queue_guard(project, project/'move.json', name='i2v-kungfu-top', validate=reject)
            self.assertEqual((source/'high.safetensors').read_bytes(), b'known')
            self.assertFalse((project/'.model/wan22-i2v-kungfu').exists())

    def test_wan_components_guarded_move_and_rollback(self):
        from workflow.common.model_storage_move import move_flattened_with_queue_guard
        for name, old, new in (('wan-umt5-top', 'text_encoders', 'umt5-xxl-fp16'),
                               ('wan-vae-top', 'vae', 'wan-2.1-vae')):
            with self.subTest(name=name), TemporaryDirectory() as temporary:
                project = Path(temporary)
                source = project/'.model/wan22-animate-components/split_files'/old
                source.mkdir(parents=True)
                (source/'weights').write_bytes(b'known')
                queue = project/'.tmp/gpu-queue'
                (queue/'active').mkdir(parents=True)
                (queue/'execution.lock').touch()
                backup = project/'.local/hermes/model-backup-verification'
                backup.mkdir(parents=True)
                (backup/'worker.lock').touch()
                journal = project/'move.json'
                def reject():
                    raise ValueError('consumer unavailable')
                with self.assertRaisesRegex(ValueError, 'consumer unavailable'):
                    move_flattened_with_queue_guard(project, journal, name=name, validate=reject)
                self.assertEqual((source/'weights').read_bytes(), b'known')
                self.assertFalse((project/'.model'/new).exists())

    def test_flatten_move_verifies_and_can_restore_original_directory(self):
        from workflow.common.model_storage_move import move_verified_storage
        with TemporaryDirectory() as directory:
            project = Path(directory)
            root = project / '.model'
            old = root / 'models/qwen3-embedding-0.6b'
            old.mkdir(parents=True)
            (old / 'weights').write_bytes(b'known-model')
            journal = project / 'move.json'
            result = move_verified_storage(root, journal, name='flatten-writer-embedding')
            new = root / 'qwen3-embedding-0.6b'
            self.assertEqual(result['verified_files'], 1)
            self.assertEqual((new / 'weights').read_bytes(), b'known-model')
            self.assertFalse(old.exists())
            rollback_storage(root, 'flatten-writer-embedding', journal)
            self.assertEqual((old / 'weights').read_bytes(), b'known-model')
            self.assertFalse(new.exists())

    def test_flattened_paths_resolve_after_existing_nested_paths_move(self):
        from workflow.common.model_storage_layout import (resolve_writer_embedding_directory,
            resolve_translation_model_directory, resolve_audio_model_directory)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            cases = [
                ('hermes-coding', resolve_hermes_model_directory),
                ('qwen3-embedding-0.6b', resolve_writer_embedding_directory),
                ('translategemma-4b', resolve_translation_model_directory),
                ('audio/heartmula', lambda r: resolve_audio_model_directory(r, 'music-heartmula')),
                ('audio/dasheng-audiogen', lambda r: resolve_audio_model_directory(r, 'sfx-dasheng-audiogen')),
            ]
            for relative, resolver in cases:
                nested, flat = root / 'models' / relative, root / relative
                nested.mkdir(parents=True)
                flat.parent.mkdir(parents=True, exist_ok=True)
                self.assertEqual(resolver(root), nested)
                nested.rename(flat)
                self.assertEqual(resolver(root), flat)

    def test_fresh_models_use_reorganized_paths(self):
        from workflow.common.model_storage_layout import (resolve_writer_embedding_directory,
            resolve_translation_model_directory, resolve_audio_model_directory)
        with TemporaryDirectory() as directory:
            root = Path(directory) / '.model'
            self.assertEqual(resolve_hermes_model_directory(root), root / 'qwen3.8-27b-iq4-xs')
            self.assertEqual(resolve_writer_embedding_directory(root), root / 'qwen3-embedding-0.6b')
            self.assertEqual(resolve_translation_model_directory(root), root / 'translategemma-4b')
            self.assertEqual(resolve_audio_model_directory(root, 'music-heartmula'), root.parent / '.local/audio-model-runtime/heartmula')
            self.assertEqual(resolve_audio_model_directory(root, 'sfx-dasheng-audiogen'), root.parent / '.local/audio-model-runtime/dasheng-audiogen')
            (root / 'prompt-translation').mkdir(parents=True)
            self.assertEqual(resolve_translation_model_directory(root), root / 'prompt-translation')

    def test_qwen_path_preferred_after_move_and_conflict_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)/'.model'
            old = root/'hermes-coding'
            old.mkdir(parents=True)
            self.assertEqual(resolve_hermes_model_directory(root), old)
            new = root/'qwen3.8-27b-iq4-xs'
            old.rename(new)
            self.assertEqual(resolve_hermes_model_directory(root), new)
            old.mkdir()
            with self.assertRaises(ValueError):
                resolve_hermes_model_directory(root)

    def test_audio_manager_observes_directory_move(self):
        from unittest.mock import patch
        from generators.music import contracts
        from workflow.domains.music.generation import MusicGenerationManager
        with TemporaryDirectory() as directory:
            project = Path(directory)
            old = project / '.model/music/music-heartmula'
            old.mkdir(parents=True)
            with patch.object(contracts, 'WORKFLOW_ROOT_DIRECTORY', project):
                manager = MusicGenerationManager('music-heartmula')
                self.assertEqual(manager.model_storage_root, old)
                target = project / '.model/models/audio/heartmula'
                target.parent.mkdir(parents=True)
                old.rename(target)
                self.assertEqual(manager.model_storage_root, target)

    def test_nested_legacy_backup_path_rejects_symlink(self):
        from workflow.common.model_backup_targets import LEGACY_TARGETS, target_path
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'other').mkdir()
            (root / 'music').symlink_to(root / 'other', target_is_directory=True)
            with self.assertRaises(ValueError):
                target_path(root, LEGACY_TARGETS['catalog-heartmula'])

    def test_translation_resolves_move_and_legacy_manifest(self):
        from unittest.mock import patch
        from workflow.domains.translation import service
        from generators.prompt_translation.prepare import resolve_translation_snapshot
        revision = '1' * 40
        with TemporaryDirectory() as directory:
            project = Path(directory)
            old = project / '.model/prompt-translation'
            old.mkdir(parents=True)
            record = {'revision': revision, 'snapshot': str(old / revision)}
            with patch.object(service, 'WORKFLOW_ROOT_DIRECTORY', project):
                self.assertEqual(service.current_translation_model_root(), old)
                target = project / '.model/models/translategemma-4b'
                target.parent.mkdir()
                old.rename(target)
                self.assertEqual(service.current_translation_model_root(), target)
                self.assertEqual(resolve_translation_snapshot(target, record), target / revision)

    def test_writer_embedding_resolves_after_move_in_long_lived_process(self):
        from unittest.mock import patch
        from generators.writer_agent import prepare
        with TemporaryDirectory() as directory:
            project = Path(directory)
            old = project / '.model/writer-agent'
            old.mkdir(parents=True)
            with patch.object(prepare, 'WORKFLOW_REPOSITORY_ROOT', project):
                self.assertEqual(prepare.embedding_model_directory(), old)
                target = project / '.model/models/qwen3-embedding-0.6b'
                target.parent.mkdir()
                old.rename(target)
                self.assertEqual(prepare.embedding_model_directory(), target)

    def test_external_cache_move_preserves_links_and_supports_rollback(self):
        with TemporaryDirectory() as directory:
            project = Path(directory)
            root = project / '.model'
            old = root / 'cache/huggingface'
            old.mkdir(parents=True)
            snapshot = resolve_minimax_snapshot(root)
            (snapshot / 'text_encoder').mkdir(parents=True)
            blobs = snapshot.parent.parent / 'blobs'
            blobs.mkdir()
            (blobs / 'config').write_text('{}')
            (snapshot / 'text_encoder/config.json').symlink_to('../../../blobs/config')
            queue = project / '.tmp/gpu-queue'
            (queue / 'active').mkdir(parents=True)
            (queue / 'execution.lock').touch()
            backup = project / '.local/hermes/model-backup-verification'
            backup.mkdir(parents=True)
            (backup / 'worker.lock').touch()
            journal = project / 'external-migration.json'
            result = move_cache_with_queue_guard(project, journal, name='external-hf-cache')
            self.assertEqual(result['verified_links'], 1)
            self.assertEqual(resolve_huggingface_cache(root), project / '.cache/huggingface')
            self.assertEqual((resolve_minimax_snapshot(root) / 'text_encoder/config.json').read_text(), '{}')
            rollback_storage(root, 'external-hf-cache', journal)
            self.assertEqual(resolve_huggingface_cache(root), old)
            self.assertEqual((snapshot / 'text_encoder/config.json').read_text(), '{}')

    def test_guard_refuses_active_queue_and_moves_only_when_idle(self):
        with TemporaryDirectory() as directory:
            project = Path(directory)
            root = project / '.model'
            (root / 'huggingface').mkdir(parents=True)
            snapshot = resolve_minimax_snapshot(root)
            (snapshot / 'text_encoder').mkdir(parents=True)
            (snapshot / 'text_encoder/config.json').write_text('{}')
            queue = project / '.tmp/gpu-queue'
            active = queue / 'active'
            active.mkdir(parents=True)
            (queue / 'execution.lock').touch()
            backup = project / '.local/hermes/model-backup-verification'
            backup.mkdir(parents=True)
            (backup / 'worker.lock').touch()
            reservation = active / 'job.json'
            reservation.write_text('{}')
            journal = project / 'migration.json'
            with self.assertRaisesRegex(ValueError, '예약'):
                move_cache_with_queue_guard(project, journal)
            self.assertFalse(journal.exists())
            self.assertTrue(snapshot.is_dir())
            reservation.unlink()
            result = move_cache_with_queue_guard(project, journal)
            self.assertEqual(result['id'], 'minimax-hf-cache')
            self.assertTrue((resolve_minimax_snapshot(root) / 'text_encoder/config.json').is_file())

    def test_guard_rolls_back_if_service_validation_fails(self):
        with TemporaryDirectory() as directory:
            project = Path(directory)
            root = project / '.model'
            (root / 'huggingface').mkdir(parents=True)
            snapshot = resolve_minimax_snapshot(root)
            (snapshot / 'text_encoder').mkdir(parents=True)
            (snapshot / 'text_encoder/config.json').write_text('{}')
            queue = project / '.tmp/gpu-queue'
            (queue / 'active').mkdir(parents=True)
            (queue / 'execution.lock').touch()
            backup = project / '.local/hermes/model-backup-verification'
            backup.mkdir(parents=True)
            (backup / 'worker.lock').touch()
            def reject():
                raise ValueError('서비스 검증 실패')
            with self.assertRaisesRegex(ValueError, '서비스 검증 실패'):
                move_cache_with_queue_guard(project, project / 'migration.json', validate=reject)
            self.assertTrue((snapshot / 'text_encoder/config.json').is_file())
            self.assertFalse((root / 'cache/huggingface').exists())

    def test_guard_refuses_busy_backup(self):
        import fcntl
        with TemporaryDirectory() as directory:
            project = Path(directory)
            (project / '.model/huggingface').mkdir(parents=True)
            queue = project / '.tmp/gpu-queue'
            (queue / 'active').mkdir(parents=True)
            (queue / 'execution.lock').touch()
            backup = project / '.local/hermes/model-backup-verification'
            backup.mkdir(parents=True)
            with (backup / 'worker.lock').open('w+') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError):
                    move_cache_with_queue_guard(project, project / 'migration.json')
            self.assertTrue((project / '.model/huggingface').is_dir())

    def test_verified_cache_move_rolls_back_on_post_move_mismatch(self):
        from unittest.mock import patch
        from workflow.common.model_backup_inventory import inventory_model_tree
        with TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / '.model'
            source = root / 'huggingface'
            source.mkdir(parents=True)
            (source / 'file').write_bytes(b'data')
            calls = []
            def inspect(*args, **kwargs):
                result = inventory_model_tree(*args, **kwargs)
                calls.append(1)
                if len(calls) == 2:
                    result['files']['file']['sha256'] = '0' * 64
                return result
            with patch('workflow.common.model_backup_inventory.inventory_model_tree', side_effect=inspect):
                with self.assertRaises(ValueError):
                    move_verified_cache(root, base / 'journal.json')
            self.assertEqual((source / 'file').read_bytes(), b'data')
            self.assertFalse((root / 'cache/huggingface').exists())

    def test_verified_cache_move_checks_content_and_link(self):
        with TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / '.model'
            source = root / 'huggingface'
            source.mkdir(parents=True)
            (source / 'file').write_bytes(b'data')
            (source / 'link').symlink_to('file')
            result = move_verified_cache(root, base / 'journal.json')
            self.assertEqual((result['verified_files'], result['verified_links']), (2, 1))
            self.assertEqual((root / 'cache/huggingface/link').read_bytes(), b'data')

    def test_safe_move_preserves_cache_links_and_rejects_existing_destination(self):
        with TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / '.model'
            snapshot = root / 'huggingface/hub/repo/snapshots/revision'
            blobs = snapshot.parent.parent / 'blobs'
            snapshot.mkdir(parents=True); blobs.mkdir()
            (blobs / 'item').write_bytes(b'model')
            (snapshot / 'item').symlink_to('../../blobs/item')
            plan = assess_storage_move(root, 'minimax-hf-cache')
            self.assertTrue(plan['requires_quiescence'])
            self.assertEqual(len(plan['relative_links']), 1)
            move_storage(root, 'minimax-hf-cache', base / 'journal.json')
            self.assertFalse((root / 'huggingface').exists())
            self.assertEqual((root / 'cache/huggingface/hub/repo/snapshots/revision/item').read_bytes(), b'model')
            self.assertTrue((base / 'journal.json').is_file())
            (root / 'huggingface').mkdir()
            with self.assertRaises(ValueError):
                move_storage(root, 'minimax-hf-cache', base / 'again.json')
            self.assertTrue((root / 'huggingface').is_dir())
            with self.assertRaises(OSError):
                rollback_storage(root, 'minimax-hf-cache', base / 'journal.json')
            (root / 'huggingface').rmdir()
            rollback_storage(root, 'minimax-hf-cache', base / 'journal.json')
            self.assertEqual((snapshot / 'item').read_bytes(), b'model')
            self.assertFalse((root / 'cache/huggingface').exists())

    def test_move_rejects_external_links(self):
        with TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / '.model'
            source = root / 'huggingface'
            source.mkdir(parents=True)
            (base / 'outside').write_text('preserve')
            (source / 'external').symlink_to('../../outside')
            with self.assertRaises(ValueError):
                assess_storage_move(root, 'minimax-hf-cache')
            self.assertTrue(source.is_dir())

    def test_existing_path_is_preferred_until_explicit_move(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old, new = root / 'hermes-agent', root / 'models/hermes-coding'
            old.mkdir(); new.mkdir(parents=True)
            self.assertEqual(resolve_hermes_model_directory(root), old)
            old.rename(root / 'preserved')
            self.assertEqual(resolve_hermes_model_directory(root), new)

    def test_cache_move_preserves_relative_links(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / 'huggingface'
            cache.mkdir()
            snapshot = resolve_minimax_snapshot(root)
            snapshot.mkdir(parents=True)
            blobs = snapshot.parent.parent / 'blobs'
            blobs.mkdir()
            (blobs / 'config').write_text('ok')
            (snapshot / 'config').symlink_to('../../blobs/config')
            self.assertEqual(resolve_huggingface_cache(root), cache)
            (root / 'cache').mkdir()
            cache.rename(root / 'cache/huggingface')
            self.assertEqual(resolve_huggingface_cache(root), root / 'cache/huggingface')
            self.assertEqual(resolve_minimax_snapshot(root).name, snapshot.name)
            self.assertEqual((resolve_minimax_snapshot(root) / 'config').read_text(), 'ok')

    def test_new_storage_symlink_is_not_selected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'cache').mkdir()
            (root / 'outside').mkdir()
            (root / 'cache/huggingface').symlink_to(root / 'outside', target_is_directory=True)
            self.assertEqual(resolve_huggingface_cache(root), root / 'huggingface')

    def test_new_cache_defaults_outside_model(self):
        with TemporaryDirectory() as directory:
            project = Path(directory)
            root = project / '.model'
            self.assertEqual(resolve_huggingface_cache(root), project / '.cache/huggingface')
            (root / 'huggingface').mkdir(parents=True)
            self.assertEqual(resolve_huggingface_cache(root), root / 'huggingface')


if __name__ == '__main__':
    unittest.main()

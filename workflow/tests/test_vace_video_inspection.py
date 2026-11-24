"""VACE UI의 공용 영상 검사와 실제 입력 길이 계약을 비교한다."""
import tempfile
import unittest
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

from generators.wan_fun.video_input import inspect_fun_pose_video
from generators.wan_vace.video_edit import decode_edit_video


class VaceVideoInspectionTests(unittest.TestCase):
    def test_reported_limit_is_decodable_and_longer_request_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'input.mp4'
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), 16, (832, 480))
            self.assertTrue(writer.isOpened())
            try:
                frame = np.zeros((480, 832, 3), dtype=np.uint8)
                for _ in range(23):
                    writer.write(frame)
            finally:
                writer.release()
            maximum, summary = inspect_fun_pose_video(path)
            self.assertEqual(maximum, 21)
            self.assertIn('23프레임', summary)
            script="""import fs from 'node:fs';import vm from 'node:vm';import {untilAborted} from './gui/managementCommand.js';
              let input='';for await(const part of process.stdin)input+=part;const payload=JSON.parse(input);
              const source=fs.readFileSync('./gui/VacePage.jsx','utf8');const code=source.slice(source.indexOf('  async function inspectVideo('),source.indexOf('  async function selectVideo('));
              const context=vm.createContext({untilAborted,fetch:async()=>({ok:true,json:async()=>payload})});vm.runInContext(code,context);
              const result=await context.inspectVideo({},new AbortController().signal);if(result.maximum_frames!==21)process.exit(1);"""
            subprocess.run(['node','--input-type=module','-e',script],cwd=Path(__file__).resolve().parents[2],input=json.dumps({'maximum_frames':maximum,'summary':summary}),text=True,check=True)
            self.assertEqual(len(decode_edit_video(path, maximum)), maximum)
            with self.assertRaisesRegex(ValueError, '프레임이 부족'):
                decode_edit_video(path, 25)

    def test_inspector_rejects_wrong_dimensions_and_rate(self):
        with tempfile.TemporaryDirectory() as temporary:
            for width, height, fps in ((640, 480, 16), (832, 480, 24)):
                with self.subTest(width=width, fps=fps):
                    path = Path(temporary) / f'{width}-{fps}.mp4'
                    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
                    self.assertTrue(writer.isOpened())
                    try:
                        for _ in range(5):
                            writer.write(np.zeros((height, width, 3), dtype=np.uint8))
                    finally:
                        writer.release()
                    maximum, summary = inspect_fun_pose_video(path)
                    self.assertIsNone(maximum)
                    self.assertIn('832×480·16fps', summary)
                    with self.assertRaisesRegex(ValueError, '832×480, 16fps'):
                        decode_edit_video(path, 5)

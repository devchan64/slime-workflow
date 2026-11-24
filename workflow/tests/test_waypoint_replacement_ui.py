"""웨이포인트 교체 입력의 기본 안내 연결을 확인한다."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


class WaypointReplacementUiTests(unittest.TestCase):
    def test_json_input_has_help_and_explicit_button_type(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'effect.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'EffectEditor.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server'),Form=require(process.argv[1]).WaypointReplacement;
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Form,{detail:{document:{id:'waypoint'},revision:'r'},onDirtyChange:()=>{},onBusyChange:()=>{},onSaved:()=>{}})));"""
            markup = subprocess.check_output(['node', '-e', script, str(bundle)], cwd=gui, text=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
        identifier = re.search(r'<textarea[^>]*aria-describedby="([^"]+)"', markup).group(1)
        self.assertIn(f'id="{identifier}">JSON 형식으로 편집한 뒤', markup)
        self.assertIn('<button type="button">교체 내용 확인</button>', markup)

    def test_preview_frame_controls_explain_playback_lock(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'effect.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'EffectEditor.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server'),{AlignmentPreview,WaypointPreview}=require(process.argv[1]),e=React.createElement;
              const frame={rect:{x:0,y:0,width:10,height:10},anchor:{x:0,y:0}};
              const detail={document:{frames:1},animationMetadata:{frames:[frame]}};
              process.stdout.write(server.renderToStaticMarkup(e(React.Fragment,null,e(AlignmentPreview,{detail,values:{frames:[[]]}}),e(WaypointPreview,{detail}))));"""
            markup = subprocess.check_output(['node', '-e', script, str(bundle)], cwd=gui, text=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
        ranges = re.findall(r'<input[^>]*type="range"[^>]*>', markup)
        self.assertEqual(len(ranges), 2)
        for item in ranges:
            self.assertIn('disabled=""', item)
            identifier = re.search(r'aria-describedby="([^"]+)"', item).group(1)
            self.assertIn(f'id="{identifier}">재생을 멈추면 프레임을 선택할 수 있습니다.', markup)

    def test_reduced_motion_starts_both_previews_paused(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'effect.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'EffectEditor.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """global.matchMedia=()=>({matches:true});
              const React=require('react'),server=require('react-dom/server'),{AlignmentPreview,WaypointPreview}=require(process.argv[1]),e=React.createElement;
              const frame={rect:{x:0,y:0,width:10,height:10},anchor:{x:0,y:0}};
              const detail={document:{frames:1},animationMetadata:{frames:[frame]}};
              process.stdout.write(server.renderToStaticMarkup(e(React.Fragment,null,e(AlignmentPreview,{detail,values:{frames:[[]]}}),e(WaypointPreview,{detail}))));"""
            markup = subprocess.check_output(['node', '-e', script, str(bundle)], cwd=gui, text=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
        ranges = re.findall(r'<input[^>]*type="range"[^>]*>', markup)
        self.assertEqual(len(ranges), 2)
        self.assertTrue(all('disabled=' not in item for item in ranges))
        self.assertEqual(markup.count('1 / 1 프레임'), 2)

    def test_alignment_coordinate_inputs_share_range_help(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'effect.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'EffectEditor.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server'),Form=require(process.argv[1]).Alignment;
              const row=[0,0,1,1],detail={document:{alignment:{target:row,frames:Array(8).fill(row),alpha:1}},revision:'r'};
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Form,{detail,onDirtyChange:()=>{},onBusyChange:()=>{}})));"""
            markup = subprocess.check_output(['node', '-e', script, str(bundle)], cwd=gui, text=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
        coordinates = re.findall(r'<input(?=[^>]*type="number")[^>]*aria-describedby="([^"]+)"[^>]*>', markup)
        self.assertEqual(len(coordinates), 36)
        self.assertEqual(len(set(coordinates)), 1)
        self.assertIn(f'id="{coordinates[0]}">좌표는 0부터 1까지', markup)

    def test_alignment_error_is_attached_only_to_affected_rectangle(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'effect.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'EffectEditor.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server'),Inputs=require(process.argv[1]).AlignmentRectangleInputs,e=React.createElement;
              const props={row:[0,0,1,1],helpId:'help',errorId:'error',error:{group:'frame:1',message:'오류'},onChange:()=>{}};
              process.stdout.write(server.renderToStaticMarkup(e(React.Fragment,null,e(Inputs,{...props,group:'target'}),e(Inputs,{...props,group:'frame:1'}))));"""
            markup = subprocess.check_output(['node', '-e', script, str(bundle)], cwd=gui, text=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
        self.assertEqual(markup.count('aria-invalid="true"'), 4)
        self.assertEqual(markup.count('aria-describedby="help error"'), 4)
        self.assertEqual(markup.count('aria-describedby="help"'), 4)


if __name__ == '__main__':
    unittest.main()

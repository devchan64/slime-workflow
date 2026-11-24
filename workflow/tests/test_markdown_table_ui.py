"""본문 표가 표 의미를 유지하며 공통 스크롤 영역에 표시되는지 확인한다."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class MarkdownTableUiTests(unittest.TestCase):
    def test_table_markup_preserves_headers_and_cells(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'table.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'MarkdownTable.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """const React=require('react'),server=require('react-dom/server'),Table=require(process.argv[1]).default;
              const e=React.createElement;
              process.stdout.write(server.renderToStaticMarkup(e(Table,{node:{type:'element'}},e('thead',null,e('tr',null,e('th',{scope:'col'},'이름'))),e('tbody',null,e('tr',null,e('td',null,'값'))))));"""
            markup = subprocess.check_output(['node', '-e', script, str(bundle)], cwd=gui, text=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
        self.assertIn('class="result-table-scroll"', markup)
        self.assertIn('<th scope="col">이름</th>', markup)
        self.assertIn('<td>값</td>', markup)
        self.assertNotIn('node=', markup)

    def test_gfm_table_renders_through_shared_component(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'table.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'), 'MarkdownTable.jsx', '--bundle', '--platform=node', '--format=cjs', '--external:react', '--outfile='+str(bundle)], cwd=gui, check=True, capture_output=True)
            script = """(async()=>{
              const React=require('react'),server=require('react-dom/server'),Table=require(process.argv[1]).default;
              const {default:Markdown}=await import(require.resolve('react-markdown'));
              const {default:gfm}=await import(require.resolve('remark-gfm'));
              const source='| 이름 | 상태 |\\n| --- | --- |\\n| 예시 | 완료 |';
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Markdown,{remarkPlugins:[gfm],components:{table:Table},skipHtml:true},source)));
            })().catch(error=>{console.error(error);process.exitCode=1;});"""
            markup = subprocess.check_output(['node', '-e', script, str(bundle)], cwd=gui, text=True, env={**os.environ, 'NODE_PATH':str(gui/'node_modules')})
        self.assertIn('class="result-table-scroll"', markup)
        self.assertIn('<th>이름</th>', markup)
        self.assertIn('<td>완료</td>', markup)
        self.assertNotIn('node=', markup)


if __name__ == '__main__':
    unittest.main()

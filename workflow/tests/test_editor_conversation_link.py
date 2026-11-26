"""편집 화면에서 대화 세션을 별도 탭으로 여는 링크 계약."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class EditorConversationLinkTest(unittest.TestCase):
    def test_session_is_encoded_and_editor_opens_conversation_in_new_tab(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'conversation-link.cjs'
            subprocess.run([str(gui / 'node_modules/.bin/esbuild'), 'ConversationLink.jsx', '--bundle',
                            '--platform=node', '--format=cjs', '--external:react', '--outfile=' + str(bundle)],
                           cwd=gui, check=True, capture_output=True)
            script = r"""const assert=require('node:assert/strict'),React=require('react'),server=require('react-dom/server');
              const Link=require(process.argv[1]).default;
              global.location={search:'?session=a%26b'};
              let markup=server.renderToStaticMarkup(React.createElement(Link));
              assert.match(markup,/href="\/management\/frame\/hermes-agent\/\?session=a%26b"/);
              assert.match(markup,/target="_blank"/);assert.match(markup,/rel="noopener noreferrer"/);
              global.location={search:''};markup=server.renderToStaticMarkup(React.createElement(Link));
              assert.match(markup,/href="\/management\/frame\/hermes-agent\/"/);
            """
            subprocess.run(['node', '-e', script, str(bundle)], cwd=gui, check=True, capture_output=True,
                           env={**os.environ, 'NODE_PATH': str(gui / 'node_modules')})

    def test_billboard_search_embedded_in_conversation_omits_return_link(self):
        gui = Path(__file__).resolve().parents[2] / 'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'billboard.cjs'
            subprocess.run([str(gui / 'node_modules/.bin/esbuild'), 'BillboardCatalog.jsx', '--bundle',
                            '--platform=node', '--format=cjs', '--external:react', '--outfile=' + str(bundle)],
                           cwd=gui, check=True, capture_output=True)
            script = r"""const assert=require('node:assert/strict'),React=require('react'),server=require('react-dom/server');
              global.location={search:'?session=abc'};
              const Catalog=require(process.argv[1]).default;
              const render=props=>server.renderToStaticMarkup(React.createElement(Catalog,props));
              assert.match(render({}),/헤르메스 대화 새 탭에서 열기/);
              assert.doesNotMatch(render({choose:()=>{}}),/헤르메스 대화 새 탭에서 열기/);
            """
            subprocess.run(['node', '-e', script, str(bundle)], cwd=gui, check=True, capture_output=True,
                           env={**os.environ, 'NODE_PATH': str(gui / 'node_modules')})

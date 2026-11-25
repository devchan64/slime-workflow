import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class WriterUncertainNavigationUiTests(unittest.TestCase):
    def test_writer_page_and_history_offer_search_navigation(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            for filename,export in [('WriterPage.jsx','default'),('SourceHistory.jsx','HistoryPage')]:
                with self.subTest(page=filename):
                    bundle=Path(directory)/(filename+'.cjs')
                    subprocess.run([str(gui/'node_modules/.bin/esbuild'),filename,'--bundle','--platform=node','--format=cjs','--external:react','--external:react-dom','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
                    script="""global.location={pathname:'/',search:'',href:'http://localhost/'};global.sessionStorage={getItem:()=> '1'};
                      const React=require('react'),server=require('react-dom/server'),Page=require(process.argv[1])[process.argv[2]];
                      console.log(server.renderToStaticMarkup(React.createElement(Page,{source:{service:'writer-agent',command:'history'},choose:()=>{}})));"""
                    markup=subprocess.check_output(['node','-e',script,str(bundle),export],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
                    self.assertIn('실행 이력 검색으로 이동',markup)
                    self.assertIn('실행 이력을 확인했고 새 요청을 작성합니다',markup)
                    self.assertIn('이전 작가 작업의 접수 여부가 확인되지 않았습니다',markup)
                    if filename=='SourceHistory.jsx':
                        self.assertIn('writer-agent 이력과 작업</legend>',markup)
                        self.assertIn('<legend>작가 작업 요청</legend>',markup)
                    else:
                        self.assertIn('<legend class="generator-visually-hidden">작가 작업 요청</legend>',markup)


if __name__=='__main__':
    unittest.main()

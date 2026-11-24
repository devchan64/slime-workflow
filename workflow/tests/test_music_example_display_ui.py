import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class MusicExampleDisplayTests(unittest.TestCase):
    def test_prompt_count_and_apply_guidance(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'music.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'MusicExamples.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server'),Detail=require(process.argv[1]).MusicExampleDetail;
              const row={label:'예제',description:'설명',request:{prompt:'warm  piano\\nstrings',lyrics:'가사',duration_seconds:30,seed:7}};
              process.stdout.write(server.renderToStaticMarkup(React.createElement(Detail,{row,apply:()=>{},onApplied:()=>{}})));"""
            markup=subprocess.check_output(['node','-e',script,str(bundle)],cwd=gui,text=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})
        self.assertIn('예제 프롬프트 3단어',markup)
        self.assertIn('출력 상한 30초',markup)
        self.assertIn('음악 태그, 가사, 출력 시간과 시드',markup)


if __name__ == '__main__':
    unittest.main()

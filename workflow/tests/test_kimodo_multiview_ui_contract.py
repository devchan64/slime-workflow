"""격리된 다중 시점 보고서와 화면 응답 계약을 연결한다."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from generators.kimodo.multiview_provenance import calculate_multiview_observation_hash
from generators.kimodo.multiview_review_report import build_multiview_review_report
from generators.kimodo.reference_review import select_multiview_review_rows


class KimodoMultiviewUiContractTests(unittest.TestCase):
    def test_input_group_has_a_legend(self):
        gui=Path(__file__).resolve().parents[2]/'gui'
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'report.cjs'
            subprocess.run([str(gui/'node_modules/.bin/esbuild'),'KimodoMultiviewReport.jsx','--bundle','--platform=node','--format=cjs','--external:react','--outfile='+str(bundle)],cwd=gui,check=True,capture_output=True)
            script="""const React=require('react'),server=require('react-dom/server');
              const Report=require(process.argv[1]).default;
              const html=server.renderToStaticMarkup(React.createElement(Report));
              if(!html.includes('<legend>검수 입력 파일</legend>'))process.exit(1);"""
            subprocess.run(['node','-e',script,str(bundle)],cwd=gui,check=True,env={**os.environ,'NODE_PATH':str(gui/'node_modules')})

    def test_real_report_is_accepted(self):
        weights={'schema':'kimodo-body18-view-weights-v1','views':[{'observation':i+1,'joints':[{'joint':j,'weight':1,'reason':'사용'} for j in range(18)]} for i in range(8)]}
        reference={'keypoints':[[[float(j),float(j),.9] for j in range(18)] for _ in range(8)],'observation_sources':[{'bbox':[0,0,32,32]} for _ in range(8)]}
        views=[{'observation':i+1,'fitted_yaw_degrees':i*45,'body_xy':[[float(j+3),float(j)] for j in range(2,14)],'face_xy':[[float(j+3),float(j)] for j in (0,14,15,16,17)],'body_fit_weights':[.9]*12,'face_fit_weights':[.9]*5} for i in range(8)]
        skeleton={'schema':'kimodo-multiview-body-face-experiment-v1','body18_joint_indices':list(range(2,14)),'face_joint_indices':[0,14,15,16,17],'joint_weight_table':weights,'views':views,'observation_sha256':calculate_multiview_observation_hash(reference)}
        report=build_multiview_review_report(reference,skeleton,None)
        payload={'views':[{'angle':view['fitted_yaw_degrees'],'rows':select_multiview_review_rows(report,view['observation'])} for view in report['views']],'limitations':report['limitations'],'joint_weights':weights}
        gui=Path(__file__).resolve().parents[2]/'gui'
        script="""import {readFileSync} from 'node:fs';import vm from 'node:vm';import {untilAborted} from './managementCommand.js';
          const source=readFileSync('./KimodoMultiviewReport.jsx','utf8');
          const code=source.slice(source.indexOf('  async function load(event)'),source.indexOf('  return <details className="kimodo-multiview">'));
          const payload=JSON.parse(process.argv[1]);let output=null,error='';
          const context=vm.createContext({AbortController,untilAborted,pending:{current:null},dirtyRef:{current:false},restoreFocus:{current:false},submitRef:{current:{}},document:{activeElement:null},
            setTimeout:()=>1,clearTimeout:()=>{},files:{observations:{text:async()=> '{}'},skeleton:{text:async()=> '{}'}},fetch:async()=>({ok:true,json:async()=>payload}),setBusy:()=>{},setError:value=>error=value,
            setView:()=>{},setReport:value=>output=value,setReportRevision:()=>{}});
          vm.runInContext(code,context);await context.load({preventDefault(){}});
          if(error || output!==payload)throw Error(error || 'report rejected');"""
        subprocess.run(['node','--input-type=module','-e',script,json.dumps(payload,ensure_ascii=False)],cwd=gui,check=True,capture_output=True,text=True)


if __name__=='__main__':
    unittest.main()

"""서버가 허용한 앵커 문서를 UI 복원 검증에 연결한다."""
import copy
import json
from pathlib import Path
import subprocess
import unittest

from workflow.domains.character_animation.anchor_history import validate_anchor_document


class SpriteAnchorRestoreContractTests(unittest.TestCase):
    def test_ui_history_id_validation_matches_server(self):
        from workflow.domains.character_animation.anchor_history import resolve_anchor_history_directory
        identifiers=['2026-11-24_12-00-00-1234abcd','../outside','2026-11-24_12-00-00-ABCDEF12','2026-11-24_12-00-00-1234abcd/extra']
        expected=[]
        for identifier in identifiers:
            try:
                resolve_anchor_history_directory(identifier)
                expected.append(True)
            except ValueError:
                expected.append(False)
        script="""import {isSpriteAnchorHistoryId} from './gui/spriteAnchorRestore.mjs';
const [ids,expected]=JSON.parse(process.argv[1]);
if(JSON.stringify(ids.map(isSpriteAnchorHistoryId))!==JSON.stringify(expected))throw Error('history ID mismatch');"""
        result=subprocess.run(['node','--input-type=module','-e',script,json.dumps([identifiers,expected])],cwd=Path(__file__).resolve().parents[2],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_server_validated_modes_restore_in_ui(self):
        rect={'x':0,'y':0,'width':10,'height':20}
        original={'imageSha256':'a'*64,'animation':{'animationId':'test.idle','version':'1','frames':[{'frameId':'down_left.0','rect':rect}]}}
        document={'schemaVersion':1,'artifactType':'character-animation-anchor-review','description':'검수','coordinateMode':'anchor',
            'source':{'animationId':'test.idle','animationVersion':'1','sheets':[{'image':'sheet.png','sha256':'a'*64}]},
            'frames':[{'frameId':'down_left.0','direction':'down_left','image':'sheet.png','rect':rect,'points':[{'x':5,'y':18}],'anchor':{'x':5,'y':18}}]}
        documents=[]
        for mode,points in [('anchor',[(5,18)]),('foot-centers',[(2,17),(6,19)]),('endpoints',[(1,16),(3,18),(5,18),(7,19)])]:
            value=copy.deepcopy(document);value['coordinateMode']=mode;value['frames'][0]['points']=[{'x':x,'y':y} for x,y in points]
            documents.append(validate_anchor_document(value))
        script="""import {restoreSpriteAnchors} from './gui/spriteAnchorRestore.mjs';
const [original,documents]=JSON.parse(process.argv[1]);
for(const doc of documents){const result=restoreSpriteAnchors(doc,original);if(result.rows.length!==1 || result.rows[0].anchorX!==5)throw Error(doc.coordinateMode);}
if(restoreSpriteAnchors(documents[2],original).feet[0][1].y!==18.5)throw Error('endpoints');"""
        result=subprocess.run(['node','--input-type=module','-e',script,json.dumps([original,documents])],cwd=Path(__file__).resolve().parents[2],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)

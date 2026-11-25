"""맵 초기화 실패·화면 이탈 시 렌더러 수명 정리를 검증한다."""
import json
from pathlib import Path
import subprocess
import unittest


class MapReviewLifecycleTests(unittest.TestCase):
    def test_save_revision_observation_does_not_claim_completion(self):
        source=(Path(__file__).resolve().parents[2]/'gui/MapReview.jsx').read_text()
        check='async function inspectSaveRevision(event){'+source.split('async function inspectSaveRevision(event){',1)[1].split('\n  async function inspectCell',1)[0]
        script=r"""
const assert=require('node:assert/strict');let result,feedback='',reading=false;
const readRequest={current:null},importRequest={current:null},savingRef={current:false};
const draft={map:'test',revision:'old'},readMap=async()=>result,setReading=value=>reading=value,setFeedback=value=>feedback=value,requestErrorMessage=e=>e.message,restorePreviewFocus={current:false};
const button={},document={activeElement:button};
SOURCE
(async()=>{for(const [revision,word] of [['old','같습니다'],['new','다릅니다']]){result={map:'test',revision};await inspectSaveRevision({currentTarget:button});assert.equal(restorePreviewFocus.current,true);assert.ok(feedback.includes(word));assert.match(feedback,/완료 여부를 판단할 수 없습니다/);assert.equal(reading,false)}
result={map:'other',revision:'new'};await inspectSaveRevision();assert.match(feedback,/조회 실패/);assert.equal(draft.revision,'old');})().catch(error=>{console.error(error);process.exitCode=1});
""".replace('SOURCE',check)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_save_timeout_keeps_draft_and_reports_uncertainty(self):
        root=Path(__file__).resolve().parents[2]
        source=(root/'gui/MapReview.jsx').read_text()
        save='async function save(event){'+source.split('async function save(event){',1)[1].split('\n  async function inspectCell',1)[0]
        until=(root/'gui/managementCommand.js').read_text().split('\nexport async function managementCommand',1)[0].replace('export async function','async function')
        script=r"""
const assert=require('node:assert/strict');let timer,calls=0,feedback='',reading=false,saving=false,changed=false;
const window={},readRequest={current:null},importRequest={current:null};
const draft={map:'test'},preview={token:'token'},savingRef={current:false},restorePreviewFocus={current:false};
const setTimeout=fn=>{timer=fn;return 1},clearTimeout=()=>{},managementCommand=()=>{calls++;return new Promise(()=>{})};
const mapDraftSaveReason=()=>'',setSaving=value=>saving=value,setReading=value=>reading=value,setFeedback=value=>feedback=value,setPreview=()=>{},setSaveUncertain=()=>{};
const requestErrorMessage=e=>e.message,setDraft=()=>changed=true;
UNTIL
SOURCE
(async()=>{const pending=save();await save();assert.equal(calls,1);timer();await pending;assert.equal(changed,false);assert.equal(reading,false);assert.equal(saving,false);assert.equal(savingRef.current,false);assert.match(feedback,/원본 상태를 확인/);assert.match(feedback,/초과/);})().catch(e=>{console.error(e);process.exitCode=1});
""".replace('SOURCE',save).replace('UNTIL',until)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_new_edit_requires_autosave_confirmation(self):
        source=(Path(__file__).resolve().parents[2]/'gui/MapReview.jsx').read_text()
        apply='async function applyDraft(next,action,stroke=null){'+source.split('async function applyDraft(next,action,stroke=null){',1)[1].split('\n  async function save(',1)[0]
        script=r"""
const assert=require('node:assert/strict');let storageFailed=false,applied=false;
const window={},readRequest={current:null},importRequest={current:null},savingRef={current:false};
const cellDirty=false,draft={map:'test'},past=[],future=[],cell=null;
const readMap=async()=>({render:{},cells:1,reachable:2}),validMapDraftPreview=()=>true,applyMapPreview=async()=>{};
const setStorageFailed=value=>storageFailed=value,setDraft=value=>{assert.equal(storageFailed,true);applied=value.map==='test'},requestErrorMessage=e=>e.message;
const setReading=()=>{},setPreview=()=>{},setFeedback=()=>{},setPast=()=>{},setFuture=()=>{},setCell=()=>{},setCellOriginal=()=>{};
SOURCE
(async()=>{await applyDraft({map:'test'},'edit');assert.equal(applied,true);})().catch(error=>{console.error(error);process.exitCode=1});
""".replace('SOURCE',apply)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_unsaved_cell_guards_same_tab_and_unload(self):
        source=(Path(__file__).resolve().parents[2]/'gui/MapReview.jsx').read_text()
        guard='function guardNavigation(event){'+source.split('function guardNavigation(event){',1)[1].split('\n  return <article',1)[0]
        effect='useEffect(()=>{'+source.split('const cellDirty=isMapCellDirty(cell,cellOriginal);',1)[1].split('useEffect(()=>{',1)[1].split('},[cellDirty,unsafeAutosave,saving,saveUncertain,field]);',1)[0]+'},[cellDirty,unsafeAutosave,saving,saveUncertain,field]);'
        script=r"""
const assert=require('node:assert/strict');let cellDirty=true,unsafeAutosave=false,saving=false,saveUncertain=false,message='',blocked=false,handler,removed=false,cleanup;const field=true;
const setFeedback=value=>message=value;
const window={addEventListener:(name,fn)=>{assert.equal(name,'beforeunload');handler=fn},removeEventListener:(name,fn)=>{removed=fn===handler}};
const useEffect=fn=>{cleanup=fn()};
GUARD
const event=overrides=>({button:0,preventDefault(){blocked=true},...overrides});
guardNavigation(event({}));assert.equal(blocked,true);assert.match(message,/검증/);
blocked=false;guardNavigation(event({ctrlKey:true}));assert.equal(blocked,false);
cellDirty=false;guardNavigation(event({}));assert.equal(blocked,false);
unsafeAutosave=true;guardNavigation(event({}));assert.equal(blocked,true);assert.match(message,/임시저장/);blocked=false;unsafeAutosave=false;
cellDirty=true;EFFECT
const unload={preventDefault(){blocked=true}};blocked=false;handler(unload);assert.equal(blocked,true);assert.equal(unload.returnValue,true);cleanup();assert.equal(removed,true);
cellDirty=false;unsafeAutosave=true;handler=null;EFFECT
assert.equal(typeof handler,'function');blocked=false;handler({preventDefault(){blocked=true}});assert.equal(blocked,true);cleanup();
unsafeAutosave=false;saving=true;blocked=false;guardNavigation(event({}));assert.equal(blocked,true);assert.match(message,/저장 결과/);EFFECT
assert.equal(typeof handler,'function');cleanup();saving=false;saveUncertain=true;handler=null;EFFECT
assert.equal(typeof handler,'function');cleanup();
""".replace('GUARD',guard).replace('EFFECT',effect)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_failed_preview_preserves_draft_and_history(self):
        source=(Path(__file__).resolve().parents[2]/'gui/MapReview.jsx').read_text()
        apply='async function applyDraft(next,action,stroke=null){'+source.split('async function applyDraft(next,action,stroke=null){',1)[1].split('\n  async function save(',1)[0]
        script=r"""
const assert=require('node:assert/strict');let draftState='old',history='old',feedback='',reading=false;
const window={},readRequest={current:null},importRequest={current:null},savingRef={current:false};
const cellDirty=false,draft={map:'test'},past=[],future=[],cell=null;
const requestErrorMessage=error=>error.message;
const readMap=async()=>({render:{},cells:1,reachable:2}),validMapDraftPreview=()=>true,applyMapPreview=async()=>{throw Error('미리보기 실패')};
const setReading=value=>reading=value,setFeedback=value=>feedback=value,setDraft=value=>draftState=value,setPast=value=>history=value;
const setPreview=()=>{},setFuture=()=>{},setCell=()=>{},setCellOriginal=()=>{};
SOURCE
(async()=>{await applyDraft({map:'test'},'edit');assert.equal(draftState,'old');assert.equal(history,'old');assert.equal(reading,false);assert.match(feedback,/미리보기 실패/);})().catch(error=>{console.error(error);process.exitCode=1});
""".replace('SOURCE',apply)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_cancelled_preview_does_not_apply_late_images(self):
        source=(Path(__file__).resolve().parents[2]/'gui/ui/map/block-map-review.js').read_text()
        preview='window.mapReviewApplyDraft=async(currentDraftRecord,{signal}={})=>{'+source.split('window.mapReviewApplyDraft=async(currentDraftRecord,{signal}={})=>{',1)[1].split('\n};',1)[0]+'\n};'
        preview=preview.replace('import.meta.url',"'http://localhost/'")
        script=r"""
const assert=require('node:assert/strict');let resolve,rendered=0,added=0,failRender=0;
const window={},isFieldMapReview=true,currentMapRecord={id:'test',name:'original'},currentMapLoadController=new AbortController();
const currentGameTextureSources={},currentTextureRecords={},loadedTextureImages={},currentSelectedGameKeys={};let currentFieldFrame=null;
const collectMapResourceKeys=()=>[],loadMapResourceImages=()=>new Promise(done=>resolve=done),currentSharedFieldView={addEditorTextures(){added++}},renderBlockMap=()=>{rendered++;if(failRender>0){failRender--;throw Error('draw failed')}};
SOURCE
(async()=>{const controller=new AbortController(),pending=window.mapReviewApplyDraft({id:'test',name:'new'},{signal:controller.signal});controller.abort();resolve({});await assert.rejects(pending,{name:'AbortError'});assert.equal(currentMapRecord.name,'original');assert.equal(rendered,0);assert.equal(added,0);
const normal=window.mapReviewApplyDraft({id:'test',name:'new'});resolve({});await normal;assert.equal(currentMapRecord.name,'new');assert.equal(rendered,1);assert.equal(added,1);
failRender=1;const failed=window.mapReviewApplyDraft({id:'test',name:'broken',extra:true});resolve({});await assert.rejects(failed,/draw failed/);assert.equal(currentMapRecord.name,'new');assert.equal('extra' in currentMapRecord,false);assert.equal(rendered,3);
failRender=2;const failedRestore=window.mapReviewApplyDraft({id:'test',name:'broken'});resolve({});await assert.rejects(failedRestore,/검증 전 셀 입력은 파일에 포함되지 않습니다/);assert.equal(currentMapRecord.name,'new');
await assert.rejects(window.mapReviewApplyDraft({id:'different',name:'wrong'}),/다릅니다/);assert.equal(currentMapRecord.name,'new');})().catch(error=>{console.error(error);process.exitCode=1});
""".replace('SOURCE',preview)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_import_accepts_matching_draft_and_cancels_on_exit(self):
        root=Path(__file__).resolve().parents[2]
        source=(root/'gui/MapReview.jsx').read_text()
        importer='async function importDraft(file,focused=false){'+source.split('async function importDraft(file,focused=false){',1)[1].split('\n  async function discardDraft()',1)[0]
        until=(root/'gui/managementCommand.js').read_text().split('\nexport async function managementCommand',1)[0].replace('export async function','async function')
        script=r"""
const assert=require('node:assert/strict');let resolve,applied=[],feedback='',reading=false;
const window={};
const draft={map:'test',revision:'r'},importRequest={current:null},readRequest={current:null},savingRef={current:false},restoreImportFocus={current:false};
const setReading=value=>reading=value,setImportError=value=>feedback=value,requestErrorMessage=e=>e.message,applyDraft=async(value,action)=>applied.push([value,action]);
UNTIL
SOURCE
(async()=>{
 await importDraft({text:async()=>JSON.stringify({version:1,state:{draft:{map:'test',revision:'r',cells:[]}}})});
 assert.equal(applied.length,1);assert.equal(applied[0][1],'import');assert.equal(reading,false);
 await importDraft({text:async()=>JSON.stringify({map:'other',revision:'r'})});assert.equal(applied.length,1);assert.match(feedback,/일치/);
 for(const text of ['{','null','[]']){await importDraft({text:async()=>text});assert.match(feedback,/올바른 JSON/);assert.equal(applied.length,1);}
 await importDraft({text:async()=>JSON.stringify({map:'test',revision:'r'})});assert.equal(feedback,'');assert.equal(applied.length,2);
 feedback='';const pending=importDraft({text:()=>new Promise(done=>resolve=done)});importRequest.current.abort();await pending;
 resolve(JSON.stringify({map:'test',revision:'r'}));await Promise.resolve();assert.equal(applied.length,2);assert.equal(feedback,'');assert.equal(importRequest.current,null);
})().catch(error=>{console.error(error);process.exitCode=1});
""".replace('SOURCE',importer).replace('UNTIL',until)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_import_timeout_does_not_apply_late_file(self):
        source=(Path(__file__).resolve().parents[2]/'gui/MapReview.jsx').read_text()
        importer='async function importDraft(file,focused=false){'+source.split('async function importDraft(file,focused=false){',1)[1].split('\n  async function discardDraft()',1)[0]
        script=r"""
const assert=require('node:assert/strict');let timer,resolve,applied=0,reading=false,feedback='';
const window={};
const draft={map:'test',revision:'r'},importRequest={current:null},readRequest={current:null},savingRef={current:false},restoreImportFocus={current:false};
const file={text:()=>new Promise(done=>resolve=done)},setTimeout=fn=>{timer=fn;return 1},clearTimeout=()=>{};
const setReading=value=>reading=value,setImportError=value=>feedback=value,requestErrorMessage=e=>e.message,applyDraft=async()=>applied++;
const untilAborted=(promise,signal)=>Promise.race([promise,new Promise((_,reject)=>signal.addEventListener('abort',()=>reject(new DOMException('aborted','AbortError')),{once:true}))]);
SOURCE
(async()=>{const pending=importDraft(file);timer();await pending;resolve(JSON.stringify({map:'test',revision:'r'}));await Promise.resolve();assert.equal(applied,0);assert.equal(reading,false);assert.match(feedback,/시간이 초과/);assert.equal(importRequest.current,null);})().catch(error=>{console.error(error);process.exitCode=1});
""".replace('SOURCE',importer)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_new_autosave_releases_only_successfully_replaced_draft(self):
        source=(Path(__file__).resolve().parents[2]/'gui/MapReview.jsx').read_text()
        effect='useEffect(()=>{'+source.split('const storageKey=map=>',1)[1].split('useEffect(()=>{',1)[1].split('},[draft,past,future,source]);',1)[0]+'},[draft,past,future,source]);'
        script=r"""
const assert=require('node:assert/strict');
let fail=false,stored,notice='';const draft={map:'test'},source={},past=[{}],future=[];
const discardedRecovery={current:new Set(['test','other'])},storageKey=map=>map,setStorageNotice=value=>notice=value,setStorageFailed=()=>{},requestErrorMessage=error=>error.message;
const sessionStorage={setItem(key,value){if(fail)throw Error('denied');stored=JSON.parse(value)}};
const useEffect=fn=>fn();
function run(){EFFECT}
fail=true;run();assert.equal(discardedRecovery.current.has('test'),true);assert.match(notice,/실패/);
fail=false;run();assert.equal(discardedRecovery.current.has('test'),false);assert.equal(discardedRecovery.current.has('other'),true);assert.equal(stored.state.draft.map,'test');assert.match(notice,/보관/);
""".replace('EFFECT',effect)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_saved_draft_does_not_restore_after_storage_removal_failure(self):
        source=(Path(__file__).resolve().parents[2]/'gui/MapReview.jsx').read_text()
        save='async function save(event){'+source.split('async function save(event){',1)[1].split('\n  async function inspectCell',1)[0]
        script=r"""
const assert=require('node:assert/strict');let draftState='old',notice='',feedback='',reading=false;
const window={},readRequest={current:null},importRequest={current:null};
const draft={map:'test'},preview={token:'token'},discardedRecovery={current:new Set()},savingRef={current:false},restorePreviewFocus={current:false};
const untilAborted=promise=>promise,setSaving=()=>{};
const managementCommand=async()=>({map:'test',saved:true}),mapDraftSaveReason=()=>'',storageKey=map=>map,requestErrorMessage=error=>error.message;
const sessionStorage={removeItem(){throw new Error('storage denied')}};
const setReading=value=>reading=value,setDraft=value=>draftState=value,setStorageNotice=value=>notice=value,setStorageFailed=()=>{},setSaveUncertain=()=>{},setFeedback=value=>feedback=value;
const setCell=()=>{},setSource=()=>{},setPreview=()=>{},setPast=()=>{},setFuture=()=>{};
SOURCE
(async()=>{await save();assert.equal(draftState,null);assert.equal(reading,false);assert.equal(discardedRecovery.current.has('test'),true);assert.match(notice,/자동 복원/);assert.match(feedback,/저장 완료/);})().catch(error=>{console.error(error);process.exitCode=1});
""".replace('SOURCE',save)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_discard_restores_original_even_when_storage_removal_fails(self):
        source=(Path(__file__).resolve().parents[2]/'gui/MapReview.jsx').read_text()
        discard='async function discardDraft(){'+source.split('async function discardDraft(){',1)[1].split('\n  function discardRecovery()',1)[0]
        script=r"""
const assert=require('node:assert/strict');
let applied=false,feedback='',notice='',draftState='old',reading=false;
const readRequest={current:null},importRequest={current:null},savingRef={current:false};
const draft={map:'test'},discardedRecovery={current:new Set()},window={confirm:()=>true};
const applyMapPreview=async()=>{applied=true};
const readMap=async()=>({render:{}}),storageKey=map=>map,requestErrorMessage=error=>error.message;
const sessionStorage={removeItem(){throw new Error('storage denied')}};
const setReading=value=>reading=value,setDraft=value=>draftState=value,setStorageNotice=value=>notice=value,setStorageFailed=()=>{},setSaveUncertain=()=>{},setFeedback=value=>feedback=value;
const setCell=()=>{},setSource=()=>{},setPreview=()=>{},setPast=()=>{},setFuture=()=>{},setBrush=()=>{};
SOURCE
(async()=>{await discardDraft();assert.equal(applied,true);assert.equal(draftState,null);assert.equal(reading,false);assert.equal(discardedRecovery.current.has('test'),true);assert.match(notice,/자동 복원/);assert.match(feedback,/원본/);})().catch(error=>{console.error(error);process.exitCode=1});
""".replace('SOURCE',discard)
        result=subprocess.run(['node','-e',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_invalid_map_keeps_selector_available_and_empty_catalog_is_explained(self):
        current_source=(Path(__file__).resolve().parents[2]/'gui/ui/map/block-map-review.js').read_text()
        current_selection='const currentRequestedKind='+current_source.split('const currentRequestedKind=',1)[1].split('const GROUND_CONTRAST_PREVIEW_VALUES=',1)[0]
        current_script=r"""
const assert=require('node:assert/strict'),vm=require('node:vm');
function setup(catalog){
 const selector={options:[],append(option){this.options.push(option)}};
 const button={},location={search:'?map=missing&mapKind=town',href:'http://localhost/map?map=missing&mapKind=town',assign(url){this.next=url.href}};
 const context={currentMapCatalog:catalog,currentMapCanvas:{dataset:{}},location,URL,URLSearchParams,Option:class{constructor(name,id){this.name=name;this.value=id}},document:{querySelector:query=>query==='#map-select'?selector:button}};
 return {context,selector,button,location};
}
let state=setup([{id:'town-a',name:'마을',kind:'town'}]);
assert.throws(()=>vm.runInNewContext(SOURCE,state.context),/목록에서 다른 맵/);
assert.equal(state.selector.value,'town-a');state.button.onclick();
assert.equal(new URL(state.location.next).searchParams.get('map'),'town-a');
state=setup([]);assert.throws(()=>vm.runInNewContext(SOURCE,state.context),/등록된 맵이 없습니다/);
""".replace('SOURCE',json.dumps(current_selection))
        current_result=subprocess.run(['node','-e',current_script],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_result.returncode,0,current_result.stderr)

    def test_standalone_initialization_failure_offers_reload(self):
        current_template=(Path(__file__).resolve().parents[2]/'gui/ui/map/block-map-review.html').read_text()
        current_loader=current_template.split('<script type="module">',1)[1].split('</script>',1)[0]
        current_loader=current_loader.replace("import('./block-map-review.js')", "Promise.reject(new Error('로드 실패'))")
        current_script=r"""
const assert=require('node:assert/strict');
let button, reloads=0;
const status={setAttribute:(key,value)=>{status[key]=value},after:value=>{button=value}};
const document={querySelector:()=>status,createElement:()=>({addEventListener:(name,fn)=>{buttonHandler=fn}})};
const location={reload:()=>reloads++};let buttonHandler;
LOADER
setImmediate(()=>{assert.equal(status.role,'alert');assert.match(status.textContent,/로드 실패/);assert.equal(button.textContent,'맵 검수 다시 불러오기');buttonHandler();assert.equal(reloads,1)});
""".replace('LOADER',current_loader)
        current_result=subprocess.run(['node','-e',current_script],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_result.returncode,0,current_result.stderr)

    def test_standalone_slow_load_notice_clears_after_success(self):
        current_template=(Path(__file__).resolve().parents[2]/'gui/ui/map/block-map-review.html').read_text()
        current_loader=current_template.split('<script type="module">',1)[1].split('</script>',1)[0]
        current_loader=current_loader.replace("import('./block-map-review.js')", 'pending')
        current_script=r"""
const assert=require('node:assert/strict');let timer,resolve,notice,focused=false,reloads=0;
const pending=new Promise(done=>resolve=done);
const status={after:node=>notice=node,focus:()=>focused=true};
const document={activeElement:null,querySelector:()=>status,createElement:()=>({children:[],setAttribute(){},append(...nodes){this.children.push(...nodes)},addEventListener(name,fn){this.click=fn},contains(node){return this.children.includes(node)},remove(){this.removed=true}})};
const setTimeout=fn=>{timer=fn;return 1},clearTimeout=()=>{},location={reload:()=>reloads++};
LOADER
timer();assert.match(notice.children[0].textContent,/오래 걸리고/);
notice.children[1].click();assert.equal(reloads,1);
document.activeElement=notice.children[1];resolve();
setImmediate(()=>{assert.equal(notice.removed,true);assert.equal(focused,true)});
""".replace('LOADER',current_loader)
        current_result=subprocess.run(['node','-e',current_script],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_result.returncode,0,current_result.stderr)

    def test_standalone_slow_load_failure_announces_before_focus(self):
        current_template=(Path(__file__).resolve().parents[2]/'gui/ui/map/block-map-review.html').read_text()
        current_loader=current_template.split('<script type="module">',1)[1].split('</script>',1)[0]
        current_loader=current_loader.replace("import('./block-map-review.js')", 'pending')
        current_script=r"""
const assert=require('node:assert/strict');let timer,reject,notice,focusText;
const pending=new Promise((_,fail)=>reject=fail);
const status={setAttribute(key,value){this[key]=value},after(node){if(!notice)notice=node},focus(){focusText=this.textContent}};
const document={activeElement:null,querySelector:()=>status,createElement:()=>({children:[],setAttribute(){},append(...nodes){this.children.push(...nodes)},addEventListener(){},contains(node){return this.children.includes(node)},remove(){}})};
const setTimeout=fn=>{timer=fn;return 1},clearTimeout=()=>{},location={reload(){}};
LOADER
timer();document.activeElement=notice.children[1];reject(new Error('서버 연결 실패'));
setImmediate(()=>{assert.equal(status.role,'alert');assert.match(focusText,/서버 연결 실패/)});
""".replace('LOADER',current_loader)
        current_result=subprocess.run(['node','-e',current_script],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_result.returncode,0,current_result.stderr)

    def test_source_list_preserves_nodes_until_sources_change(self):
        current_source_path=Path(__file__).resolve().parents[2]/'gui/ui/map/block-map-review.js'
        current_render_source=current_source_path.read_text().split('let currentAppliedSourceSignature=',1)[1].split('\nrenderAppliedTileSourceList();',1)[0]
        current_render_source=('let currentAppliedSourceSignature='+current_render_source).replace('import.meta.url',json.dumps('http://localhost/'))
        current_script_source=r"""
const assert=require('node:assert/strict');
const isFieldMapReview=false,isCharacterReviewPage=true;
const groundTextureNames={paving:'first'};
const currentMapRecord={terrainCodes:{p:'paving'},guardCenters:[]};
const currentSafeVisualRecords={};
const currentTextureRecords={first:{path:'first.png',source:'/tiles/first.png',source_size:[128,128]},second:{path:'second.png',source:'/tiles/second.png',source_size:[128,128]}};
const currentAppliedGameKeys={};
let currentReplacementCount=0;
function createTestElement(){return {children:[],append(...currentChildNodes){this.children.push(...currentChildNodes);},setAttribute(){},addEventListener(){},replaceChildren(){this.children=[];},get childElementCount(){return this.children.length;}};}
const currentSourceList=createTestElement(),currentOtherLists={};
currentSourceList.replaceChildren=()=>{currentReplacementCount++;currentSourceList.children=[];};
const document={querySelector:(currentSelectorName)=>currentSelectorName==='#applied-tile-list'?currentSourceList:(currentOtherLists[currentSelectorName]??=createTestElement()),createElement:createTestElement};
SOURCE
renderAppliedTileSourceList();
const currentOriginalNode=currentSourceList.children[0];
currentOriginalNode.expanded=true;
renderAppliedTileSourceList();
assert.equal(currentReplacementCount,1);
assert.equal(currentSourceList.children[0],currentOriginalNode);
assert.equal(currentSourceList.children[0].expanded,true);
groundTextureNames.paving='second';renderAppliedTileSourceList();
assert.equal(currentReplacementCount,2);
assert.notEqual(currentSourceList.children[0],currentOriginalNode);
currentTextureRecords.second.path='updated.png';renderAppliedTileSourceList();
assert.equal(currentReplacementCount,3);
assert.equal(currentSourceList.children[1].children[1].children[0].children[0].children[0].href,'http://localhost/updated.png');
""".replace('SOURCE',current_render_source)
        current_test_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)

    def test_initialization_failure_and_early_exit_destroy_renderer_once(self):
        current_adapter_path=Path(__file__).resolve().parents[2]/'gui/ui/map/field-map-view.js'
        current_adapter_source='\n'.join(current_source_line for current_source_line in current_adapter_path.read_text().splitlines() if not current_source_line.startswith('import '))
        current_adapter_source=current_adapter_source.replace('export async function','async function').replace('export function','function')
        current_script_source=r"""
const assert=require('node:assert/strict');
const TERRAIN_DEPTH={actor:1,overlay:2},GAME_INTERNAL_RESOLUTION_SCALE=2;
const currentEventHandlers=new Map();
const window={addEventListener:(name,callback)=>currentEventHandlers.set(name,callback),removeEventListener:name=>currentEventHandlers.delete(name)};
let currentDestroyCount=0,currentBootCallback,currentFailAtlas=false;
const Phaser={WEBGL:1,Scale:{NONE:0},Game:class{
 constructor(settings){this.scale={};currentBootCallback=()=>settings.scene.create.call({textures:{addImage:()=>({add(){}}),exists:()=>false}});}
 destroy(){currentDestroyCount++;}
}};
const collectTerrainTextureSources=()=>({});
const createTerrainAtlas=()=>{if(currentFailAtlas)throw Error('atlas failure');};
ADAPTER_SOURCE
const currentCanvasElement={clientWidth:100,clientHeight:100,parentElement:{getBoundingClientRect:()=>({width:100,height:100})},style:{}};
const currentCharacterRecord={frame:{rect:{x:0,y:0,width:1,height:1}}};
const createTestReview=()=>createSharedFieldReview(currentCanvasElement,{}, {},currentCharacterRecord,{}, {},{});
(async()=>{
 currentFailAtlas=true;
 let currentPendingReview=createTestReview();currentBootCallback();
 await assert.rejects(currentPendingReview,/atlas failure/);
 assert.equal(currentDestroyCount,1);assert.equal(currentEventHandlers.size,0);
 currentFailAtlas=false;
 currentPendingReview=createTestReview();
 currentEventHandlers.get('pagehide')();
 await assert.rejects(currentPendingReview,/닫혔습니다/);
 assert.equal(currentDestroyCount,2);assert.equal(currentEventHandlers.size,0);
 currentPendingReview=createTestReview();currentBootCallback();
 const currentReadyReview=await currentPendingReview;
 currentReadyReview.destroy();currentReadyReview.destroy();
 assert.throws(()=>currentReadyReview.render({}, {}, {}),/맵 검수 화면이 닫혔습니다/);
 assert.throws(()=>currentReadyReview.renderTown({}, {}, ()=>({})),/맵 검수 화면이 닫혔습니다/);
 assert.equal(currentDestroyCount,3);assert.equal(currentEventHandlers.size,0);
})().catch(error=>{console.error(error);process.exitCode=1;});
""".replace('ADAPTER_SOURCE',current_adapter_source)
        current_test_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)

    def test_texture_progress_preserves_failure_during_other_completions(self):
        current_loader_path = (Path(__file__).resolve().parents[2] / 'gui/ui/map/vendor/field-renderer/town-renderer.mjs').resolve()
        current_loader_source = 'var MAP_RESOURCE_CONCURRENCY = ' + current_loader_path.read_text().split('var MAP_RESOURCE_CONCURRENCY = ', 1)[1].split('function collectMapResourceKeys', 1)[0]
        current_script_source = r"""
const assert=require('node:assert/strict');
SOURCE
(async()=>{
 const currentProgressRecords=[],currentPendingLoads={};
 const currentResourceRecords=[{key:'a',url:'a.png'},{key:'b',url:'b.png'}];
 const currentLoadPromise=loadMapResourceImages(currentResourceRecords,{onProgress:currentProgressRecord=>currentProgressRecords.push(currentProgressRecord),loadImage:(currentImageUrl)=>new Promise((resolveImage,rejectImage)=>{currentPendingLoads[currentImageUrl]={resolveImage,rejectImage};})});
 const currentRejectedLoad=assert.rejects(currentLoadPromise,/타일 로드 실패/);
 currentPendingLoads['a.png'].rejectImage(Error('타일 로드 실패'));
 await currentRejectedLoad;
 currentPendingLoads['b.png'].resolveImage({});
 await new Promise(currentResolve=>setImmediate(currentResolve));
 assert.deepEqual(currentProgressRecords,[{completed:0,total:2}]);
 const currentSuccessProgress=[];
 const currentImages=await loadMapResourceImages(currentResourceRecords,{onProgress:currentProgressRecord=>currentSuccessProgress.push(currentProgressRecord),loadImage:async currentImageUrl=>currentImageUrl});
 assert.deepEqual(currentImages,{a:'a.png',b:'b.png'});
 assert.deepEqual(currentSuccessProgress,[{completed:0,total:2},{completed:1,total:2},{completed:2,total:2}]);
})().catch(currentError=>{console.error(currentError);process.exitCode=1;});
""".replace('SOURCE', current_loader_source)
        current_test_result = subprocess.run(['node', '-e', current_script_source], capture_output=True, text=True, timeout=10)
        self.assertEqual(current_test_result.returncode, 0, current_test_result.stderr)

    def test_resize_uses_parent_bounds_and_rejects_zero_area(self):
        current_adapter_source=(Path(__file__).resolve().parents[2]/'gui/ui/map/field-map-view.js').read_text()
        current_resize_source=current_adapter_source.split('function readReviewViewportSize',1)[1].split('/** 화면 컨트롤',1)[0]
        current_script_source=r"""
const assert=require('node:assert/strict');
const GAME_INTERNAL_RESOLUTION_SCALE=2;
SOURCE
let currentParentBounds={width:859,height:644.25};
const currentCanvasElement={clientWidth:287,clientHeight:0,style:{},parentElement:{getBoundingClientRect:()=>currentParentBounds}};
let currentResizeCalls=0;
const currentFieldGame={scale:{width:574,height:0,resize(width,height){currentResizeCalls++;this.width=width;this.height=height;currentCanvasElement.style.height='0px';}}};
resizeReviewViewport(currentFieldGame,currentCanvasElement);
assert.equal(currentFieldGame.scale.width,1718);
assert.equal(currentFieldGame.scale.height,1289);
assert.equal(currentCanvasElement.style.height,'100%');
resizeReviewViewport(currentFieldGame,currentCanvasElement);
assert.equal(currentResizeCalls,1);
currentParentBounds={width:390,height:292.5};
resizeReviewViewport(currentFieldGame,currentCanvasElement);
assert.equal(currentFieldGame.scale.height,585);
currentParentBounds={width:390,height:0};
assert.throws(()=>resizeReviewViewport(currentFieldGame,currentCanvasElement),/크기가 유효하지/);
assert.equal(currentResizeCalls,2);
""".replace('SOURCE','function readReviewViewportSize'+current_resize_source)
        current_test_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)

    def test_container_resize_batches_frames_and_cleans_up(self):
        current_adapter_source=(Path(__file__).resolve().parents[2]/'gui/ui/map/block-map-review.js').read_text()
        current_observer_source=current_adapter_source.split('let currentResizeFrameRequest=',1)[1].split('currentMapCanvas.onclick=',1)[0]
        current_script_source=r"""
const assert=require('node:assert/strict');
let currentResizeCallback,currentFrameCallback,currentExitCallback,currentRenderCount=0,currentCancelCount=0,currentDisconnectCount=0;
let currentViewportBounds={width:800,height:600},currentRenderFailure=false;
const currentStatusElement={textContent:''};
const currentMapCanvas={parentElement:{getBoundingClientRect:()=>currentViewportBounds}};
const document={querySelector:()=>currentStatusElement};
const window={addEventListener:(name,callback)=>{assert.equal(name,'pagehide');currentExitCallback=callback;}};
const requestAnimationFrame=callback=>{currentFrameCallback=callback;return 1;};
const cancelAnimationFrame=()=>currentCancelCount++;
class ResizeObserver{constructor(callback){currentResizeCallback=callback;}observe(element){assert.equal(element,currentMapCanvas.parentElement);}disconnect(){currentDisconnectCount++;}}
function renderBlockMap(){if(currentRenderFailure)throw Error('GPU failure');currentRenderCount++;}
SOURCE
currentResizeCallback();const currentFirstCallback=currentFrameCallback;currentResizeCallback();
assert.equal(currentFrameCallback,currentFirstCallback);currentFrameCallback();assert.equal(currentRenderCount,1);
currentViewportBounds={width:0,height:0};currentResizeCallback();currentFrameCallback();assert.equal(currentRenderCount,1);
currentViewportBounds={width:400,height:300};currentResizeCallback();currentFrameCallback();assert.equal(currentRenderCount,2);
currentRenderFailure=true;currentResizeCallback();currentFrameCallback();assert.match(currentStatusElement.textContent,/맵 크기 변경 실패: GPU failure/);
currentResizeCallback();currentExitCallback();assert.equal(currentCancelCount,1);assert.equal(currentDisconnectCount,1);
currentFrameCallback=null;currentResizeCallback();assert.equal(currentFrameCallback,null);
""".replace('SOURCE','let currentResizeFrameRequest='+current_observer_source)
        current_test_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)

    def test_character_keyboard_movement_preserves_camera_and_rejects_blocked_cells(self):
        current_source_text=(Path(__file__).resolve().parents[2]/'gui/ui/map/block-map-review.js').read_text()
        current_move_source='function placeReviewCharacterCell'+current_source_text.split('function placeReviewCharacterCell',1)[1].split('currentMapCanvas.onclick=',1)[0]
        current_key_source='currentMapCanvas.onkeydown='+current_source_text.split('currentMapCanvas.onkeydown=',1)[1].split("currentMapCanvas.addEventListener('wheel'",1)[0]
        current_offsets_source='const CHARACTER_CELL_KEY_OFFSETS='+current_source_text.split('const CHARACTER_CELL_KEY_OFFSETS=',1)[1].split(';',1)[0]+';'
        current_script_source=r"""
const assert=require('node:assert/strict');
const isCharacterReviewPage=false;
const canTraverseBridgeEdge=()=>true;
const currentMapRecord={columns:3,rows:3},currentBlockedCells=new Set(['2,1']),currentMapCanvas={};
let currentCharacterCell={column:1,row:1},currentOffsetX=0,currentOffsetY=0,currentRenderCount=0;
const MAP_KEYBOARD_PAN_DISTANCE=48,MAP_ZOOM_FACTOR=1.25,currentStatusElement={textContent:''};
global.document={querySelector:()=>currentStatusElement};
function renderBlockMap(){currentRenderCount++;} function changeMapZoom(){}
SOURCE
function pressReviewKey(currentKeyName,currentShiftEnabled){currentMapCanvas.onkeydown({key:currentKeyName,shiftKey:currentShiftEnabled,preventDefault(){}});}
pressReviewKey('ArrowRight',true);assert.deepEqual(currentCharacterCell,{column:1,row:1});assert.match(currentStatusElement.textContent,/이동할 수 없는/);
pressReviewKey('ArrowLeft',true);assert.deepEqual(currentCharacterCell,{column:0,row:1});assert.equal(currentOffsetX,0);
pressReviewKey('ArrowLeft',true);assert.deepEqual(currentCharacterCell,{column:0,row:1});
pressReviewKey('ArrowUp',true);assert.deepEqual(currentCharacterCell,{column:0,row:0});
pressReviewKey('ArrowRight',false);assert.equal(currentOffsetX,-48);assert.deepEqual(currentCharacterCell,{column:0,row:0});
assert.equal(placeReviewCharacterCell(1.5,0),false);assert.equal(placeReviewCharacterCell(1,2),true);
assert.equal(currentRenderCount,4);
""".replace('SOURCE',current_offsets_source+current_move_source+current_key_source)
        current_test_result=subprocess.run(['node','-e',current_script_source],capture_output=True,text=True,timeout=10)
        self.assertEqual(current_test_result.returncode,0,current_test_result.stderr)

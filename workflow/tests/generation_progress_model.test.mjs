import assert from 'node:assert/strict';
import {createRequire,Module} from 'node:module';
import {fileURLToPath} from 'node:url';
import {observedGenerationProgress,validInferenceCompletion,generationProgressSummary} from '../../gui/generationProgressModel.mjs';
assert.equal(generationProgressSummary({stage:'reference_vae_encode',step:0,total:8}),'참조 영상 인코딩');
assert.equal(generationProgressSummary({stage:'inference',step:3,total:8}),'단계 3/8');
assert.equal(generationProgressSummary({stage:'saving',step:8,total:8},'minimax-h3-ref2va'),'결과 저장');
assert.equal(generationProgressSummary({stage:'saving',step:8,total:8},'other'),'단계 8/8');

const guiRequire=createRequire(new URL('../../gui/package.json',import.meta.url));
const React=guiRequire('react'),{renderToStaticMarkup}=guiRequire('react-dom/server');
const output=guiRequire('esbuild').buildSync({entryPoints:[fileURLToPath(new URL('../../gui/GenerationProgress.jsx',import.meta.url))],bundle:true,platform:'node',format:'cjs',external:['react','react-dom'],write:false}).outputFiles[0].text;
const renderedModule=new Module(fileURLToPath(new URL('../../gui/progress-render-check.cjs',import.meta.url)));
renderedModule.filename=fileURLToPath(new URL('../../gui/progress-render-check.cjs',import.meta.url));
renderedModule.paths=Module._nodeModulePaths(fileURLToPath(new URL('../../gui/',import.meta.url)));
renderedModule._compile(output,renderedModule.filename);
const renderStage=(stage,service)=>renderToStaticMarkup(React.createElement(renderedModule.exports.default,{service,job:{status:'running',worker_progress:{stage,step:0,total:8,updated_at:'2026-11-25T00:00:00Z'}}}));
for(const stage of ['prepare','load','reference_prepare','reference_text_encode','reference_vae_encode','saving']){
  const html=renderStage(stage,'minimax-h3-ref2va');
  assert.match(html,/이 단계의 진행률은 제공되지 않습니다/);
  assert.doesNotMatch(html,/<progress|0\/8/);
}
assert.match(renderStage('inference','minimax-h3-ref2va'),/<progress/);
assert.match(renderStage('saving','other'),/<progress/);
const worker={stage:'inference',step:3,total:20,updated_at:'2026-11-22T14:45:00+09:00',scope:'추론 단계'};
assert.deepEqual(observedGenerationProgress({worker_progress:worker}),{stage:'inference',step:3,total:20,updatedAt:worker.updated_at,scope:'추론 단계'});
assert.equal(observedGenerationProgress({worker_progress:{...worker,step:21}}),null);
assert.equal(observedGenerationProgress({worker_progress:null}),null);
const event={'generation.stage':'inference','generation.step':4,'generation.step.total':20,'generation.updated_at':worker.updated_at};
assert.equal(observedGenerationProgress({progress_event:event,worker_progress:worker}).step,4);
assert.equal(observedGenerationProgress({progress_event:{...event,'generation.step':-1},worker_progress:worker}).step,3);

assert.equal(observedGenerationProgress({progress_event:event}).estimate,null);
const estimated={...event,'generation.estimate.basis':'추론 단계 표본','generation.estimate.scope':'추론 단계','generation.estimate.sample_count':2,'generation.estimate.remaining_seconds':120,'generation.estimate.completion_time':'2026-11-22T14:47:00+09:00'};
assert.equal(observedGenerationProgress({progress_event:estimated}).estimate.samples,2);
assert.equal(observedGenerationProgress({progress_event:{...estimated,'generation.estimate.sample_count':-1}}).estimate,null);

assert.equal(validInferenceCompletion('2026-11-22T14:47:00+09:00'),true);
assert.equal(validInferenceCompletion('2026-11-22T05:47:00Z'),true);
assert.equal(validInferenceCompletion('2026-11-22T14:47:00'),false);
assert.equal(validInferenceCompletion('not-a-date'),false);
assert.equal(validInferenceCompletion(null),false);
assert.equal(observedGenerationProgress({progress_event:{...estimated,'generation.estimate.scope':'  '}}).estimate,null);
assert.equal(observedGenerationProgress({progress_event:{...estimated,'generation.estimate.sample_count':Number.MAX_SAFE_INTEGER+1}}).estimate,null);

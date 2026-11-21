import {test} from 'node:test';
import assert from 'node:assert/strict';
import {generationResumeCommand} from '../../gui/generationResumeCommand.mjs';

test('서비스가 검토 지문을 받는 게이트웨이 명령으로 재개한다', () => {
  for (const service of ['kimodo', 'dwpose', 'wan22-animate2', 'wan22-vace', 'wan22-fun-control', 'flux-image', 'flux-character', 'flux-mannequin', 'flux-billboard', 'flux-prop', 'flux-vegetation', 'flux-building', 'flux-seamless'])
    assert.equal(generationResumeCommand(service), 'resume-reviewed', service);
  for (const service of ['music-heartmula', 'sfx-dasheng-audiogen', 'prompt-translation'])
    assert.equal(generationResumeCommand(service), 'resume', service);
  assert.equal(generationResumeCommand('flux-expression'), null);
  assert.equal(generationResumeCommand('unknown'), null);
});

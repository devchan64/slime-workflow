import {test} from 'node:test';
import assert from 'node:assert/strict';
import {videoLookupSuggestion} from '../../gui/videoLookupSuggestion.mjs';
const id='2026-11-21_20-42-44-44a7d6ee';
const command=`조회:\n\n\`\`\`bash\n/runtime/.venv/bin/python /control/management-status.py video-source-status '{"service":"wan22-fun-control","job_id":"${id}"}'\n\`\`\``;
test('accepts only a supported lookup for the user-requested ID',()=>{
  assert.deepEqual(videoLookupSuggestion(command,`작업 ${id} 확인`),{service:'wan22-fun-control',job_id:id});
  assert.equal(videoLookupSuggestion(command,'다른 작업'),null);
  assert.equal(videoLookupSuggestion(command.replace('wan22-fun-control','other'),'작업 '+id),null);
  assert.equal(videoLookupSuggestion(command+'\n추가 명령',id),null);
  assert.equal(videoLookupSuggestion(command.replace('video-source-status','video-cancel'),id),null);
});

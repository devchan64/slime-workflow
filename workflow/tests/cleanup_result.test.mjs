import test from "node:test";
import assert from "node:assert/strict";
import {validCleanupResult} from "../../gui/formatCleanupResult.mjs";

test("삭제 결과는 확인된 상태와 유효한 건수·용량이 있어야 한다",()=>{
  const valid={status:"cleared",deleted_jobs:1,deleted_bytes:0};
  assert.equal(validCleanupResult(valid,true),true);
  for(const invalid of [null,{}, {...valid,status:"failed"}, {...valid,deleted_jobs:0},
    {...valid,deleted_bytes:-1}, {...valid,deleted_bytes:NaN}, {...valid,skipped_jobs:{}}])
    assert.equal(validCleanupResult(invalid,true),false);
  assert.equal(validCleanupResult({...valid,deleted_jobs:0},false),true);
});

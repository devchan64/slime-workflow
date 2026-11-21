import test from "node:test";
import assert from "node:assert/strict";
import {requestErrorMessage} from "../../gui/requestError.mjs";

test("network errors receive a useful message while service errors stay specific", () => {
  assert.match(requestErrorMessage(new TypeError("Failed to fetch")), /서버에 연결할 수 없습니다/);
  assert.equal(requestErrorMessage(new Error("저장된 입력이 없습니다.")), "저장된 입력이 없습니다.");
  assert.match(requestErrorMessage(null), /다시 시도/);
});

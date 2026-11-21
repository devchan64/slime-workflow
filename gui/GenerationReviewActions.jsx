import React, {useId} from "react";

export default function GenerationReviewActions({busy=false,onCancel,onConfirm,disabledReason=""}) {
  const reasonId=useId();
  return <div className="choice-buttons" aria-label="생성 요청 확인 행동">
    {disabledReason && <p id={reasonId}>{disabledReason}</p>}
    <button type="button" disabled={busy} onClick={onCancel}>입력 수정</button>
    <button type="button" disabled={busy || Boolean(disabledReason)} aria-describedby={disabledReason ? reasonId : undefined} onClick={onConfirm}>{busy ? "접수 중…" : "확인 후 대기열에 추가"}</button>
  </div>;
}

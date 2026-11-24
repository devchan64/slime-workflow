import React, {useId} from "react";

export default function GenerationReviewActions({busy=false,onCancel,onConfirm,disabledReason="",confirmLabel="확인 후 대기열에 추가"}) {
  const reasonId=useId();
  const busyId=reasonId+"-busy";
  const descriptions=[disabledReason && reasonId,busy && busyId].filter(Boolean).join(" ") || undefined;
  return <div className="choice-buttons generation-review-actions" role="group" aria-label="생성 요청 확인 행동">
    {disabledReason && <p id={reasonId}>{disabledReason}</p>}
    {busy && <p id={busyId} role="status">요청을 접수하고 있습니다. 잠시 기다려 주세요.</p>}
    <button type="button" aria-disabled={busy} aria-describedby={busy ? busyId : undefined} onClick={()=>{if(!busy)onCancel?.();}}>입력 수정</button>
    <button type="button" aria-disabled={busy || Boolean(disabledReason)} aria-describedby={descriptions} onClick={()=>{if(!busy && !disabledReason)onConfirm?.();}}>{busy ? "접수 중…" : confirmLabel}</button>
  </div>;
}

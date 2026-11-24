import React, {useEffect,useRef,useState} from "react";
import {untilAborted} from "./managementCommand.js";
import {verifyPriorityTarget} from "./verifyPriorityTarget.mjs";

export default function QueuePriority({step, call}) {
  const service = step.generator;
  const id = step.source_job_id;
  if (step.state !== "submitting" || step.source_state !== "queued" || !id) return "—";

  async function verifyTarget() {
    const receipt = await call("service-receipt", {service, request_id:step.request_id});
    if (receipt.state !== "accepted" || receipt.service !== service ||
        receipt.request_id !== step.request_id || receipt.job_id !== id) {
      throw new Error("접수된 작업이 변경되었습니다. 대기열을 다시 조회하세요.");
    }
  }

  return <JobPriority key={service+"/"+id} service={service} id={id} call={call} verifyTarget={verifyTarget}/>;
}

export function JobPriority({service,id,call,verifyTarget,inline=false,disabled=false,onInteractionChange}) {
  const [review, setReview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const previewRequest=useRef(null);
  const triggerRef=useRef(null),reviewRef=useRef(null),restoreFocus=useRef(false);
  useEffect(()=>()=>previewRequest.current?.abort(),[]);
  useEffect(()=>{onInteractionChange?.(busy || Boolean(review));return ()=>onInteractionChange?.(false);},[busy,review,onInteractionChange]);
  useEffect(()=>{if(!busy && restoreFocus.current){restoreFocus.current=false;if(document.activeElement===document.body || document.activeElement===triggerRef.current)(review ? reviewRef : triggerRef).current?.focus();}},[busy,review]);
  function startPreview(){restoreFocus.current=document.activeElement===triggerRef.current;run(preview);}
  function cancelReview(){restoreFocus.current=Boolean(reviewRef.current?.contains(document.activeElement));setReview(null);}
  async function preview() {
    const controller=new AbortController();previewRequest.current=controller;let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try {
    await untilAborted(Promise.resolve().then(()=>verifyTarget?.()),controller.signal);
    const ticket = await untilAborted(call("priority-preview", {service,id}),controller.signal);
    if (ticket.service !== service || ticket.job_id !== id || !/^[a-f0-9]{64}$/.test(ticket.ticket_revision) ||
        !Number.isInteger(ticket.queue_position) || !Number.isInteger(ticket.queue_count) ||
        ticket.queue_position < 1 || ticket.queue_position > ticket.queue_count) {
      throw new Error("대기 티켓을 확인할 수 없습니다.");
    }
    const bytes = new TextEncoder().encode([service,id,ticket.ticket_revision].join("\0"));
    const digest = new Uint8Array(await untilAborted(crypto.subtle.digest("SHA-256",bytes),controller.signal));
    const request_id = "priority_" + Array.from(digest, n => n.toString(16).padStart(2,"0")).join("");
    const receipt = await untilAborted(call("priority-receipt",{request_id}),controller.signal);
    if (receipt.state !== "not_found") {
      if (!["completed","unknown"].includes(receipt.state) || receipt.request_id!==request_id ||
          receipt.service!==service || receipt.job_id!==id || receipt.ticket_revision!==ticket.ticket_revision)
        throw new Error("기존 접수 기록이 검토 대상과 일치하지 않습니다.");
      setNotice("기존 접수 상태 " + receipt.state + " · " + request_id);
      return;
    }
    setReview({ticket, payload:{service,id,request_id,ticket_revision:ticket.ticket_revision}});
    } catch(error){if(timedOut)throw new Error("우선 실행 검토 조회 시간이 초과됐습니다. 다시 확인하세요.");throw error;}
    finally{clearTimeout(timer);if(previewRequest.current===controller)previewRequest.current=null;}
  }

  async function submit() {
    const {payload} = review;
    const controller=new AbortController();previewRequest.current=controller;
    try {
      await verifyPriorityTarget(verifyTarget,controller);
    } finally {if(previewRequest.current===controller)previewRequest.current=null;}
    setReview(null);
    try {
      const receipt = await call("priority-submit",payload);
      if (receipt.state !== "completed" || receipt.service !== service || receipt.job_id !== id ||
          receipt.request_id !== payload.request_id || receipt.ticket_revision !== payload.ticket_revision) {
        throw new Error();
      }
      setNotice("순서 변경 접수 완료 · " + payload.request_id);
    } catch {
      setNotice("접수 결과 확인 필요 · " + payload.request_id);
    }
  }

  async function run(action) {
    setBusy(true);
    setNotice("");
    try { await action(); }
    catch (error) { setNotice(error.message); }
    finally { setBusy(false); }
  }

  if(inline) return <>
    <button ref={triggerRef} className="history-action-priority" type="button" disabled={disabled || busy || Boolean(review)} onClick={startPreview}>우선 실행 검토</button>
    {review && <section ref={reviewRef} tabIndex={-1} aria-label="우선 실행 검토" className="history-action-detail"><p>{id} · 관측 순번 {review.ticket.queue_position} / {review.ticket.queue_count} · 실행기 신원 {review.ticket.executor_identity === "verified" ? "확인" : "미확인"}</p>
      <button type="button" disabled={disabled || busy} onClick={()=>run(submit)}>대기열 맨 앞으로 이동</button>
      <button type="button" disabled={disabled || busy} onClick={cancelReview}>취소</button></section>}
    {(busy || notice) && <p className="history-action-detail" role="status">{busy ? "우선 실행 요청을 확인하고 있습니다." : notice}</p>}
  </>;

  return <>{review ? <section ref={reviewRef} tabIndex={-1} aria-label="우선 실행 검토">
    <p>{id} · 관측 순번 {review.ticket.queue_position} / {review.ticket.queue_count} · 실행기 신원 {review.ticket.executor_identity === "verified" ? "확인" : "미확인"}</p>
    <button type="button" disabled={busy} onClick={() => run(submit)}>대기열 맨 앞으로 이동</button>
    <button type="button" disabled={busy} onClick={cancelReview}>취소</button>
  </section> : <button ref={triggerRef} type="button" disabled={busy} onClick={startPreview}>우선 실행 검토</button>}
    <p role="status">{busy ? "우선 실행 요청을 확인하고 있습니다." : notice}</p>
  </>;
}

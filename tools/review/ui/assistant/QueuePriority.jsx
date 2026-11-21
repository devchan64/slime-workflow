import React, {useState} from "react";

export default function QueuePriority({step, call}) {
  const [review, setReview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
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

  async function preview() {
    await verifyTarget();
    const ticket = await call("priority-preview", {service,id});
    if (ticket.service !== service || ticket.job_id !== id || !/^[a-f0-9]{64}$/.test(ticket.ticket_revision) ||
        !Number.isInteger(ticket.queue_position) || !Number.isInteger(ticket.queue_count) ||
        ticket.queue_position < 1 || ticket.queue_position > ticket.queue_count) {
      throw new Error("대기 티켓을 확인할 수 없습니다.");
    }
    const bytes = new TextEncoder().encode([service,id,ticket.ticket_revision].join("\0"));
    const digest = new Uint8Array(await crypto.subtle.digest("SHA-256",bytes));
    const request_id = "priority_" + Array.from(digest, n => n.toString(16).padStart(2,"0")).join("");
    const receipt = await call("priority-receipt",{request_id});
    if (receipt.state !== "not_found") {
      setNotice("기존 접수 상태 " + receipt.state + " · " + request_id);
      return;
    }
    setReview({ticket, payload:{service,id,request_id,ticket_revision:ticket.ticket_revision}});
  }

  async function submit() {
    const {payload} = review;
    setReview(null);
    await verifyTarget();
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

  return <>{review ? <>
    <p>{id} · 관측 순번 {review.ticket.queue_position} / {review.ticket.queue_count} · 실행기 신원 {review.ticket.executor_identity === "verified" ? "확인" : "미확인"}</p>
    <button disabled={busy} onClick={() => run(submit)}>대기열 맨 앞으로 이동</button>
    <button disabled={busy} onClick={() => setReview(null)}>취소</button>
  </> : <button disabled={busy} onClick={() => run(preview)}>우선 실행 검토</button>}
    <p role="status">{notice}</p>
  </>;
}

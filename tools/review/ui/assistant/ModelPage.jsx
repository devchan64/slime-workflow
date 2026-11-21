import DownloadProgress from "./DownloadProgress.jsx";
import React, {useEffect, useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ModelReadiness from "./ModelReadiness.jsx";

const buildLabels = {
  idle:"빌드 이력 없음", queued:"GPU 대기 중", running:"빌드 중", completed:"최근 빌드 완료",
  failed:"빌드 실패", cancelled:"취소됨", checking:"GPU 환경 확인 중", ready:"빌드 준비 완료",
  rebuild_required:"현재 환경에 맞는 빌드 필요", unavailable:"빌드 유효성 확인 실패",
};

function KimodoBuild() {
  const [record, setRecord] = useState(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  useEffect(() => {
    if (pending) return;
    let active = true, timer;
    async function poll() {
      try {
        const next = await managementCommand("kimodo", "migraphx-build-status");
        if (active) setRecord(next);
      } catch (problem) {
        if (active) setRecord({status:"unavailable", error:problem.message});
      } finally {
        if (active) timer = setTimeout(poll, 5000);
      }
    }
    poll();
    return () => {active = false; clearTimeout(timer);};
  }, [pending]);
  async function start() {
    setPending(true);
    setError("");
    setRecord(null);
    try {
      setRecord(await managementCommand("kimodo", "migraphx-build"));
    } catch (problem) {
      setError(problem.message);
    } finally {
      setPending(false);
    }
  }
  return <section><h2>DWPose MIGraphX 빌드</h2>
    <p role="status">{pending ? "빌드 접수 중" : buildLabels[record?.status] || record?.status || "빌드 상태 확인 중"}
      {record?.id && <> · 작업 <code>{record.id}</code></>}</p>
    {record?.status === "failed" && record.id && <p>상세 로그 <code>.tmp/test/kimodo-migraphx-build/{record.id}/worker.log</code></p>}
    {(error || record?.error) && <p role="alert">{error || record.error}</p>}
    <button disabled={pending || record?.status !== "rebuild_required"} onClick={start}>GPU 대기열에 빌드 등록</button>
  </section>;
}

export default function ModelPage() {
  const [models, setModels] = useState([]);
  const [service, select] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    async function load() {
      try {
        const response = await fetch("/management/assistant/model-services");
        if (!response.ok) throw new Error("모델 목록을 조회할 수 없습니다.");
        const items = await response.json();
        setModels(items);
        select(items[0]?.id || "");
      } catch (problem) {setError(problem.message);}
    }
    load();
  }, []);
  return <article><h1>모델 상태와 파일</h1>
    <a href="/management/assistant/">헤르메스 대화로 이동</a>
    {error && <p role="alert">{error}</p>}
    <label>모델 <select value={service} onChange={event => select(event.target.value)}>
      {models.map(model => <option key={model.id} value={model.id}>{model.label}</option>)}
    </select></label>
    {service && <ModelReadiness key={service} service={service}/>}
    {service && <DownloadProgress key={"progress-" + service} service={service}/>}
    {service === "kimodo" && <KimodoBuild/>}
  </article>;
}

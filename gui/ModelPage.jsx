import DownloadProgress from "./DownloadProgress.jsx";
import React, {useEffect, useState} from "react";
import {managementCommand} from "./managementCommand.js";
import ModelReadiness from "./ModelReadiness.jsx";
import JobIdentifier from "./JobIdentifier.jsx";

const buildLabels = {
  idle:"빌드 이력 없음", queued:"GPU 대기 중", running:"빌드 중", completed:"최근 빌드 완료",
  failed:"빌드 실패", cancelled:"취소됨", checking:"GPU 환경 확인 중", ready:"빌드 준비 완료",
  rebuild_required:"현재 환경에 맞는 빌드 필요", unavailable:"빌드 유효성 확인 실패",
};

export function KimodoBuildStatus({record,error,pending}) {
  return <><p role="status">{pending ? "빌드 접수 중" : buildLabels[record?.status] || record?.status || "빌드 상태 확인 중"}</p>
    {record?.id && <div>빌드 작업 ID · <JobIdentifier id={record.id} label="빌드 작업 ID" compact/></div>}
    {record?.status === "failed" && record.id && <p>상세 로그 <code>.tmp/test/kimodo-migraphx-build/{record.id}/worker.log</code></p>}
    {(error || record?.error) && <p role="alert">{error || record.error}</p>}</>;
}

export function KimodoBuildButton({record,pending,onStart}) {
  return <button disabled={pending || record?.status !== "rebuild_required"} onClick={onStart}>GPU 대기열에 빌드 등록</button>;
}

export function ModelSelect({models,service,onChange}) {
  return <label>모델 <select value={service} onChange={onChange}>
    {!service && <option value="">모델 선택</option>}
    {models.map(model => <option key={model.id} value={model.id}>{model.label}</option>)}
  </select></label>;
}

function KimodoBuild() {
  const [record, setRecord] = useState(null);
  const [error, setError] = useState("");
  const [pollError,setPollError]=useState(""),[checkedAt,setCheckedAt]=useState(null);
  const [pending, setPending] = useState(false);
  useEffect(() => {
    if (pending) return;
    let active = true, timer;
    async function poll() {
      try {
        const next = await managementCommand("kimodo", "migraphx-build-status");
        if (active) {setRecord(next);setCheckedAt(new Date());setPollError("");}
      } catch (problem) {
        if (active) setPollError(problem.message);
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
      setError("빌드 요청의 접수 결과를 확인하지 못했습니다. 다시 요청하기 전에 빌드 상태를 확인하세요. · "+problem.message);
    } finally {
      setPending(false);
    }
  }
  return <section><h2>DWPose MIGraphX 빌드</h2>
    <KimodoBuildStatus record={record || (pollError ? {status:"unavailable"} : null)} error={error} pending={pending}/>
    {checkedAt && <p>마지막 조회 성공 · {checkedAt.toLocaleString("ko-KR")}</p>}
    {pollError && <p role="alert">빌드 상태를 조회하지 못했습니다. {record && "위 상태는 마지막 조회 결과입니다. "}잠시 후 다시 확인합니다. · {pollError}</p>}
    <KimodoBuildButton record={record} pending={pending || Boolean(pollError)} onStart={start}/>
  </section>;
}

export default function ModelPage() {
  const session=new URLSearchParams(location.search).get("session");
  const [models, setModels] = useState([]);
  const [service, select] = useState("");
  const [error, setError] = useState("");
  const [missingModel,setMissingModel]=useState("");
  const [loading,setLoading]=useState(true),[revision,setRevision]=useState(0);
  useEffect(() => {
    let active=true;
    async function load() {
      setLoading(true);setError("");
      try {
        const response = await fetch("/management/assistant/model-services");
        if (!response.ok) throw new Error("모델 목록을 조회할 수 없습니다.");
        const items = await response.json();
        if(!Array.isArray(items))throw new Error("모델 목록 형식을 확인할 수 없습니다.");
        if(!active)return;
        setModels(items);
        const requested = new URLSearchParams(location.search).get("model");
        const missing=Boolean(requested && !items.some(model=>model.id===requested));
        setMissingModel(missing ? requested : "");
        select(missing ? "" : requested || items[0]?.id || "");
      } catch (problem) {if(active)setError(problem.message);}
      finally {if(active)setLoading(false);}
    }
    load();
    return ()=>{active=false;};
  }, [revision]);
  return <article className="model-management-page"><h1>모델 상태와 파일</h1>
    <a href={"/management/frame/hermes-agent/"+(session?"?"+new URLSearchParams({session}):"")}>헤르메스 대화로 이동</a>
    {loading && <p role="status">모델 목록 조회 중…</p>}
    {error && <div role="alert"><p>{error}</p><button type="button" onClick={()=>setRevision(value=>value+1)}>다시 시도</button></div>}
    {!loading && !error && !models.length && <p>등록된 모델이 없습니다.</p>}
    {missingModel && <p role="status">요청한 모델 ‘{missingModel}’을 목록에서 찾지 못했습니다. 모델을 선택해 주세요.</p>}
    {models.length>0 && <ModelSelect models={models} service={service} onChange={event => {const value=event.target.value;select(value);setMissingModel("");const url=new URL(location.href);url.searchParams.set("model",value);history.replaceState(null,"",url);}}/>}
    {service === "flux-image" && <p>약 20.32GB · <a href="https://huggingface.co/black-forest-labs/flux-3-image-klein">FLUX 접근 조건</a>을 확인하고 Hugging Face에 로그인하세요.</p>}
    {service === "prompt-translation" && <p><a href="https://huggingface.co/google/translategemma-4b-it">Gemma 접근 조건</a>에 동의하고 Hugging Face에 로그인하세요.</p>}
    {service === "animationgpt" && <p>제3자 FP16 변환본과 토크나이저·정규화 파일 약 770MB · <a href="https://huggingface.co/Kijai/AnimationGPT_pruned">출처와 라이선스</a> · 생성기 연결과 무기 출력은 별도입니다.</p>}
    {service === "wan21-fun-1.3b" && <p>공용 텍스트 인코더와 VAE는 14B 준비 환경을 사용합니다.</p>}
    {service && <ModelReadiness key={service} service={service} manage/>}
    {service && <DownloadProgress key={"progress-" + service} service={service}/>}
    {service === "kimodo" && <KimodoBuild/>}
  </article>;
}

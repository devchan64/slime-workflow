import DownloadProgress from "./DownloadProgress.jsx";
import ModelBackupCompare from "./ModelBackupCompare.jsx";
import ModelCatalog from "./ModelCatalog.jsx";
import React, {useEffect, useId, useRef, useState} from "react";
import {managementCommand,untilAborted} from "./managementCommand.js";
import ModelReadiness from "./ModelReadiness.jsx";
import JobIdentifier from "./JobIdentifier.jsx";
import {resolveModelSelection} from "./modelSelection.mjs";
import {isBuildVerificationFresh} from "./buildVerification.mjs";

const buildLabels = {
  idle:"빌드 이력 없음", queued:"GPU 대기 중", running:"빌드 중", completed:"최근 빌드 완료",
  failed:"빌드 실패", cancelled:"취소됨", checking:"GPU 환경 확인 중", ready:"빌드 준비 완료",
  rebuild_required:"현재 환경에 맞는 빌드 필요", unavailable:"빌드 유효성 확인 실패",
};
function validBuildRecord(record){
  return Boolean(record && typeof record==="object" && Object.hasOwn(buildLabels,record.status) && (record.id==null || typeof record.id==="string") && (record.error==null || typeof record.error==="string"));
}

export function KimodoBuildStatus({record,error,pending}) {
  return <><p role="status">{pending ? "빌드 접수 중" : buildLabels[record?.status] || record?.status || "빌드 상태 확인 중"}</p>
    {record?.id && <div>빌드 작업 ID · <JobIdentifier id={record.id} label="빌드 작업 ID" compact/></div>}
    {record?.status === "failed" && record.id && <p>상세 로그 <code>.tmp/test/kimodo-migraphx-build/{record.id}/worker.log</code></p>}
    {(error || record?.error) && <p role="alert">{error || record.error}</p>}</>;
}

export function KimodoBuildButton({record,pending,checking,pollError,onStart}) {
  const reasonId=useId();
  const reason=pending ? "빌드 요청을 접수하고 있습니다." : checking ? "GPU 환경 확인이 끝날 때까지 기다리세요." : pollError ? "빌드 상태를 다시 확인한 후 등록할 수 있습니다." : !record ? "빌드 상태를 확인하고 있습니다." : record.status === "rebuild_required" ? "" : ["queued","running"].includes(record.status) ? "빌드가 대기 중이거나 진행 중입니다. 완료될 때까지 기다리세요." : record.status === "checking" ? "GPU 환경 확인이 끝날 때까지 기다리세요." : record.status === "unavailable" ? "빌드 유효성을 확인하지 못했습니다. GPU 환경 확인을 다시 시도하세요." : record.status === "ready" ? "현재 빌드가 준비되어 있어 추가 등록이 필요하지 않습니다." : "GPU 환경 확인을 눌러 빌드가 필요한지 확인하세요.";
  return <><button disabled={Boolean(reason)} aria-describedby={reason ? reasonId : undefined} onClick={onStart}>GPU 대기열에 빌드 등록</button>{reason && <p id={reasonId}>{reason}</p>}</>;
}

export function ModelSelect({models,service,onChange,descriptionId}) {
  return <label>모델 <select value={service} onChange={onChange} aria-describedby={descriptionId || undefined}>
    {!service && <option value="">모델 선택</option>}
    {models.map(model => <option key={model.id} value={model.id}>{model.label}</option>)}
  </select></label>;
}

function KimodoBuild() {
  const [record, setRecord] = useState(null);
  const [error, setError] = useState("");
  const [pollError,setPollError]=useState(""),[checkedAt,setCheckedAt]=useState(null);
  const [pending, setPending] = useState(false);
  const [verify,setVerify]=useState(false);
  const verifyReasonId=useId();
  const verified=useRef(null),verifyExpiry=useRef(null),submitPending=useRef(false);
  function clearVerified(){clearTimeout(verifyExpiry.current);verifyExpiry.current=null;verified.current=null;}
  useEffect(()=>()=>clearVerified(),[]);
  useEffect(() => {
    if (pending) return;
    let active = true, timer,controller;
    async function poll() {
      controller=new AbortController();let timedOut=false;
      const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
      try {
        const next = await untilAborted(managementCommand("kimodo", verify ? "migraphx-build-status" : "migraphx-build-observe",{},{signal:controller.signal}),controller.signal);
        if(!validBuildRecord(next))throw new Error("빌드 상태 응답 형식을 확인할 수 없습니다.");
        if (active) {
          if(verify && next.status!=="checking"){
            clearVerified();
            if(["ready","rebuild_required","unavailable"].includes(next.status)){
              const result={record:next,id:next.id || null,buildStatus:next.build_status || "idle",checkedAt:Date.now()};
              verified.current=result;
              verifyExpiry.current=setTimeout(()=>{
                if(verified.current!==result)return;
                clearVerified();setRecord(current=>current===result.record ? {status:result.buildStatus,id:result.id,cache_status:"unverified"} : current);
              },30000);
            }
            setVerify(false);
          }
          if(!verify && verified.current && (Date.now()-verified.current.checkedAt>=30000 || verified.current.id!==(next.id || null) || verified.current.buildStatus!==next.status))clearVerified();
          setRecord(!verify && verified.current ? verified.current.record : next);setCheckedAt(new Date());setPollError("");
        }
      } catch (problem) {
        if (active) {setPollError(timedOut ? "빌드 상태 조회 시간이 초과됐습니다." : problem.message || "빌드 상태를 확인할 수 없습니다.");if(verify){clearVerified();setVerify(false);}}
      } finally {
        clearTimeout(timeout);
        if (active) timer = setTimeout(poll, 5000);
      }
    }
    poll();
    return () => {active = false; clearTimeout(timer);controller?.abort();};
  }, [pending,verify]);
  async function start() {
    if(submitPending.current || verify || pending)return;
    const confirmation=verified.current;
    if(!isBuildVerificationFresh(confirmation)){
      if(confirmation)setRecord({status:confirmation.buildStatus,id:confirmation.id,cache_status:"unverified"});
      clearVerified();setError("GPU 환경 확인이 만료됐습니다. 다시 확인한 후 빌드를 등록하세요.");return;
    }
    submitPending.current=true;clearVerified();
    setPending(true);
    setError("");
    setRecord(null);
    try {
      const controller=new AbortController();let timedOut=false;
      const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
      let next;
      try{next=await untilAborted(managementCommand("kimodo", "migraphx-build",{},{signal:controller.signal}),controller.signal);}
      catch(problem){throw new Error(timedOut ? "응답 시간이 초과됐습니다." : problem.message);}
      finally{clearTimeout(timeout);}
      if(!validBuildRecord(next))throw new Error("빌드 접수 응답 형식을 확인할 수 없습니다.");
      setRecord(next);
    } catch (problem) {
      setError("빌드 요청의 접수 결과를 확인하지 못했습니다. 다시 요청하기 전에 빌드 상태를 확인하세요. · "+problem.message);
    } finally {
      submitPending.current=false;setPending(false);
    }
  }
  const verifyReason=pending ? "빌드 요청 접수 중에는 GPU 환경을 확인할 수 없습니다." : verify ? "GPU 환경을 확인하고 있습니다." : pollError ? "빌드 기록 조회가 복구된 후 확인하세요." : !record ? "먼저 빌드 기록을 확인하고 있습니다." : ["queued","running"].includes(record.status) ? "빌드가 대기 중이거나 진행 중입니다. 완료 후 확인하세요." : "";
  return <section><h2>DWPose MIGraphX 빌드</h2>
    <KimodoBuildStatus record={record || (pollError ? {status:"unavailable"} : null)} error={error} pending={pending}/>
    {checkedAt && <p>마지막 조회 성공 · {checkedAt.toLocaleString("ko-KR")}</p>}
    {pollError && <p role="alert">빌드 상태를 조회하지 못했습니다. {record && "위 상태는 마지막 조회 결과입니다. "}잠시 후 다시 확인합니다. · {pollError}</p>}
    <p>자동 조회는 빌드 기록만 확인합니다. GPU 환경 확인을 누르면 검사 작업이 GPU 대기열에 등록될 수 있습니다.</p>
    <button type="button" aria-disabled={Boolean(verifyReason)} aria-describedby={verifyReason ? verifyReasonId : undefined} onClick={()=>{if(verifyReason)return;clearVerified();setError("");setPollError("");setVerify(true);}}>{verify ? "GPU 환경 확인 중…" : "GPU 환경 확인"}</button>
    {verifyReason && <p id={verifyReasonId}>{verifyReason}</p>}
    <KimodoBuildButton record={record} pending={pending} checking={verify} pollError={pollError} onStart={start}/>
  </section>;
}

export default function ModelPage() {
  const [backupSelection, setBackupSelection] = useState(null);
  const session=new URLSearchParams(location.search).get("session");
  const [models, setModels] = useState([]);
  const [service, select] = useState("");
  const [modelQuery,setModelQuery] = useState("");
  const selectedRef=useRef(""),missingRef=useRef("");
  const [error, setError] = useState("");
  const [missingModel,setMissingModel]=useState("");
  const [checkedAt,setCheckedAt]=useState(null);
  const missingModelId=useId();
  const [loading,setLoading]=useState(true),[revision,setRevision]=useState(0);
  useEffect(() => {
    let active=true,timedOut=false;
    const controller=new AbortController();
    const timeout=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    async function load() {
      setLoading(true);setError("");
      try {
        const items=await untilAborted((async()=>{const response=await fetch("/management/assistant/model-services",{signal:controller.signal});if(!response.ok)throw new Error("모델 목록을 조회할 수 없습니다.");return response.json();})(),controller.signal);
        if(!Array.isArray(items) || items.some(item=>!item || typeof item.id!=="string" || !item.id.trim() || typeof item.label!=="string" || !item.label.trim()) || new Set(items.map(item=>item.id)).size!==items.length)throw new Error("모델 목록 형식을 확인할 수 없습니다.");
        if(!active)return;
        setModels(items);setCheckedAt(new Date());
        const requested = new URLSearchParams(location.search).get("model");
        const choice=resolveModelSelection(items,selectedRef.current || missingRef.current,requested);
        selectedRef.current=choice.selected;missingRef.current=choice.missing;select(choice.selected);setMissingModel(choice.missing);
      } catch (problem) {if(active)setError(timedOut ? "모델 목록 조회 시간이 초과됐습니다. 다시 시도하세요." : problem.message || "모델 목록을 조회할 수 없습니다.");}
      finally {clearTimeout(timeout);if(active)setLoading(false);}
    }
    load();
    return ()=>{active=false;clearTimeout(timeout);controller.abort();};
  }, [revision]);
  const searchTerms=modelQuery.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const matchingModels=models.filter(model=>searchTerms.every(term=>`${model.label} ${model.id}`.toLocaleLowerCase().includes(term)));
  const selectedModel=models.find(model=>model.id===service);
  function chooseModel(value){
    selectedRef.current=value;missingRef.current="";select(value);setMissingModel("");
    const url=new URL(location.href);url.searchParams.set("model",value);history.replaceState(null,"",url);
  }
  return <article className="model-management-page"><h1>모델 상태와 파일</h1>
    <a href={"/management/frame/hermes-agent/"+(session?"?"+new URLSearchParams({session}):"")}>헤르메스 대화로 이동</a>
    <button type="button" aria-disabled={loading} onClick={()=>{if(!loading)setRevision(value=>value+1);}}>{loading ? "모델 목록 조회 중…" : "모델 목록 새로고침"}</button>
    {checkedAt && <p>마지막 목록 조회 성공 · {checkedAt.toLocaleString("ko-KR")}</p>}
    {loading && <p role="status">모델 목록을 조회하고 있습니다.{models.length>0 && " 아래는 마지막 조회 결과입니다."}</p>}
    {error && <p role="alert">{error}{models.length>0 && " · 이전 목록을 유지합니다."}</p>}
    {!loading && !error && !models.length && <p>등록된 모델이 없습니다.</p>}
    {missingModel && <p id={missingModelId} role="status">요청한 모델 ‘{missingModel}’을 목록에서 찾지 못했습니다. 모델을 선택해 주세요.</p>}
    {models.length>0 && <section className="model-finder" aria-labelledby="model-list-heading"><h2 id="model-list-heading">모델 찾기</h2>
      <p>목록에서 모델을 선택하면 아래에 준비 상태와 다운로드 기록이 표시됩니다. 이름이나 서비스 ID로 검색할 수도 있습니다.</p>
      <label>모델 검색 <input type="search" value={modelQuery} onChange={event=>setModelQuery(event.target.value)} placeholder="예: FLUX, 번역, wan22"/></label>
      {modelQuery && <button type="button" onClick={()=>setModelQuery("")}>검색 지우기</button>}
      {selectedModel && <p>선택한 모델 · <strong>{selectedModel.label}</strong> <small>({selectedModel.id})</small></p>}
      <p role="status">{modelQuery.trim() ? `검색 결과 ${matchingModels.length}개 / 전체 ${models.length}개` : `등록 모델 ${models.length}개`}{service && searchTerms.length>0 && !matchingModels.some(model=>model.id===service) ? " · 현재 선택은 유지됩니다." : ""}</p>
      <div role="group" aria-label="모델 목록" className="model-choice-list">
        {matchingModels.map(model=><button key={model.id} type="button" className="generator-history-select" aria-pressed={service===model.id} onClick={()=>chooseModel(model.id)}><span className="history-card-content"><span className="history-card-heading"><strong>{model.label}</strong>{service===model.id && <span>선택됨</span>}</span><small className="history-card-id">{model.id}</small></span></button>)}
      </div>
      {modelQuery.trim() && matchingModels.length===0 && <p>일치하는 모델이 없습니다. 다른 이름이나 서비스 ID로 검색하세요.</p>}
    </section>}
    {service === "flux-image" && <p>약 20.32GB · <a href="https://huggingface.co/black-forest-labs/flux-3-image-klein">FLUX 접근 조건</a>을 확인하고 Hugging Face에 로그인하세요.</p>}
    {service === "hermes-model" && <p>아래는 모델 파일과 실행 구성의 준비 상태입니다. 세션별 GPU 로딩 여부는 대화 입력창의 Qwen 3.8 상태에서 확인하세요.</p>}
    {service === "prompt-translation" && <p><a href="https://huggingface.co/google/translategemma-4b-it">Gemma 접근 조건</a>에 동의하고 Hugging Face에 로그인하세요.</p>}
    {service === "animationgpt" && <p>제3자 FP16 변환본과 토크나이저·정규화 파일 약 770MB · <a href="https://huggingface.co/Kijai/AnimationGPT_pruned">출처와 라이선스</a> · 생성기 연결과 무기 출력은 별도입니다.</p>}
    {service === "wan22-fighting-lora" && <p>High Noise LoRA 약 38MB · <a href="https://www.runninghub.ai/model/public/1984976690503958530">모델 정보</a> · <a href="https://huggingface.co/r4tn4/Bubble/blob/338e12cb179abf0573b61c310db6163018effdde/wan2.2fighting_high_noise.safetensors">다운로드 사본</a> · VACE 생성기 연결과 실제 동작은 별도 검증이 필요합니다.</p>}
    {service === "wan21-fun-1.3b" && <p>공용 텍스트 인코더와 VAE는 14B 준비 환경을 사용합니다.</p>}
    {service && <ModelReadiness key={service} service={service} manage/>}
    {service && <DownloadProgress key={"progress-" + service} service={service}/>}
    <ModelCatalog onCompare={(name, jobId) => setBackupSelection({name, jobId, request: Symbol()})}/>
    <ModelBackupCompare requestedSelection={backupSelection}/>
    {service === "kimodo" && <KimodoBuild/>}
  </article>;
}

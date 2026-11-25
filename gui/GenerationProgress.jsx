import React from "react";
import {LiveRefreshControl} from "./LiveRefresh.jsx";
import {observedGenerationProgress,validInferenceCompletion,unmeasuredStageLabel} from "./generationProgressModel.mjs";

const stages={prepare:"준비",load:"모델 불러오기",encoding:"입력 인코딩",inference:"추론",saving:"결과 저장",'pose-preprocess':"포즈 전처리",completed:"완료",failed:"실패",cancelled:"취소"};
function time(value){const date=new Date(value);return value && !Number.isNaN(date.getTime()) ? date.toLocaleString("ko-KR",{timeZone:"Asia/Seoul",hour12:false}) : "확인 불가";}
function showObservationTime(value,reference){const observed=new Date(value).getTime(),queried=new Date(reference).getTime();return !value || !Number.isFinite(observed) || !reference || !Number.isFinite(queried) || queried-observed>30000 || observed>queried+30000;}
function completionPassed(value,reference){const completion=new Date(value).getTime(),queried=new Date(reference).getTime();return Boolean(value && reference && Number.isFinite(completion) && Number.isFinite(queried) && completion<queried);}

export default function GenerationProgress({job,jobId,service,live,supportsProgress=true,showQueryTime=true,referenceTime}){
  const estimate=job?.estimate, observed=observedGenerationProgress(job);
  const unmeasured=unmeasuredStageLabel(observed,service);
  const stageName=observed && (Object.hasOwn(stages,observed.stage) ? stages[observed.stage] : observed.stage);
  const queryTime=referenceTime || job.queried_at;
  const running=job.status==="running" || job.status==="queued";
  const inference=observed?.estimate;
  const pendingEstimate=estimate && estimate.total_seconds===null && estimate.remaining===null && estimate.completion===null && estimate.estimated_progress===null;
  return <section ref={live?.ref} className="generation-progress" aria-label="생성 진행 상황">
    <strong>생성 진행 상황</strong>
    {live && <LiveRefreshControl live={live} label="진행 상황 자동 갱신" inactiveReason={["completed","failed","cancelled","canceled"].includes(job.status) ? "작업 종료로 중지" : ["missing","unknown"].includes(job.status) ? "작업 상태 확인 불가" : "일시 중지"}/>}
    {showQueryTime && job.queried_at && <p>조회 시각 · {time(job.queried_at)}</p>}
    {estimate && running && <div className="generation-estimate">{showObservationTime(estimate.updated_at,queryTime) || completionPassed(estimate.completion,queryTime) ? <p>전체 예상 정보가 오래됐거나 유효하지 않습니다. 최신 진행을 확인하세요.</p> : pendingEstimate ? <p>전체 예상 시간·남은 시간·완료 시각·진행률 · 계산 중 · {estimate.basis} · 표본 {estimate.sample_count}개</p> : <><p>예상 총 소요 시간 · {estimate.total_seconds===null ? "계산 중" : `약 ${Math.ceil(estimate.total_seconds/60)}분`}</p>
      <p>예상 남은 시간 · {estimate.remaining===null ? "계산 중" : `조회 시점 기준 약 ${Math.ceil(estimate.remaining/60)}분`} · 예상 완료 · {estimate.completion ? time(estimate.completion) : "계산 중"}</p>
      <p>예상 진행률 · {estimate.estimated_progress===null ? "계산 중" : `${estimate.estimated_progress}%`} · {estimate.basis} · 표본 {estimate.sample_count}개</p></>}
      <p>추정 범위 · {estimate.scope}</p>{showObservationTime(estimate.updated_at,queryTime) && <p>예상 정보 갱신 · {time(estimate.updated_at)}</p>}</div>}
    {running && !estimate && <p>전체 예상 시간은 확인할 수 없습니다. 작업 상태를 다시 확인하세요.</p>}
    {observed ? <div className="generation-stage">
      {unmeasured ? <p>{unmeasured} · 이 단계의 진행률은 제공되지 않습니다.</p> : <><p>{stageName} · 단계 진행 {observed.step}/{observed.total} (전체 작업 진행률과 별개)</p>
      <progress aria-label={`${jobId ? jobId+' · ' : ''}${stageName} 단계 진행`} aria-valuetext={`${observed.step} / ${observed.total}`} max={observed.total} value={observed.step}/></>}
      <p>관측 범위 · {observed.scope || '현재 단계'}</p>{showObservationTime(observed.updatedAt,queryTime) && <p>단계 관측 · {time(observed.updatedAt)}</p>}
      {running && inference && !unmeasured && <p>추론 종료 예상 · {showObservationTime(observed.updatedAt,queryTime) || completionPassed(inference.completion,queryTime) ? "이전 관측이거나 예상 시각이 지났습니다. 최신 진행을 확인하세요." : Number.isFinite(inference.remaining) && inference.remaining>=0 && validInferenceCompletion(inference.completion) ? `조회 시점 기준 약 ${Math.ceil(inference.remaining/60)}분 후 (${time(inference.completion)})` : "계산 중 · 유효한 추론 예상 정보를 기다리는 중입니다."}<br/>
        {inference.basis} · 표본 {inference.samples}개<br/>{inference.scope}</p>}
    </div> : <p>{!supportsProgress ? "이 서비스는 상세 진행 이벤트를 제공하지 않습니다. 작업 상태와 결과를 확인하세요." : running ? "현재 시도의 진행 관측을 기다리는 중입니다." : "이 작업에는 진행 이벤트가 없습니다."}</p>}
  </section>;
}

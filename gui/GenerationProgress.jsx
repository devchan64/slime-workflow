import React from "react";
import {LiveRefreshControl} from "./LiveRefresh.jsx";

const stages={prepare:"준비",load:"모델 불러오기",encoding:"입력 인코딩",inference:"추론",saving:"결과 저장",'pose-preprocess':"포즈 전처리",completed:"완료",failed:"실패",cancelled:"취소"};
function time(value){const date=new Date(value);return value && !Number.isNaN(date.getTime()) ? date.toLocaleString("ko-KR",{timeZone:"Asia/Seoul",hour12:false}) : "확인 불가";}

export default function GenerationProgress({job,live,supportsProgress=true}){
  const event=job?.progress_event, estimate=job?.estimate;
  const running=job.status==="running" || job.status==="queued";
  const remaining=event?.["generation.estimate.remaining_seconds"];
  const completion=event?.["generation.estimate.completion_time"];
  return <section ref={live?.ref} className="generation-progress" aria-label="생성 진행 상황">
    <strong>생성 진행 상황</strong>
    {live && <LiveRefreshControl live={live} label="진행 상황 자동 갱신"/>}
    {job.queried_at && <p>조회 시각 · {time(job.queried_at)}</p>}
    {estimate && running && <div><p>예상 총 소요 시간 · {estimate.total_seconds===null ? "계산 중" : `약 ${Math.ceil(estimate.total_seconds/60)}분`}</p>
      <p>예상 남은 시간 · {estimate.remaining===null ? "계산 중" : `약 ${Math.ceil(estimate.remaining/60)}분`} · 예상 완료 · {estimate.completion ? time(estimate.completion) : "계산 중"}</p>
      <p>예상 진행률 · {estimate.estimated_progress===null ? "계산 중" : `${estimate.estimated_progress}%`} · {estimate.basis} · 표본 {estimate.sample_count}개</p>
      <p>추정 범위 · {estimate.scope} · 갱신 시각 · {time(estimate.updated_at)}</p></div>}
    {running && !estimate && !event && <p>예상 시간은 확인할 수 없습니다. 작업 상태를 다시 확인하세요.</p>}
    {event ? <>
      <p>{stages[event["generation.stage"]] || event["generation.stage"]} · 추론 스텝 {event["generation.step"]}/{event["generation.step.total"]}</p>
      <progress aria-label="추론 스텝 진행" max={event["generation.step.total"]} value={event["generation.step"]}/>
      <p>관측 시각 · {time(event["generation.updated_at"])}</p>
      {running && <p>추론 종료 예상 · {Number.isFinite(remaining) && remaining>=0 && completion ? `약 ${Math.ceil(remaining/60)}분 후 (${time(completion)})` : "계산 중 · 추론 스텝 표본이 필요합니다."}<br/>
        {event["generation.estimate.basis"]} · 표본 {event["generation.estimate.sample_count"]}개<br/>{event["generation.estimate.scope"]}</p>}
    </> : <p>{!supportsProgress ? "이 서비스는 상세 진행 이벤트를 제공하지 않습니다. 작업 상태와 결과를 확인하세요." : running ? "현재 시도의 진행 관측을 기다리는 중입니다." : "이 작업에는 진행 이벤트가 없습니다."}</p>}
  </section>;
}

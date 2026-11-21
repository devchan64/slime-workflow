import React from "react";
import {LiveRefreshControl} from "./LiveRefresh.jsx";

const stages={prepare:"준비",load:"모델 불러오기",encoding:"입력 인코딩",inference:"추론",saving:"결과 저장",'pose-preprocess':"포즈 전처리",completed:"완료",failed:"실패",cancelled:"취소"};
function time(value){const date=new Date(value);return value && !Number.isNaN(date.getTime()) ? date.toLocaleString("ko-KR",{timeZone:"Asia/Seoul",hour12:false}) : "확인 불가";}

export default function GenerationProgress({job,live,supportsProgress=true}){
  const event=job?.progress_event;
  const running=job.status==="running" || job.status==="queued";
  const remaining=event?.["generation.estimate.remaining_seconds"];
  const completion=event?.["generation.estimate.completion_time"];
  return <section ref={live?.ref} className="generation-progress" aria-label="생성 진행 상황">
    <strong>생성 진행 상황</strong>
    {live && <LiveRefreshControl live={live} label="진행 상황 자동 갱신"/>}
    {job.queried_at && <p>조회 시각 · {time(job.queried_at)}</p>}
    {event ? <>
      <p>{stages[event["generation.stage"]] || event["generation.stage"]} · 추론 스텝 {event["generation.step"]}/{event["generation.step.total"]}</p>
      <progress aria-label="추론 스텝 진행" max={event["generation.step.total"]} value={event["generation.step"]}/>
      <p>관측 시각 · {time(event["generation.updated_at"])}</p>
      {running && <p>추론 종료 예상 · {Number.isFinite(remaining) && remaining>=0 && completion ? `약 ${Math.ceil(remaining/60)}분 후 (${time(completion)})` : "계산 중 · 추론 스텝 표본이 필요합니다."}<br/>
        {event["generation.estimate.basis"]} · 표본 {event["generation.estimate.sample_count"]}개<br/>{event["generation.estimate.scope"]}</p>}
    </> : <p>{!supportsProgress ? "이 서비스는 상세 진행 이벤트를 제공하지 않습니다. 작업 상태와 결과를 확인하세요." : running ? "현재 시도의 진행 관측을 기다리는 중입니다." : "이 작업에는 진행 이벤트가 없습니다."}</p>}
  </section>;
}

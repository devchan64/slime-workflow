import React,{useId} from 'react';

export function ActiveGeneratorJobStatus({statusRef,retryRef,loading,notice,error,activeId,job,onOpen,onRetry,showRetry=false}){
  const errorId=useId();
  return <div ref={statusRef} tabIndex={-1} className="proposal-feedback" aria-label="진행 작업 조회 상태">
    {loading && <p role="status">진행 작업을 확인하고 있습니다.</p>}{notice && <p role="status">{notice}</p>}
    {activeId && activeId!==job && !loading && !error && <button type="button" aria-label={activeId+' 진행 작업 결과 보기'} onClick={onOpen}>진행 작업 결과 보기</button>}
    {error && <p id={errorId} role="alert">{error}</p>}
    {showRetry && !loading && <button ref={retryRef} type="button" aria-describedby={error ? errorId : undefined} onClick={onRetry}>진행 작업 다시 확인</button>}
  </div>;
}

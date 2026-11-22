const stages={queued:"대기",preparing:"환경 준비",indexing:"학습",searching:"탐색",reasoning:"작성·중복 판단",review:"변경 검토 대기",completed:"완료",applied:"원본 적용 완료",failed:"실패",interrupted:"중단"};
const modes={prepare:"환경 준비",learn:"문서 학습",write:"작성 제안",deduplicate:"중복 검토"};
export const writerStageLabel=value=>Object.hasOwn(stages,value) ? stages[value] : value;
export const writerModeLabel=value=>Object.hasOwn(modes,value) ? modes[value] : value;

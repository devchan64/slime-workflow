"""Hermes가 제공하는 주요 관리 기능의 범위와 영향 안내."""

HERMES_CAPABILITY_RECORDS = (
    {'command':'hermes-cleanup-preview','label':'이력 정리 대상 요약','required':['service'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'cleanup_preview','note':'삭제 없이 원 서비스 정리 후보·차단 수를 확인한다. 숨긴 작업까지 전체 순회할 수 있으며 대상과 상태는 변경될 수 있다.'},
    {'command':'hermes-video-resume-proposal','label':'영상 재개 제안 조회','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'video_resume_proposal','note':'완료된 대화의 영상 재개 제안을 읽는다.'},
    {'command':'hermes-video-resume-preview','label':'영상 재개 예비 검토','required':['service','job_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'video_resume_preview','note':'저장 입력과 준비 작업 상태를 검토한다. GPU 가용성은 별도다.'},
    {'command':'hermes-video-resume-submit','label':'영상 재개 접수','required':['request_id','service','job_id','expected_resume_fingerprint'],'optional':[],'effect':'enqueue','gpu':'queued','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'video_resume_receipt','note':'검토 지문을 재확인하고 중복 접수를 방지한다.'},
    {'command':'hermes-video-resume-receipt','label':'영상 재개 접수 조회','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'video_resume_receipt','note':'접수 기록을 확인한다. 실제 실행 상태는 원 서비스에서 확인한다.'},
    {'command':'hermes-flux-resume-proposal','label':'FLUX 재개 제안 조회','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'flux_resume_proposal','note':'완료된 Hermes 답변의 서비스·작업 ID와 검토값을 읽는다. GPU 재개는 하지 않는다.'},
    {'command':'hermes-flux-resume-submit','label':'FLUX 재개 접수','required':['request_id','service','job_id','expected_resume_fingerprint'],'optional':[],'effect':'enqueue','gpu':'queued','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'flux_resume_receipt','note':'검토 지문과 모델 준비 충돌을 재확인하고 중복 접수를 막는다. 실행 및 GPU 가용성은 별도다.'},
    {'command':'hermes-flux-resume-receipt','label':'FLUX 재개 접수 조회','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'flux_resume_receipt','note':'접수 기록만 확인하며 실제 실행·완료는 원 서비스에서 확인한다.'},
    {'command':'hermes-flux-resume-preview','label':'FLUX 재개 예비 검토','required':['service','job_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'flux_resume_preview','note':'저장 요청·참조·실행 기록과 모델 준비 충돌을 잠금 아래 검토한다. GPU 가용성은 별도다.'},
    {'command':'hermes-kimodo-resume-submit','label':'Kimodo 재개 접수','required':['request_id','job_id','expected_resume_fingerprint'],'optional':[],'effect':'enqueue','gpu':'queued','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'kimodo_resume_receipt','note':'검토값과 잠금·키프레임을 재확인하고 중복 접수를 막는다. 실행 및 GPU 가용성은 별도다.'},
    {'command':'hermes-kimodo-resume-receipt','label':'Kimodo 재개 접수 조회','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'kimodo_resume_receipt','note':'접수 기록만 확인하며 실제 실행·완료는 원 서비스에서 확인한다.'},
    {'command':'hermes-kimodo-resume-proposal','label':'Kimodo 재개 제안 읽기','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'kimodo_resume_proposal','note':'완료된 Hermes 답변의 작업 ID와 검토값을 읽는다. GPU 재개는 하지 않는다.'},
    {'command':'hermes-kimodo-resume-preview','label':'Kimodo 재개 예비 검토','required':['job_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'kimodo_resume_preview','note':'작업 상태·실행 명령·키프레임과 모델 준비 충돌을 조회한다. 진행 중·확인 불가는 재개를 보류하며 GPU 가용성은 별도다.'},
    {'command':'hermes-translation-resume-preview','label':'번역 작업 재개 검토','required':['job_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'translation_resume_preview','note':'저장 기록과 기존 실행 잠금을 확인한다. 번역을 실행하지 않는다.'},
    {'command':'hermes-translation-resume-submit','label':'번역 작업 재개 접수','required':['request_id','job_id','expected_resume_fingerprint'],'optional':[],'effect':'enqueue','gpu':'queued','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'translation_resume_receipt','note':'검토한 기록을 재확인하고 대기열에 접수한다. 결과 불명 시 자동 재접수하지 않는다.'},
    {'command':'hermes-translation-resume-receipt','label':'번역 재개 접수 확인','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'translation_resume_receipt','note':'접수 기록이며 번역 완료나 GPU 종료를 보장하지 않는다.'},
    {'command':'hermes-audio-resume-preview','label':'음악·효과음 재개 검토','required':['service','job_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'audio_resume_preview','note':'기록·실행 잠금과 모델 다운로드 상태를 확인한다. 재개 대상이 모델 준비 작업이면 다른 준비 작업도 확인한다. 확인 불가는 재개를 보류하며 접수 시 다시 검사한다. GPU 가용성은 보장하지 않는다.'},
    {'command':'hermes-audio-resume-submit','label':'음악·효과음 재개 접수','required':['request_id','service','job_id','expected_resume_fingerprint'],'optional':[],'effect':'enqueue','gpu':'queued','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'audio_resume_receipt','note':'접수 전 충돌이나 기록 변경은 blocked로 반환하며 접수 기록을 만들지 않는다. 접수 후 결과 불명 시 자동 재접수하지 않는다.'},
    {'command':'hermes-audio-resume-receipt','label':'음악·효과음 재개 접수 확인','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'audio_resume_receipt','note':'접수 기록을 읽는다. 작업 완료나 GPU 프로세스 종료를 보장하지 않는다.'},
    {'command':'hermes-generator-reservation-recover','label':'생성기 GPU 예약 정리','required':['request_id','service','job_id','review_sha256','outside_processes_checked'],'optional':[],'effect':'write','gpu':'none','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'generator_reservation_receipt','note':'검토한 작업자 그룹을 강제 종료하고 예약을 해제한다. 별도 GPU 프로세스를 확인한 사용자 지시가 필요하다.'},
    {'command':'hermes-generator-reservation-receipt','label':'생성기 GPU 예약 정리 접수 확인','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'generator_reservation_receipt','note':'응답 유실 시 확인하며 확인 불가 접수를 재실행하지 않는다.'},
    {'command':'hermes-generator-reservation-inspect','label':'생성기 GPU 예약 신원 조회','required':['service','job_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'generator_reservation_identity','note':'유일한 예약과 원 서비스·작업자 리더를 비파괴 조회한다. 그룹 전체·별도 그룹과 예약 해제는 확인하지 않는다.'},
    {'command':'hermes-generator-source-history','label':'생성·번역 원본 이력','required':['service'],'optional':['offset','limit','snapshot','query'],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'generator_source_history','note':'기록 상태만 읽는다. 건물 호환 경로는 빌보드 이력을 공유한다. 중단 작업 복구를 실행하지 않으며 실제 생존과 결과는 별도 확인한다.'},
    {'command':'hermes-audio-source-status','label':'음악·효과음 원본 작업 상태','required':['service','job_id'],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'audio_source_job_status','note':'직접 시작한 작업을 ID로 조회한다. 파일 관측은 존재·확인 불가를 구분하며 재생·품질이나 프로세스 생존은 별도다.'},
    {'command':'hermes-audio-source-history','label':'음악·효과음 원본 이력','required':['service'],'optional':['offset','limit','snapshot','query'],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'audio_source_history','note':'Hermes 접수 이외의 원본 이력도 기록 상태만 읽는다. 실제 작업 생존과 결과는 별도다.'},
    {'command':'hermes-kimodo-build-status','label':'Kimodo MIGraphX 빌드 기록','required':[],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'kimodo_build_status','note':'최근 빌드 기록만 읽는다. 캐시 유효성과 작업 생존은 별도 확인한다.'},
    {'command':'hermes-capabilities','label':'Hermes 기능 목록','required':[],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'capability_catalog','note':'게이트웨이 등록과 목록의 차이를 함께 표시한다.'},
    {'command':'hermes-session-create','label':'대화 세션 생성','required':['session_id'],'optional':[],'effect':'write','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'session','note':'같은 세션 ID로 재시도할 수 있다.'},
    {'command':'hermes-session-read','label':'대화 세션 기록 조회','required':['session_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'session','note':'저장된 세션 기록을 읽는다.'},
    {'command':'hermes-session-list','label':'대화 세션 목록','required':[],'optional':['offset','limit','snapshot','query'],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'session_list','note':'최근 세션과 잘림 여부를 반환한다.'},
    {'command':'hermes-session-view','label':'대화 및 작업 상태 조회','required':['session_id'],'optional':['offset','snapshot'],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'session_view','note':'최근 메시지와 연결된 작업 상태를 제공한다.'},
    {'command':'hermes-submit','label':'운영·격리 작업 접수','required':['request_id','prompt'],'optional':['verification_modules'],'effect':'enqueue','gpu':'exclusive','retry':'request_id','interfaces':['gui','mcp'],'result':'hermes_job_id','note':'운영 조회·제안과 격리 코드 작업을 처리한다. 코드 변경은 격리 사본에 남으며 동일 접수 ID와 입력은 기존 작업을 반환한다. 배타 예약은 관리도구 대기열에만 적용되며 외부 GPU 작업과 성능 경합이 가능하다.'},
    {'command':'hermes-detail','label':'격리 작업 상세 조회','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'hermes_job_detail','note':'상태와 답변·diff·검증 결과를 반환한다.'},
    {'command':'hermes-history','label':'격리 작업 이력 조회','required':[],'optional':['offset','limit','snapshot','query','status'],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'hermes_history','note':'빈 입력은 기존 최근 100건이며 전체 이력의 검색·상태 필터와 최대 30건 페이지를 지원한다. 다음 페이지는 동일 조건과 목록 확인값이 필요하다. 작업 상태는 조회 시점의 값이다.'},
    {'command':'hermes-cancel','label':'격리 작업 중지 요청','required':['id'],'optional':[],'effect':'cancel_request','gpu':'none','retry':'check_status','interfaces':['gui','mcp'],'result':'cancel_request_status','note':'중지 요청과 실제 프로세스 종료는 구분한다.'},
    {'command':'hermes-delegation-history','label':'Kimodo 위임 접수 이력','required':[],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'receipt_history','note':'Kimodo 위임 접수 기록만 확인한다.'},
    {'command':'hermes-video-proposal','label':'동작·영상 위임 제안 읽기','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'untrusted_video_proposal','note':'서비스·모드·지시만 읽는다. 사용자가 첨부하고 기존 검증을 완료해야 한다.'},
    {'command':'hermes-delegate-video','label':'동작·영상 작업 위임','required':['request_id','service','request'],'optional':[],'effect':'enqueue','gpu':'queued','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'video_receipt','note':'DWPose와 Wan 3개 생성기의 입력·첨부 검증과 공용 GPU 대기열을 사용한다.'},
    {'command':'hermes-video-source-status','label':'동작·영상 원본 작업 상태','required':['service','job_id'],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'video_source_job_status','note':'Kimodo·DWPose·Wan의 중단 작업을 복구하지 않고 기록과 결과 세 파일 존재만 확인한다. 참조 분석 전용 결과와 재생·품질은 원 서비스에서 확인한다.'},
    {'command':'hermes-video-status','label':'동작·영상 작업 상태','required':['request_id','service'],'optional':[],'effect':'recovery_possible','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'video_status','note':'중단 작업 복구가 따를 수 있으며 검증된 동일 출처 결과만 반환한다.'},
    {'command':'hermes-video-history','label':'동작·영상 접수 이력','required':['service'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'video_receipts','note':'선택 서비스의 Hermes 접수만 표시한다.'},
    {'command':'hermes-video-cancel','label':'동작·영상 작업 중지','required':['request_id','service','job_id'],'optional':[],'effect':'cancel_request','gpu':'none','retry':'check_status','interfaces':['gui','mcp'],'result':'video_cancel','note':'접수 기록과 일치하는 작업만 중지 요청한다.'},
    {'command':'hermes-model-preparation-proposal','label':'모델 준비 제안 읽기','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'untrusted_model_preparation_proposal','note':'완료 답변에서 모델 준비 대상을 검증해 읽는다. 다운로드와 GPU 실행은 하지 않으며 별도 준비 검토·확인이 필요하다.'},
    {'command':'hermes-writer-proposal','label':'작가 요청 제안 읽기','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'untrusted_writer_proposal','note':'완료된 답변의 작가 요청을 입력 계약으로 검증하며 생성과 적용은 하지 않는다.'},
    {'command':'hermes-audio-proposal','label':'음악·효과음 위임 제안 읽기','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'untrusted_audio_proposal','note':'완료된 답변의 제안을 서비스별 입력 계약으로 검증한다. 생성은 하지 않는다.'},
    {'command':'hermes-delegate-audio','label':'음악·효과음 생성 위임','required':['request_id','service','request'],'optional':[],'effect':'enqueue','gpu':'queued','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'audio_receipt','note':'HeartMuLa와 Dasheng의 기존 입력 검증·공용 GPU 대기열을 사용한다.'},
    {'command':'hermes-audio-status','label':'음악·효과음 작업 상태','required':['request_id','service'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'audio_status','note':'검증된 동일 출처 결과 경로만 반환한다.'},
    {'command':'hermes-audio-history','label':'음악·효과음 접수 이력','required':['service'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'audio_receipts','note':'선택한 서비스의 Hermes 접수만 표시한다.'},
    {'command':'hermes-audio-cancel','label':'음악·효과음 작업 중지','required':['request_id','service','job_id'],'optional':[],'effect':'cancel_request','gpu':'none','retry':'check_status','interfaces':['gui','mcp'],'result':'audio_cancel','note':'접수 기록과 일치하는 작업만 중지 요청한다.'},
    {'command':'hermes-character-source-status','label':'과거 캐릭터 작업 상태','required':['job_id'],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'character_source_job_status','note':'폐기된 생성기의 기록과 마지막 완료 프레임 파일만 확인한다. 전체 결과·품질은 별도다.'},
    {'command':'hermes-image-source-status','label':'기존 이미지 원본 작업 상태','required':['service','job_id'],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'image_source_job_status','note':'기존 Qwen·타일 원본의 기록과 조회 시점 결과 파일 존재를 복구 없이 확인한다. 건물은 빌보드 이력을 공유한다.'},
    {'command':'hermes-flux-source-status','label':'FLUX 원본 작업 상태','required':['service','job_id'],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'flux_source_job_status','note':'복구 없이 기록과 조회 시점의 이미지 파일 존재를 확인한다. 이미지 내용과 프로세스 생존은 별도다.'},
    {'command':'hermes-delegate-flux-profile','label':'FLUX 프로필 생성 위임','required':['request_id','service','request'],'optional':[],'effect':'enqueue','gpu':'queued','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'flux_profile_receipt','note':'8개 이미지 프로필과 별도 표정 생성기의 참조·크기 검증과 GPU 대기열을 사용한다.'},
    {'command':'hermes-flux-profile-status','label':'FLUX 프로필 작업 상태','required':['request_id','service'],'optional':[],'effect':'recovery_possible','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'flux_profile_status','note':'해당 생성기의 작업 복구 동작이 따를 수 있다.'},
    {'command':'hermes-flux-profile-history','label':'FLUX 프로필 접수 이력','required':['service'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'flux_profile_history','note':'서비스가 일치하는 Hermes 접수만 표시한다.'},
    {'command':'hermes-flux-profile-cancel','label':'FLUX 프로필 작업 중지','required':['request_id','service','job_id'],'optional':[],'effect':'cancel_request','gpu':'none','retry':'check_status','interfaces':['gui','mcp'],'result':'flux_profile_cancel','note':'접수 기록과 일치하는 프로필 작업만 중지 요청한다.'},
    {'command':'hermes-writer-apply','label':'확인한 작가 제안 적용','required':['request_id','writer_request_id','job_id','proposal_hash'],'optional':[],'effect':'write','gpu':'none','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'writer_apply_receipt','note':'전체 diff와 제안 해시를 확인해야 하며 문서 원본을 변경한다.'},
    {'command':'hermes-writer-apply-status','label':'작가 제안 적용 접수 확인','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'writer_apply_receipt','note':'접수 기록만 확인한다.'},
    {'command':'hermes-writer-apply-history','label':'작가 제안 적용 이력','required':[],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'writer_apply_history','note':'Hermes의 적용 기록만 조회한다.'},
    {'command':'hermes-delegate-writer','label':'작가 AI 작업 위임','required':['request_id','request'],'optional':[],'effect':'enqueue','gpu':'queued','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'writer_receipt','note':'문서 색인·작성·중복 검토를 기존 GPU 대기열로 접수한다.'},
    {'command':'hermes-writer-search-paths','label':'작가 검색 결과 경로 조회','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['mcp','isolated_fixed_bridge'],'result':'writer_search_paths','note':'검증된 상대 경로와 누락 여부만 반환한다. 실패 작업의 검색 기록도 포함하므로 작업 성공을 뜻하지 않으며, 파일 접근 시 문서 루트 포함 여부를 다시 확인한다. 현재 파일이 검색 당시 문서와 같은지는 확인되지 않는다.'},
    {'command':'hermes-writer-job-material','label':'작가 검색·제안 원본 페이지','required':['job_id','section'],'optional':['offset','limit','snapshot'],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'writer_material_page','note':'원 서비스가 제공한 검색 또는 제안 JSON을 잘라내지 않고 이어 읽는다. 실행·적용이나 현재 문서 일치는 확인하지 않는다.'},
    {'command':'hermes-writer-job-review','label':'작가 작업 상태·제안 조회','required':['job_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'writer_job_review','note':'직접 생성한 작업도 조회한다. 실패·중단의 원 서비스 오류와 제한된 로그 끝부분을 포함한다. 제안 diff와 근거에도 크기 제한이 있으며 적용하지 않는다.'},
    {'command':'hermes-writer-job-search-paths','label':'작가 작업 검색 경로 조회','required':['job_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['mcp','isolated_fixed_bridge'],'result':'writer_search_paths','note':'작가 서비스에서 직접 생성한 작업을 포함한다. 현재 문서 루트 기준 상대 경로이며 검색 당시 문서 동일성은 확인되지 않는다.'},
    {'command':'hermes-writer-index-status','label':'작가 문서 색인 상태','required':[],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp','bridge'],'result':'writer_index_status','note':'조회 시점 색인 최신 상태만 확인한다. 갱신 비용이나 GPU 가용성은 확인하지 않는다.'},
    {'command':'hermes-writer-status','label':'작가 AI 작업·제안 조회','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'writer_review','note':'제안 diff와 근거는 크기 제한이 있다. 작가 AI 화면에서 전체 내용을 확인한 뒤 Hermes의 별도 적용 확인을 사용할 수 있다.'},
    {'command':'hermes-writer-reservation-recover','label':'작가 GPU 예약 정리','required':['request_id','job_id','review_sha256','outside_processes_checked'],'optional':[],'effect':'write','gpu':'none','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'writer_reservation_receipt','note':'검토한 그룹을 강제 종료한 뒤 예약을 해제한다. 별도 그룹 GPU 프로세스 확인이 필요하다.'},
    {'command':'hermes-writer-reservation-receipt','label':'작가 GPU 예약 정리 접수 확인','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'writer_reservation_receipt','note':'응답 유실 시 확인하며 미확인 작업을 재실행하지 않는다.'},
    {'command':'hermes-writer-reservation-preview','label':'작가 GPU 예약 복구 가능 여부','required':['job_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'writer_reservation_preview','note':'실행기와 작업자 신원만 검토한다. 종료·예약 삭제는 하지 않는다.'},
    {'command':'hermes-writer-cancel','label':'작가 AI 작업 중지 요청','required':['request_id','job_id'],'optional':[],'effect':'cancel_request','gpu':'none','retry':'check_status','interfaces':['gui','mcp'],'result':'writer_cancel','note':'접수와 작업 ID를 확인하고 중지를 요청한다. 실제 종료는 별도 확인한다.'},
    {'command':'hermes-writer-history','label':'작가 AI 위임 이력','required':[],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'writer_receipt_history','note':'Hermes의 작가 AI 접수만 표시한다.'},
    {'command':'hermes-translation-evidence','label':'번역 문서 근거 검색','required':['text'],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp','bridge'],'result':'translation_evidence','note':'작가 AI 색인의 근거를 반환한다. 승인 번역어나 실행 지시가 아니다.'},
    {'command':'hermes-translation-proposal','label':'번역 위임 제안 읽기','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'untrusted_translation_proposal','note':'완료된 답변의 단일 제안을 기존 번역 정책으로 검증한다. 번역을 실행하지 않는다.'},
    {'command':'hermes-delegate-translation','label':'프롬프트 번역 위임','required':['request_id','request'],'optional':[],'effect':'enqueue','gpu':'queued','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'translation_receipt','note':'기존 용어 검증과 GPU 대기열을 사용한다.'},
    {'command':'hermes-translation-status','label':'번역 작업과 검토 결과','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'translation_status','note':'결과와 용어·조건 점검을 반환한다.'},
    {'command':'hermes-translation-history','label':'번역 위임 이력','required':[],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'translation_receipt_history','note':'Hermes를 통한 번역 접수만 표시한다.'},
    {'command':'hermes-translation-cancel','label':'번역 작업 중지','required':['request_id','job_id'],'optional':[],'effect':'cancel_request','gpu':'none','retry':'check_status','interfaces':['gui','mcp'],'result':'cancel_request_status','note':'접수와 일치하는 번역 작업에 중지를 요청한다.'},
    {'command':'hermes-city-proposal','label':'도시 맵 변경 제안 읽기','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'untrusted_city_proposal','note':'완료 답변의 변경 제안만 읽으며 DB 세대·리비전과 도시 맵 검증은 별도다.'},
    {'command':'hermes-field-proposal','label':'야외 맵 셀 변경 제안 읽기','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'untrusted_field_proposal','note':'완료된 답변의 셀 제안만 읽으며 원본 리비전과 맵 검증은 별도다.'},
    {'command':'hermes-field-region', 'label':'야외 맵 영역과 배치 조회', 'required':['map'], 'optional':['column','row','width','height','offset','limit','revision'], 'effect':'read', 'gpu':'none', 'retry':'safe', 'interfaces':['mcp','isolated_fixed_bridge'], 'result':'field_region_page', 'note':'등록 에셋 원본을 DB 없이 조회한다. asset: 지문은 페이지 조회 전용이며 편집 리비전이 아니다. blocked는 실제 최종 통행 판정이 아니다.'},
    {'command':'hermes-city-source','label':'도시 맵 에셋 원본 조회','required':['map'],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'city_asset_document','note':'에셋 원본·등록부·백엔드 잠금을 확인해 도시 문서와 해시를 조회한다. DB 세대·리비전과 실행 중인 백엔드는 확인하지 않으며 저장하지 않는다.'},
    {'command':'hermes-city-load','label':'도시 맵 DB 편집 문서 조회','required':['map'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'city_map_document','note':'콘텐츠 DB 편집 문서와 세대·리비전을 읽는다. 관리 원본은 에셋 저장소이며 원본 확인에는 hermes-city-source를 사용한다. 격리 조회는 city-map과 맵 ID를 사용하며 응답은 256 KiB로 제한된다.'},
    {'command':'hermes-city-preview','label':'도시 맵 초안 검증','required':['draft'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'city_preview_token','note':'원장 세대·리비전과 공간 검증 후 로컬 임시 초안을 남긴다. source_alignment는 현재 도시 DB 문서와 에셋 원본·등록부·잠금의 조회 시점 비교다. 실행 중인 서비스 반영은 확인하지 않으며 신규 저장은 중단된다.'},
    {'command':'hermes-city-save','label':'도시 맵 초안 저장','required':['request_id','draft','token'],'optional':[],'effect':'write','gpu':'none','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'city_save_receipt','note':'기존 콘텐츠 DB 저장은 도시 맵 원본·등록부와 백엔드 잠금의 동기화 저장이 없어 신규 접수를 차단한다. 기존 접수 조회와 동일 요청 재조회는 유지한다.'},
    {'command':'hermes-city-receipt','label':'도시 맵 저장 확인','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'city_save_receipt','note':'저장 접수만 확인한다.'},
    {'command':'hermes-city-history','label':'도시 맵 저장 이력','required':[],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'city_save_history','note':'최근 접수 중 손상된 기록은 제외한다.'},
    {'command':'hermes-field-receipt', 'label':'야외 맵 저장 접수 확인', 'required':['request_id'], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'field_save_receipt', 'note':'원본은 변경하지 않는다. 확인 불가 시 원본을 살펴본다.'},
    {'command':'hermes-field-history', 'label':'야외 맵 저장 이력', 'required':[], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'field_save_history', 'note':'최근 접수 기록만 읽으며 손상된 기록은 제외한다.'},
    {'command':'hermes-field-load', 'label':'야외 맵 편집 원본 읽기', 'required':['map'], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'field_map_document', 'note':'기존 맵 편집기의 원본·리비전을 읽으며 로컬 잠금 파일을 만들 수 있다.'},
    {'command':'hermes-field-preview', 'label':'야외 맵 초안 검증', 'required':['draft'], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'field_preview_token', 'note':'기존 편집 검증을 사용하며 로컬 임시 초안 기록을 생성한다. save_available이 false면 저장이 차단되며 save_block_reason은 DB 모드(database), 이전 저장 중단(interrupted) 또는 미제공이다. null과 사유 미제공은 확인 불가이며 false와 null 모두 신규 저장을 보류한다. 사유가 database일 때 타일·지형과 등록 원본의 조회 시점 비교를 반환하며 실행 중인 서비스 반영은 확인하지 않는다. true도 이후 저장 성공을 보장하지 않는다.'},
    {'command':'hermes-field-save', 'label':'야외 맵 초안 저장', 'required':['request_id','draft','token'], 'optional':[], 'effect':'write', 'gpu':'none', 'retry':'request_id_or_unknown', 'interfaces':['gui','mcp'], 'result':'field_save_receipt', 'note':'파일 모드에서는 원본·등록부·백엔드 잠금과 카탈로그를 갱신한다. DB 모드의 기존 저장은 콘텐츠 DB만 갱신하므로 원본과 소비자 동기 저장이 구현될 때까지 원 서비스에서 차단한다. 기존 접수의 결과 확인은 별도다.'},
    {'command':'hermes-map-database-receipt','label':'맵 DB 변경 접수 확인','required':['database_request_id','request_sha256'],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'map_database_receipt','note':'DB 요청 ID와 원본 요청 SHA-256의 일치만 확인한다. 파일 동기화나 not_found 이후 재접수 안전은 보장하지 않는다.'},
    {'command':'hermes-content-database-status', 'label':'콘텐츠 DB와 원장 반영 상태', 'required':[], 'optional':[], 'effect':'read', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp','isolated_fixed_bridge'], 'result':'content_database_generation_status', 'note':'콘텐츠 서비스의 DB 세대와 원장 반영 상태를 조회한다. 연결 실패는 미확인이다.'},
    {'command':'hermes-model-prepare-history', 'label':'모델 준비 접수 이력', 'required':[], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'preparation_receipt_history', 'note':'최근 접수 기록을 읽는다. 손상된 기록은 제외한다.'},
    {'command':'hermes-model-prepare', 'label':'모델 준비 요청', 'required':['request_id','service'], 'optional':[], 'effect':'enqueue', 'gpu':'service_dependent', 'retry':'request_id_or_unknown', 'interfaces':['gui','mcp'], 'result':'preparation_receipt', 'note':'다운로드·디스크 사용 및 서비스별 GPU 작업이 발생할 수 있다. Hermes 모델 사용 충돌이나 준비 상태 확인 불가가 접수 전 확인되면 blocked를 반환하고 기록하지 않는다. 응답 불명확과 구분하며 완료는 별도 확인한다.'},
    {'command':'hermes-capture-proposal','label':'검수 캡처 제안 읽기','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'untrusted_capture_proposal','note':'완료된 대화의 캡처 설정과 맵 등록 여부를 읽는다. 확인 불가와 미등록을 구분한다. 캡처 실행은 지원하지 않는다.'},
    {'command':'hermes-capture-status','label':'검수 캡처 접수 상태 확인','required':['request_id','service'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'capture_receipt_status','note':'운영 이력의 검증된 대기 항목과 기존 캡처 접수만 확인하며 캡처 실행은 아직 지원하지 않는다.'},
    {'command':'hermes-model-prepare-status', 'label':'모델 준비 접수 확인', 'required':['request_id','service'], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'preparation_receipt', 'note':'요청 ID·서비스·접수 기록만 확인한다. 응답 당시 준비 상태는 현재 완료 상태가 아니며 모델 상태를 별도 조회한다.'},
    {'command':'hermes-building-proposal','label':'건물 앵커 제안 읽기','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'untrusted_building_proposal','note':'완료된 답변의 앵커 제안만 읽고 현재 세대·속성·사용 맵 검증은 별도로 수행한다.'},
    {'command':'hermes-building-preview','label':'건물 앵커 변경 검토','required':['draft'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'building_anchor_review','note':'앵커만 검토한다. 현재 세대·속성·사용 맵을 확인한다.'},
    {'command':'hermes-building-save','label':'건물 앵커 저장','required':['request_id','draft','review_sha256'],'optional':[],'effect':'write','gpu':'none','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'building_anchor_receipt','note':'검토를 재확인하고 세대 조건부로 저장한다. 응답 유실은 확인 필요다.'},
    {'command':'hermes-building-receipt','label':'건물 앵커 저장 접수 조회','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'building_anchor_receipt','note':'미확인 상태는 자동 재실행하지 않는다.'},
    {'command':'hermes-building-catalog', 'label':'건물 에셋 목록 조회', 'required':[], 'optional':['query','offset','limit','snapshot'], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp','isolated_fixed_bridge'], 'result':'building_catalog_page', 'note':'콘텐츠 서비스가 필요하다. 이미지 픽셀과 표시 크기를 구분한다.'},
    {'command':'hermes-world-map', 'label':'월드맵 연결 조회', 'required':[], 'optional':['map'], 'effect':'read', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp','isolated_fixed_bridge'], 'result':'validated_world_map', 'note':'등록된 원본·썸네일과 맵 간 연결을 검증한다. 표시 좌표는 실제 맵 좌표가 아니다.'},
    {'command':'hermes-billboard-proposal','label':'빌보드 변경 제안 읽기','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'untrusted_billboard_proposal','note':'완료 답변의 현재값과 제안값만 읽으며 원본 조회와 검토가 필요하다.'},
    {'command':'hermes-sprite-clip-playback','label':'등록 클립 재생 검수','required':['draft','token','review_sha256','clip'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'sprite_clip_gif','note':'등록된 프레임 순서·시간·반복으로 검수하며 GIF 시간은 10ms 단위다.'},
    {'command':'hermes-sprite-playback','label':'스프라이트 앵커 재생 검수','required':['draft','token','review_sha256','fps'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'sprite_preview_gif','note':'기존 GIF 검수기로 전체 프레임을 균일 FPS로 재생한다. 임시 시트와 GIF를 생성한다.'},
    {'command':'hermes-sprite-proposal','label':'스프라이트 앵커 제안 읽기','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'untrusted_sprite_proposal','note':'완료된 답변의 앵커 제안만 읽으며 원본 검증과 이미지·재생 검토가 별도다.'},
    {'command':'hermes-sprite-preview','label':'스프라이트 앵커 변경 검토','required':['draft'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'sprite_anchor_preview','note':'원본 확인 후 임시 시트 출력을 생성하며 재패킹 결과를 표시한다.'},
    {'command':'hermes-sprite-pending-status','label':'스프라이트 중단 저장 확인','required':[],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'sprite_pending_status','note':'중단 표시의 대상·백업 해시를 비교한다. 자동 복구하지 않는다.'},
    {'command':'hermes-sprite-save','label':'스프라이트 앵커 저장','required':['request_id','draft','token','review_sha256'],'optional':[],'effect':'write','gpu':'none','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'sprite_anchor_receipt','note':'검토 후 시트·좌표맵·등록부·프런트 잠금을 갱신한다. 사전 상태가 중단·사용 중·확인 불가면 접수 전 blocked를 반환한다.'},
    {'command':'hermes-sprite-receipt','label':'스프라이트 저장 접수 확인','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'sprite_anchor_receipt','note':'응답 유실 시 자동으로 다시 실행하지 않는다.'},
    {'command':'hermes-sprite-catalog','label':'등록 스프라이트 검색','required':[],'optional':['query','offset','limit'],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'sprite_catalog','note':'에셋 등록부와 애니메이션 메타데이터 해시를 확인한다.'},
    {'command':'hermes-sprite-detail','label':'스프라이트 프레임·앵커 조회','required':['path'],'optional':['offset','limit','snapshot'],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'sprite_sheet','note':'등록 원본 이미지와 메타데이터 해시를 확인한다. 픽셀은 반환하지 않는다.'},
    {'command':'hermes-effect-proposal','label':'이펙트 좌표 제안 읽기','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'untrusted_effect_proposal','note':'완료 답변의 좌표만 읽는다. 원본 검증과 시각 검수는 별도다.'},
    {'command':'hermes-effect-register-preview','label':'이펙트 신규 등록 검토','required':['draft'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'effect_registration_review','note':'등록 원본·PNG와 웨이포인트 애니메이션 규격을 검토한다.'},
    {'command':'hermes-effect-register','label':'이펙트 신규 등록','required':['request_id','draft','review_sha256'],'optional':[],'effect':'write','gpu':'none','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'effect_registration_receipt','note':'신규 ID만 등록한다. 응답이 불확실하면 자동 재등록하지 않는다.'},
    {'command':'hermes-effect-register-receipt','label':'이펙트 등록 접수 확인','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'effect_registration_receipt','note':'저장 시점 DB 세대와 불확실 상태를 확인한다.'},
    {'command':'hermes-waypoint-preview','label':'웨이포인트 교체 검토','required':['draft'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'waypoint_replacement_review','note':'기존 revision과 새 이미지·메타데이터 등록 및 해시를 확인한다.'},
    {'command':'hermes-waypoint-replace','label':'웨이포인트 교체','required':['request_id','draft','review_sha256'],'optional':[],'effect':'write','gpu':'none','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'waypoint_replacement_receipt','note':'기존 ID를 제거하므로 변경과 실제 사용 맵을 확인해야 한다.'},
    {'command':'hermes-waypoint-receipt','label':'웨이포인트 교체 접수 확인','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'waypoint_replacement_receipt','note':'불확실한 요청은 자동으로 재실행하지 않는다.'},
    {'command':'hermes-effect-preview','label':'이펙트 좌표 변경 검토','required':['draft'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'effect_edit_preview','note':'등록 원본과 revision을 재조회하여 좌표 변경을 검증한다.'},
    {'command':'hermes-effect-save','label':'이펙트 공용 좌표 저장','required':['request_id','draft','token'],'optional':[],'effect':'write','gpu':'none','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'effect_edit_receipt','note':'확인한 좌표만 콘텐츠 DB에 조건부 저장한다.'},
    {'command':'hermes-effect-receipt','label':'이펙트 저장 접수 확인','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'effect_edit_receipt','note':'응답 유실 시 자동 재접수하지 않는다.'},
    {'command':'hermes-effect-catalog','label':'맵 이펙트 목록','required':[],'optional':['query','offset','limit'],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'effect_catalog','note':'콘텐츠 DB와 로컬 편집 잠금이 필요하다.'},
    {'command':'hermes-effect-detail','label':'맵 이펙트 좌표 조회','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'effect_detail','note':'등록 이미지 검증과 좌표를 읽지만 이미지나 로컬 경로는 반환하지 않는다.'},
    {'command':'hermes-billboard-load','label':'빌보드 속성 불러오기','required':['texture'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'billboard_edit_source','note':'기존 카탈로그에서 현재 속성과 revision을 읽는다.'},
    {'command':'hermes-billboard-preview','label':'빌보드 변경 검증','required':['draft'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'billboard_edit_preview','note':'변경 전후·사용 맵 경고를 확인한다.'},
    {'command':'hermes-billboard-save','label':'빌보드 변경 저장','required':['request_id','draft','token','review_sha256'],'optional':[],'effect':'write','gpu':'none','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'billboard_edit_receipt','note':'검토 결과를 다시 확인한 후 기존 저장 계약을 호출한다.'},
    {'command':'hermes-billboard-receipt','label':'빌보드 저장 접수 확인','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'billboard_edit_receipt','note':'응답 유실 시 자동 재저장하지 않는다.'},
    {'command':'hermes-billboard-catalog', 'label':'빌보드 카탈로그 조회', 'required':[], 'optional':['category','query','offset','limit'], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp','isolated_fixed_bridge'], 'result':'billboard_catalog_page', 'note':'공용 속성과 검수 여부를 구분한다. 로컬 잠금 파일 생성이 따를 수 있다.'},
    {'command':'hermes-model-readiness', 'label':'모델 서비스 준비 상태', 'required':['service'], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp','isolated_fixed_bridge'], 'result':'model_readiness', 'note':'상태 조회에 로컬 잠금 파일 생성이 따를 수 있다. 실행과 해시 검증은 별도다.'},
    {'command':'hermes-flux-proposal', 'label':'FLUX 제안 읽기', 'required':['id'], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'validated_untrusted_proposal', 'note':'텍스트 이미지 제안은 자동 실행되지 않는다.'},
    {'command':'hermes-flux-delegation-history', 'label':'FLUX 위임 이력', 'required':[], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'receipt_history', 'note':'손상되거나 서비스 확인이 불가능한 기록은 제외된다.'},
    {'command':'hermes-delegate-flux-image', 'label':'FLUX 이미지 생성 위임', 'required':['request_id','request'], 'optional':[], 'effect':'enqueue', 'gpu':'queued', 'retry':'request_id_or_unknown', 'interfaces':['gui','mcp'], 'result':'receipt_and_job_id', 'note':'사용자의 생성 요청을 기존 입력 검증과 공용 GPU 대기열로 접수한다.'},
    {'command':'hermes-flux-delegation-status', 'label':'FLUX 위임 작업 상태', 'required':['request_id'], 'optional':[], 'effect':'recovery_possible', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'receipt_and_job_status', 'note':'작업 상태 조회에 기존 서비스의 복구가 따를 수 있다.'},
    {'command':'hermes-flux-delegation-cancel', 'label':'FLUX 위임 작업 중지', 'required':['request_id','job_id'], 'optional':[], 'effect':'cancel_request', 'gpu':'none', 'retry':'check_status', 'interfaces':['gui','mcp'], 'result':'cancel_request_status', 'note':'일치하는 FLUX 작업만 중지 요청하며 실제 종료는 별도다.'},
    {'command':'hermes-service-registration', 'label':'관리 서비스 등록 목록', 'required':[], 'optional':['query','offset','limit'], 'effect':'read', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp','isolated_fixed_bridge'], 'result':'gateway_registered_services', 'note':'등록은 실행 가능·권한·Hermes 연결을 보증하지 않는다.'},
    {'command':'hermes-model-download-status','label':'모델 다운로드 상태 조회','required':[],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'model_download_status','note':'오래된 기록을 삭제하지 않고 조회한다. 외부 다운로드와 PID 재사용은 확인하지 않는다.'},
    {'command':'hermes-model-inventory', 'label':'모델 파일 보유량 조회', 'required':[], 'optional':[], 'effect':'read', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp','isolated_fixed_bridge'], 'result':'model_file_counts_and_sizes', 'note':'파일 존재는 준비 완료나 해시 검증을 뜻하지 않는다.'},
    {'command':'hermes-expression-catalog','label':'표정 프리셋 검색','required':[],'optional':['query','offset','limit','snapshot'],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'expression_catalog','note':'표정 생성기의 등록 ID와 한국어 이름만 제공한다.'},
    {'command':'hermes-service-receipt','label':'서비스 접수 ID 조회','required':['request_id','service'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'service_receipt','note':'요청 ID·서비스·접수 상태만 확인한다. 원 서비스의 작업 상태·결과·생존 여부는 확인하지 않으며 상태 복구나 생성을 실행하지 않는다. Kimodo는 별도 접수 확인을 사용한다.'},
    {'command':'hermes-priority-submit','label':'GPU 대기 작업 우선 실행','required':['request_id','service','id','ticket_revision'],'optional':[],'effect':'write','gpu':'none','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'priority_receipt','note':'확인한 티켓을 대기열 맨 앞으로 옮긴다. 결과 불명 시 같은 접수 기록을 확인하며 재실행하지 않는다.'},
    {'command':'hermes-priority-receipt','label':'GPU 우선 실행 접수 조회','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'priority_receipt','note':'우선 실행 접수 기록을 읽으며 순서는 변경하지 않는다.'},
    {'command':'hermes-priority-preview','label':'GPU 우선 실행 대상 확인','required':['service','id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'priority_preview','note':'원 서비스가 확인된 유일한 대기 티켓을 조회하며 순서는 변경하지 않는다.'},
    {'command':'hermes-management-status', 'label':'관리 상태 조회', 'required':[], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp','isolated_fixed_bridge'], 'result':'model_gpu_queue_and_recent_jobs', 'note':'최근 작업 조회에 로컬 잠금이 따른다. Kimodo 활성 상태는 기록 기준이며 GPU 관측은 캐시될 수 있다.'},
    {'command':'hermes-session-submit', 'label':'대화·격리 작업 접수', 'required':['session_id','request_id','prompt'], 'optional':['verification_modules'], 'effect':'enqueue', 'gpu':'exclusive', 'retry':'request_id', 'interfaces':['gui','mcp'], 'result':'hermes_job_id', 'note':'동일 ID와 입력의 재접수만 허용한다. 배타 예약은 관리도구 대기열에만 적용되며 외부 GPU 작업과 성능 경합이 가능하다.'},
    {'command':'hermes-kimodo-keyframe-validate','label':'Kimodo 키프레임 배치 검증','required':['keyframes','frames'],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'kimodo_keyframe_validation','note':'원본과 골격 구조를 검증한다. 접수 시 다시 검증한다.'},
    {'command':'hermes-kimodo-source-frame','label':'Kimodo 원본 프레임 검토','required':['job_id','attempt_id','frame'],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'kimodo_source_frame','note':'완료된 현재 시도의 프레임 PNG 시그니처와 해시를 확인한다. 모션·골격 및 저장 가능성은 검증하지 않는다.'},
    {'command':'hermes-kimodo-keyframe-preview','label':'Kimodo 키프레임 검증 미리보기','required':['keyframe_id'],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'kimodo_keyframe_preview','note':'기존 서비스의 모션·골격·이미지 해시 검증을 사용한다.'},
    {'command':'hermes-kimodo-keyframe-source-review','label':'Kimodo 원본 키프레임 검토','required':['job_id','attempt_id','frame','tag'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'kimodo_keyframe_source_review','note':'원본 스냅샷과 검토 해시, 기존 대화 접수 확인 상태를 조회한다. 로컬 잠금이 생길 수 있다.'},
    {'command':'hermes-kimodo-keyframe-save','label':'Kimodo 검토 키프레임 저장','required':['request_id','job_id','attempt_id','frame','tag','review_sha256'],'optional':[],'effect':'write','gpu':'none','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'kimodo_keyframe_receipt','note':'검토한 원본만 저장하며 응답 유실 시 자동 재저장하지 않는다.'},
    {'command':'hermes-kimodo-keyframe-receipt','label':'Kimodo 키프레임 저장 접수','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'kimodo_keyframe_receipt','note':'완료·불확실·미접수를 구분한다.'},
    {'command':'hermes-kimodo-keyframes','label':'Kimodo 키프레임 목록','required':[],'optional':['query','offset','limit','snapshot'],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'kimodo_keyframe_catalog','note':'기록의 ID·태그·원본 프레임만 제공한다. 다음 페이지에 snapshot을 전달하면 목록 변경을 감지한다. 확인값 없는 이전 페이지는 변경 여부를 확인할 수 없다. 해시와 실제 동작은 Kimodo에서 확인한다.'},
    {'command':'hermes-kimodo-proposal', 'label':'Kimodo 제안 읽기', 'required':['id'], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'validated_untrusted_proposal', 'note':'제안은 실행되지 않는다.'},
    {'command':'hermes-delegate-kimodo', 'label':'Kimodo 생성 위임', 'required':['request_id','request'], 'optional':[], 'effect':'enqueue', 'gpu':'queued', 'retry':'request_id_or_unknown', 'interfaces':['gui','mcp'], 'result':'receipt_and_job_id', 'note':'화면은 입력과 GPU 사용 확인 후 접수한다. 응답 불확실 시 재실행하지 않는다.'},
    {'command':'hermes-delegation-status', 'label':'위임 접수 확인', 'required':['request_id'], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'receipt', 'note':'Kimodo 접수 ID·서비스·접수 상태를 확인한다. 원 작업의 상태·생존·결과는 확인하지 않고 상태 복구나 생성을 실행하지 않는다.'},
    {'command':'hermes-delegation-job-status', 'label':'Kimodo 작업 상태', 'required':['request_id'], 'optional':[], 'effect':'recovery_possible', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'receipt_and_job_status', 'note':'MCP는 접수 ID로 조회한다. 화면은 같은 Kimodo 상태 명령을 작업 ID로 조회하며 중단 작업 복구가 발생할 수 있다.'},
    {'command':'hermes-delegation-cancel', 'label':'위임 작업 중지', 'required':['request_id','job_id'], 'optional':[], 'effect':'cancel_request', 'gpu':'none', 'retry':'check_status', 'interfaces':['gui','mcp'], 'result':'cancel_request_status', 'note':'확인한 작업에 중지를 요청하며 실제 종료는 별도다.'},
    {'command':'hermes-diff', 'label':'격리 변경 전체 조회', 'required':['id','offset','limit'], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'base64_byte_chunk', 'note':'종료된 작업의 바이트 조각을 읽는다.'},
)


HERMES_FIELD_SCHEMAS = {
    'text': {'type':'string','minLength':1,'maxLength':6000},
    'expected_resume_fingerprint': {'type':'string','pattern':'^[a-f0-9]{64}$'},
    'keyframes': {'type':'array','minItems':1,'validation':'Kimodo 키프레임 배치 계약'},
    'frames': {'type':'integer','minimum':1,'note':'생성할 총 출력 프레임'},
    'keyframe_id': {'type':'string','pattern':'^[a-f0-9]{32}$'},
    'writer_request_id': {'type':'string','pattern':'^[A-Za-z0-9_-]{8,80}$'},
    'proposal_hash': {'type':'string','pattern':'^[a-f0-9]{64}$'},
    'ticket_revision': {'type':'string','pattern':'^[a-f0-9]{64}$'},
    'column': {'type':'integer','minimum':0,'maximum':10000},
    'row': {'type':'integer','minimum':0,'maximum':10000},
    'width': {'type':'integer','minimum':1,'maximum':16},
    'height': {'type':'integer','minimum':1,'maximum':16},
    'revision': {'type':'string','maxLength':4096},
    'clip': {'type':'string','minLength':1,'maxLength':200},
    'fps': {'type':'integer','enum':[4,6,8,12,16,24,30]},
    'section': {'type':'string'},
    'snapshot': {'type':'string','pattern':'^[a-f0-9]{64}$','note':'후속 프레임 페이지에 첫 조회에서 받은 값'},
    'path': {'type':'string','maxLength':512},
    'texture': {'type':'string','pattern':'^[a-z][a-z0-9-]{0,95}$'},
    'review_sha256': {'type':'string','pattern':'^[a-f0-9]{64}$'},
    'draft': {'type':'object','validation':'map-assets map-edit-preview'},
    'token': {'type':'string','pattern':'^[a-f0-9]{64}$'},
    'map': {'type':'string','pattern':'^[a-z0-9][a-z0-9-]{0,95}$'},
    'category': {'type':'string','enum':['vegetation','herbaceous','large-trees','rocks-minerals','props']},
    'query': {'type':'string','maxLength':100,'pattern':r'^[^\x00-\x1f]*$'},
    'status': {'type':'string', 'note':'명령별 기록 상태'},
    'service': {'type':'string', 'note':'명령별 관리 서비스 식별자'},
    'session_id': {'type':'string', 'pattern':'^[0-9a-f]{32}$'},
    'outside_processes_checked': {'type':'boolean','const':True,'note':'별도 그룹 GPU 프로세스 확인'},
    'request_id': {'type':'string', 'pattern':'^[A-Za-z0-9_-]{8,80}$'},
    'database_request_id': {'type':'string','minLength':1,'maxLength':180},
    'request_sha256': {'type':'string','pattern':'^[a-f0-9]{64}$'},
    'prompt': {'type':'string', 'minLength':1, 'maxLength':8000, 'pattern':r'\S'},
    'verification_modules': {'type':'array', 'items':{'type':'string'}, 'maxItems':5, 'uniqueItems':True, 'note':'공용 회귀 모듈 허용 목록'},
    'id': {'type':'string', 'pattern':'^\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}-\\d{2}-[a-f0-9]{8}$'},
    'attempt_id': {'type':'string','pattern':'^[a-f0-9]{32}$'},
    'tag': {'type':'string','minLength':1,'maxLength':80,'note':'앞뒤 공백을 제거한 값이 비어 있거나 제어 문자를 포함하면 거부한다.'},
    'frame': {'type':'integer','minimum':1,'maximum':1000},
    'job_id': {'type':'string', 'pattern':'^\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}-\\d{2}-[a-f0-9]{8}$'},
    'offset': {'type':'integer', 'minimum':0},
    'limit': {'type':'integer', 'minimum':1, 'maximum':262144},
    'request': {'type':'object', 'validation':'generators.kimodo.contracts.validate_kimodo_request'},
}


def list_hermes_capability_catalog():
    """경로·방식은 공용 게이트웨이 등록을 원본으로 사용한다."""
    from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, MANAGEMENT_COMMAND_ROUTES
    current_catalog_records = []
    for current_capability_record in HERMES_CAPABILITY_RECORDS:
        current_command_name = current_capability_record['command']
        if current_command_name not in MANAGEMENT_SERVICE_COMMANDS['hermes-agent']:
            raise ValueError('등록되지 않은 Hermes 관리 명령: ' + current_command_name)
        current_method_value, current_route_suffix = MANAGEMENT_COMMAND_ROUTES[current_command_name]
        current_field_names = current_capability_record['required'] + current_capability_record['optional']
        current_payload_schema = {'type':'object', 'required':current_capability_record['required'], 'properties':{current_field_name:HERMES_FIELD_SCHEMAS[current_field_name] for current_field_name in current_field_names}, 'additionalProperties':False}
        if current_command_name == 'hermes-kimodo-keyframe-validate':
            from tools.review.domains.kimodo.keyframe_storage import KIMODO_KEYFRAME_LIMIT
            current_payload_schema['properties']['keyframes'] = {'type':'array','minItems':1,'maxItems':KIMODO_KEYFRAME_LIMIT,'items':{'type':'object','required':['id','frame'],'properties':{'id':{'type':'string','pattern':'^[a-f0-9]{32}$'},'frame':{'type':'integer','minimum':1}},'additionalProperties':False},'note':'출력 프레임은 frames 이하이며 서로 중복될 수 없다.'}
        if current_command_name=='hermes-cleanup-preview':
            current_payload_schema['properties']['service']={'type':'string','enum':[current_name for current_name,current_commands in MANAGEMENT_SERVICE_COMMANDS.items() if 'history-reset-preview' in current_commands]}
        if current_command_name in ('hermes-video-resume-preview','hermes-video-resume-submit'):
            current_payload_schema['properties']['service']={'type':'string','enum':['dwpose','wan22-animate2','wan22-vace','wan22-fun-control']}
        if current_command_name in ('hermes-flux-resume-preview','hermes-flux-resume-submit'):
            from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
            current_payload_schema['properties']['service']={'type':'string','enum':list(FLUX_IMAGE_PROFILE_RECORDS)}
        if current_command_name in ('hermes-audio-source-history','hermes-generator-source-history'):
            current_payload_schema['properties']['query']={'type':'string','maxLength':80,'pattern':'^[A-Za-z0-9_-]*$','note':'작업 ID 일부만 검색한다.'}
        if current_command_name == 'hermes-service-registration':
            current_payload_schema['properties']['limit'] = {'type':'integer','minimum':1,'maximum':10}
        if current_command_name in ('hermes-submit','hermes-session-submit'):
            from tools.review.tests.run_management_audit import MANAGEMENT_AUDIT_MODULES
            current_payload_schema['properties']['verification_modules'] = {'type':'array','items':{'type':'string','enum':list(MANAGEMENT_AUDIT_MODULES)},'maxItems':5,'uniqueItems':True,'note':'공용 회귀 실행기에 등록된 모듈만 지정한다.'}
        if current_command_name == 'hermes-submit':
            current_payload_schema['properties']['prompt'] = {'type':'string','minLength':1,'maxLength':12000,'pattern':r'\S'}
        if current_command_name == 'hermes-effect-detail':
            current_payload_schema['properties']['id'] = {'type':'string','pattern':'^[a-z][a-z0-9-]{0,95}$'}
        if current_command_name in ('hermes-billboard-catalog', 'hermes-building-catalog', 'hermes-effect-catalog', 'hermes-sprite-catalog', 'hermes-sprite-detail', 'hermes-kimodo-keyframes', 'hermes-audio-source-history', 'hermes-generator-source-history', 'hermes-expression-catalog'):
            current_payload_schema['properties']['limit'] = {'type':'integer','minimum':1,'maximum':30}
        if current_command_name == 'hermes-billboard-catalog':
            current_payload_schema['properties']['category'] = {'anyOf':[HERMES_FIELD_SCHEMAS['category'],{'type':'null'}]}
        if current_command_name in ('hermes-building-catalog', 'hermes-sprite-detail', 'hermes-kimodo-keyframes', 'hermes-audio-source-history', 'hermes-generator-source-history'):
            current_payload_schema['properties']['snapshot'] = {'anyOf':[HERMES_FIELD_SCHEMAS['snapshot'],{'type':'null'}]}
        if current_command_name == 'hermes-building-catalog':
            current_payload_schema['properties']['snapshot'] = {'anyOf':[{'type':'string','pattern':'^[a-f0-9]{64}$','note':'후속 건물 목록 페이지에 첫 조회에서 받은 값'},{'type':'null'}]}
        if current_command_name in ('hermes-sprite-detail','hermes-audio-source-history','hermes-generator-source-history','hermes-session-view','hermes-expression-catalog','hermes-history'):
            current_payload_schema['allOf'] = [{'if':{'required':['offset'],'properties':{'offset':{'minimum':1}}},'then':{'required':['snapshot'],'properties':{'snapshot':HERMES_FIELD_SCHEMAS['snapshot']}}}]
        if current_command_name == 'hermes-session-list':
            current_payload_schema['properties']['limit'] = {'type':'integer','minimum':1,'maximum':30}
            current_payload_schema['properties']['query'] = {'type':'string','maxLength':100,'pattern':r'^[^\x00-\x1f]*$','note':'세션 ID 또는 사용자 지시의 일부; 지시 원문은 목록에 포함되지 않는다.'}
            current_payload_schema['properties']['snapshot'] = {'type':'string','pattern':'^[a-f0-9]{64}$'}
            current_payload_schema['allOf'] = [{'if':{'required':['offset'],'properties':{'offset':{'minimum':1}}},'then':{'required':['snapshot']}}]
        if current_command_name == 'hermes-history':
            current_payload_schema['properties']['limit'] = {'type':'integer','minimum':1,'maximum':30}
            current_payload_schema['properties']['snapshot'] = {'type':'string','pattern':'^[a-f0-9]{64}$','note':'후속 작업 이력 페이지에 첫 조회에서 받은 목록 확인값'}
            from tools.review.domains.hermes_agent.history_catalog import HERMES_HISTORY_STATUS_LABELS
            current_payload_schema['properties']['status'] = {'type':'string','enum':['전체',*HERMES_HISTORY_STATUS_LABELS]}
        if current_command_name == 'hermes-writer-job-material':
            current_payload_schema['properties'].update({'job_id':{'type':'string','pattern':'^[0-9]{8}-[0-9]{6}-[a-f0-9]{8}$'},'section':{'type':'string','enum':['search','proposal']},'offset':{'type':'integer','minimum':0},'limit':{'type':'integer','minimum':1,'maximum':40000},'snapshot':{'anyOf':[{'type':'string','pattern':'^[a-f0-9]{64}$'},{'type':'null'}]}})
            current_payload_schema['allOf']=[{'if':{'required':['offset'],'properties':{'offset':{'minimum':1}}},'then':{'required':['snapshot'],'properties':{'snapshot':{'type':'string','pattern':'^[a-f0-9]{64}$'}}}}]
        if current_command_name == 'hermes-field-region':
            current_payload_schema['properties']['revision'] = {'anyOf':[{'type':'string','minLength':1,'maxLength':4096},{'type':'null'}]}
            current_payload_schema['allOf'] = [{'if':{'required':['offset'],'properties':{'offset':{'minimum':1}}},'then':{'required':['revision'],'properties':{'revision':{'type':'string','minLength':1,'maxLength':4096}}}}]
            current_payload_schema['properties']['offset'] = {'type':'integer','minimum':0,'maximum':100000}
            current_payload_schema['properties']['limit'] = {'type':'integer','minimum':1,'maximum':30}
        if current_command_name in ('hermes-writer-cancel','hermes-writer-reservation-preview','hermes-writer-reservation-recover','hermes-writer-job-search-paths','hermes-writer-job-review'):
            current_payload_schema['properties']['job_id'] = {'type':'string','pattern':'^[0-9]{8}-[0-9]{6}-[a-f0-9]{8}$'}
        if current_command_name in ('hermes-generator-reservation-inspect','hermes-generator-reservation-recover'):
            current_payload_schema['properties']['job_id'] = {'type':'string','pattern':'^[A-Za-z0-9_-]{1,80}$','note':'유일한 예약과 원 서비스 경로를 별도로 검증한다.'}
        if current_command_name == 'hermes-writer-apply':
            current_payload_schema['properties']['job_id'] = {'type':'string','pattern':'^[0-9]{8}-[0-9]{6}-[a-f0-9]{8}$'}
        if current_command_name in ('hermes-building-preview','hermes-building-save'):
            current_shadow_fields=['shadowShape','shadowOffsetColumn','shadowOffsetRow','shadowScaleX','shadowScaleY']
            current_building_properties={
                'type':'object','required':['anchorX','anchorY'],'additionalProperties':False,
                'properties':{
                    'anchorX':{'type':'number','minimum':0,'maximum':16},
                    'anchorY':{'type':'number','minimum':0,'maximum':16},
                    'displayWidthAdjustment':{'type':'integer','minimum':-2048,'maximum':2048},
                    'displayHeightAdjustment':{'type':'integer','minimum':-2048,'maximum':2048},
                    'shadowShape':{'type':'string','enum':['circle','rectangle']},
                    'shadowOffsetColumn':{'type':'number','minimum':-4,'maximum':4},
                    'shadowOffsetRow':{'type':'number','minimum':-4,'maximum':4},
                    'shadowScaleX':{'type':'number','minimum':0.1,'maximum':4},
                    'shadowScaleY':{'type':'number','minimum':0.1,'maximum':4}},
                'dependentRequired':{
                    'displayWidthAdjustment':['displayHeightAdjustment'],
                    'displayHeightAdjustment':['displayWidthAdjustment'],
                    **{current_shadow_name:[current_other_name for current_other_name in current_shadow_fields if current_other_name!=current_shadow_name] for current_shadow_name in current_shadow_fields}}}
            current_payload_schema['properties']['draft'] = {
                'type':'object','required':['texture','generation','expected','properties'],'additionalProperties':False,
                'properties':{'texture':{'type':'string','pattern':'^(?:town-[a-z0-9-]+-v[1-9][0-9]*|ward-tower-v1)$'},
                    'generation':{'type':'integer','minimum':0},'expected':current_building_properties,'properties':current_building_properties},
                'note':'현재 속성과 검토 결과는 서버가 다시 확인하며, 앵커 외 필드는 변경할 수 없습니다.'}
        if current_command_name in ('hermes-sprite-preview','hermes-sprite-save','hermes-sprite-playback','hermes-sprite-clip-playback'):
            current_payload_schema['properties']['draft'] = {'type':'object','validation':'Hermes sprite anchor and character-animation sheet-update'}
        if current_command_name in ('hermes-effect-register-preview','hermes-effect-register'):
            current_payload_schema['properties']['draft'] = {'type':'object','validation':'Hermes effect registration preview'}
        if current_command_name in ('hermes-waypoint-preview','hermes-waypoint-replace'):
            current_payload_schema['properties']['draft'] = {'type':'object','validation':'Hermes waypoint replacement preview'}
        if current_command_name in ('hermes-effect-preview','hermes-effect-save'):
            current_payload_schema['properties']['draft'] = {'type':'object','validation':'Hermes effect alignment and map-assets effect-save'}
        if current_command_name in ('hermes-billboard-preview','hermes-billboard-save'):
            current_payload_schema['properties']['draft'] = {'type':'object','validation':'map-assets asset-preview'}
        if current_command_name in ('hermes-city-preview','hermes-city-save'):
            current_payload_schema['properties']['draft'] = {'type':'object','validation':'map-assets city-edit-preview'}
        if 'service' in current_field_names and current_command_name not in ('hermes-video-resume-preview','hermes-video-resume-submit') and (current_command_name.startswith('hermes-video-') or current_command_name == 'hermes-delegate-video'):
            current_payload_schema['properties']['service'] = {'type':'string','enum':['dwpose','wan22-animate2','wan22-fun-control','wan22-vace']}
        if current_command_name == 'hermes-delegate-video':
            current_payload_schema['properties']['request'] = {'type':'object','validation':'해당 동작·영상 생성기의 validate_generation_request'}
        if 'service' in current_field_names and (current_command_name.startswith('hermes-audio-') or current_command_name == 'hermes-delegate-audio'):
            current_payload_schema['properties']['service'] = {'type':'string','enum':['music-heartmula','sfx-dasheng-audiogen']}
        if current_command_name == 'hermes-generator-source-history':
            from tools.review.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES
            current_payload_schema['properties']['service'] = {'type':'string','enum':list(SOURCE_HISTORY_GENERATOR_SERVICES)}
        if current_command_name in ('hermes-generator-reservation-inspect','hermes-generator-reservation-recover'):
            from tools.review.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES,SOURCE_HISTORY_AUDIO_SERVICES
            current_payload_schema['properties']['service'] = {'type':'string','enum':sorted((set(SOURCE_HISTORY_GENERATOR_SERVICES)|set(SOURCE_HISTORY_AUDIO_SERVICES)) - {'writer-agent'})}
        if current_command_name == 'hermes-audio-source-history':
            from generators.music.service_constants import AUDIO_SERVICE_NAMES
            current_payload_schema['properties']['service'] = {'type':'string','enum':list(AUDIO_SERVICE_NAMES)}
        if current_command_name == 'hermes-video-source-status':
            from tools.review.domains.hermes_agent.video_operations import HERMES_VIDEO_SOURCE_SERVICES
            current_payload_schema['properties']['service'] = {'type':'string','enum':list(HERMES_VIDEO_SOURCE_SERVICES)}
        if current_command_name == 'hermes-image-source-status':
            from tools.review.domains.hermes_agent.image_source_operations import IMAGE_SOURCE_SERVICES
            current_payload_schema['properties']['service'] = {'type':'string','enum':list(IMAGE_SOURCE_SERVICES)}
        if current_command_name == 'hermes-delegate-audio':
            current_payload_schema['properties']['request'] = {'type':'object','validation':'generators.music.contracts.validate_music_request'}
        if 'service' in current_field_names and (current_command_name.startswith('hermes-flux-profile-') or current_command_name in ('hermes-delegate-flux-profile','hermes-flux-source-status')):
            from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
            current_payload_schema['properties']['service'] = {'type':'string','enum':[*FLUX_IMAGE_PROFILE_RECORDS,'flux-expression']}
        if current_command_name == 'hermes-delegate-flux-profile':
            current_payload_schema['properties']['request'] = {'type':'object','validation':'해당 FLUX 이미지 프로필 또는 표정 생성기의 validate_generation_request'}
        if current_command_name in ('hermes-model-readiness','hermes-model-prepare','hermes-model-prepare-status'):
            from tools.review.common.model_management_catalog import MODEL_PREPARATION_SERVICES
            current_payload_schema['properties']['service'] = {'type':'string','enum':[current_name for _,current_name in MODEL_PREPARATION_SERVICES],'note':'등록 서비스이며 실제 준비 허용 여부는 서비스 정책과 상태를 확인한다.'}
        if current_command_name in ('hermes-priority-preview','hermes-priority-submit'):
            from tools.review.domains.hermes_agent.priority_observer import validate_hermes_priority_target
            current_priority_services=[]
            for current_service_name in sorted(MANAGEMENT_SERVICE_COMMANDS):
                try:validate_hermes_priority_target(current_service_name,'2026-11-20_12-00-00-abcdef12')
                except ValueError:continue
                current_priority_services.append(current_service_name)
            current_payload_schema['properties']['service'] = {'type':'string','enum':current_priority_services,'note':'등록과 폐기 정책만 반영한다. 대기 티켓과 원 서비스 일치는 별도로 검증한다.'}
        if current_command_name == 'hermes-capture-status':
            current_payload_schema['properties']['service'] = {'type':'string','enum':['map-review','character-review'],'note':'기존 접수 조회만 지원하며 신규 캡처를 실행하지 않는다.'}
        if current_command_name == 'hermes-service-receipt':
            from tools.review.domains.hermes_agent.delegation_store import list_hermes_service_receipt_names
            current_payload_schema['properties']['service'] = {'type':'string','enum':list(list_hermes_service_receipt_names()),'note':'Kimodo 접수는 hermes-delegation-status를 사용한다.'}
        if current_command_name == 'hermes-delegate-writer':
            current_payload_schema['properties']['request'] = {'type':'object','validation':'generators.writer_agent.jobs.validate_job_request'}
        if current_command_name == 'hermes-delegate-translation':
            current_payload_schema['properties']['request'] = {'type':'object','validation':'tools.review.domains.translation.service.validate_translation_submission'}
        if current_command_name == 'hermes-delegate-flux-image':
            current_payload_schema['properties']['request'] = {'type':'object', 'validation':'tools.review.domains.image.flux_image_generation.FluxImageGenerationManager(flux-image).validate_generation_request'}
        current_catalog_records.append({**current_capability_record, 'payload_schema':current_payload_schema, 'service':'hermes-agent', 'method':current_method_value, 'route':'/hermes-agent' + current_route_suffix})
    current_catalog_commands=[current_record['command'] for current_record in current_catalog_records]
    if len(current_catalog_commands)!=len(set(current_catalog_commands)):
        raise ValueError('Hermes 기능 목록에 중복 명령이 있습니다.')
    current_unlisted_commands=sorted(set(MANAGEMENT_SERVICE_COMMANDS['hermes-agent'])-set(current_catalog_commands))
    return {'version':1, 'records':current_catalog_records, 'unlisted_commands':current_unlisted_commands, 'note':'목록에 없는 등록 명령은 지원이나 권한이 확인된 기능으로 간주하지 않는다. 표시된 인터페이스도 별도 사용자 인증·역할 권한 체계를 의미하지 않으며 입력 검증과 확인은 기존 서비스 및 클라이언트가 수행한다. MCP 표시는 서버 구현 기준이며 현재 연결된 Codex 세션의 도구 목록이 최신인지 확인해야 한다. 새 도구가 없으면 MCP 연결을 다시 시작한다.'}


def search_hermes_capability_catalog(current_search_request):
    """격리 작업자가 공용 목록을 검색하고 제한된 페이지로 읽는다."""
    if not isinstance(current_search_request,dict) or set(current_search_request)-{'query','offset','limit'}:
        raise ValueError('기능 검색 필드 오류')
    current_query_text=current_search_request.get('query','')
    current_offset_value=current_search_request.get('offset',0)
    current_limit_value=current_search_request.get('limit',10)
    if not isinstance(current_query_text,str) or len(current_query_text)>100 or type(current_offset_value) is not int or current_offset_value<0 or type(current_limit_value) is not int or not 1<=current_limit_value<=20:
        raise ValueError('기능 검색 범위 오류')
    current_catalog_value=list_hermes_capability_catalog()
    current_query_text=current_query_text.strip().casefold()
    current_matching_records=[current_record for current_record in current_catalog_value['records'] if not current_query_text or current_query_text in ' '.join((current_record['command'],current_record['label'],current_record['note'],*current_record['interfaces'])).casefold()]
    current_page_records=current_matching_records[current_offset_value:current_offset_value+current_limit_value]
    current_next_offset=current_offset_value+len(current_page_records)
    return {'version':current_catalog_value['version'],'records':current_page_records,'total':len(current_matching_records),'offset':current_offset_value,'next_offset':current_next_offset if current_next_offset<len(current_matching_records) else None,'unlisted_commands':current_catalog_value['unlisted_commands'],'note':current_catalog_value['note']}


HERMES_SERVICE_CONDITIONAL_LIMITATIONS = {
    'map-review': [
        {'command':'capture','note':'Hermes에서는 맵 캡처를 실행하지 않는다. 원 서비스는 등록 맵을 준비하고 8770의 헤드리스 Chrome WebGL로 렌더링해 PNG와 기록 파일을 생성하며 GPU를 사용할 수 있다. 요청 ID 중복 방지 계약이 없으므로 응답이 불확실하면 결과를 확인한다.'},
    ],
    'character-review': [
        {'command':'capture','note':'Hermes에서는 캐릭터 캡처를 실행하지 않는다. 캐릭터 표현 검수 화면은 폐기되었다. 기존 원 서비스 명령은 8770의 헤드리스 Chrome WebGL로 렌더링해 PNG와 기록 파일을 생성하며 GPU를 사용할 수 있다. 요청 ID 중복 방지 계약이 없으므로 응답이 불확실하면 결과를 확인한다.'},
    ],
    'floor-tile': [
        {'command':'catalog','note':'폐기된 바닥 타일 생성기의 과거 프롬프트·기본 설정 조회다. 생성과 재개 가능 상태를 뜻하지 않으며 Hermes에서 직접 조회하지 않는다.'},
    ],
    'seamless-tile': [
        {'command':'pause','note':'원 서비스는 과거 단계별 작업에 단계 완료 후 일시정지 요청을 기록한다. 실제 중단 완료나 GPU 해제를 뜻하지 않는다. Hermes는 직접 일시정지를 지원하지 않는다.'},
    ],
    'map-assets': [
        {'command':'database-seed','note':'원 서비스는 에셋·맵·이펙트 원본을 검증해 콘텐츠 DB 초기화 요청을 보낸다. Hermes는 직접 실행하지 않는다.'},
        {'command':'database-sync','note':'원 서비스는 콘텐츠 DB 내용을 에셋 원장에 동기화하고 DB 완료 기록을 갱신한다. Hermes는 직접 실행하지 않는다.'},
        {'command':'database-snapshot','note':'호환 명령 이름이며 현재 원 서비스는 세대별 스냅샷을 만들지 않고 콘텐츠 DB 원장을 동기화한다. Hermes는 직접 실행하지 않는다.'},
        {'command':'database-status','note':'콘텐츠 DB 상태를 조회한다. Hermes 콘텐츠 DB 상태 조회는 원장·맵 원본 상태를 제한적으로 함께 확인한다.'},
        {'command':'map-edit-save','note':'야외 맵 DB 모드 신규 저장은 원본·등록부·백엔드 잠금의 동기 저장이 구현될 때까지 차단한다. 파일 모드는 검증 후 원본과 잠금을 갱신한다.'},
        {'command':'city-edit-save','note':'기존 도시 저장은 콘텐츠 DB만 갱신하므로 에셋 원본·등록부와 백엔드 잠금의 동기 저장이 구현될 때까지 원 서비스의 신규 저장을 차단한다.'},
        {'command':'building-register','note':'Hermes의 건물 앵커 편집은 건물 신규 등록을 지원하지 않는다. 등록은 원본 이미지·등록부·콘텐츠 DB와 소비자 잠금이 관련되며 원 도구에서 검토한다.'},
        {'command':'building-retire','note':'Hermes는 건물 폐기를 지원하지 않는다. 원 도구의 사용 맵·등록부·콘텐츠 DB와 소비자 상태를 확인해야 한다.'},
        {'command':'asset-crop','note':'Hermes의 빌보드 속성 편집은 이미지 크롭을 지원하지 않는다. 원본 소유권과 이미지 등록 절차를 확인한다.'},
        {'command':'asset-retire','note':'Hermes는 빌보드 에셋 폐기를 지원하지 않는다. 원 도구에서 사용 맵과 원본 등록 상태를 확인한다.'},
    ],
    'kimodo': [
        {'command':'keyframe-source-review','note':'원본 프레임·골격·모션을 저장 없이 검토하고 확인값을 반환한다. GPU를 사용하지 않는다.'},
        {'command':'keyframe-save-reviewed','note':'검토한 원본과 태그를 다시 확인해 저장한다. 요청 ID 중복 방지는 없으므로 응답 유실 시 자동 재실행하지 않는다.'},
        {'command':'keyframe-save','note':'Hermes는 키프레임 저장을 연결하지 않는다. 원 서비스는 완료된 작업의 프레임을 검증해 독립 사본을 새 ID로 저장하며 재요청 시 중복될 수 있다.'},
        {'command':'keyframe-replace','note':'Hermes는 키프레임 교체를 연결하지 않는다. 원 서비스는 새 항목을 확인하고 이전 항목을 .replaced에 보관한다.'},
        {'command':'keyframe-retire','note':'Hermes는 키프레임 폐기를 연결하지 않는다. 원 서비스는 검증한 사용자 항목을 .retired에 보관하며 제작 기준 예제는 폐기할 수 없다.'},
        {'command':'migraphx-build-status','note':'최근 빌드가 대기·실행 중이 아니면 캐시 유효성 확인을 위해 GPU 대기열에 검사 작업을 추가할 수 있다. 기록만 보려면 migraphx-build-observe 또는 Hermes 빌드 기록 조회를 사용한다.'},
        {'command':'migraphx-build','note':'캐시 검사와 GPU 빌드를 접수할 수 있으며 요청 ID 기반 중복 방지가 없다. 실행 접수 후 응답이 불확실하면 재요청 전에 원 서비스의 빌드 기록과 대기열을 확인한다. Hermes는 빌드 실행을 연결하지 않는다.'},
    ],
    'character-animation': [
        {'command':'catalog','note':'이전 생성기 설정의 모션·캐릭터와 고정 프롬프트를 읽는다. 생성기는 폐기됐으며 Hermes의 등록 스프라이트 카탈로그와 다르다.'},
        {'command':'status','note':'작업 상태·입력·최근 로그와 결과를 파일에서 읽는다. 로컬 경로가 포함될 수 있고 기록 상태는 프로세스 생존 확인이 아니다. Hermes에서 직접 조회하지 않는다.'},
        {'command':'logs','note':'해당 작업의 worker.log 전체를 읽는다. 비공개 경로·내용과 큰 출력이 포함될 수 있어 Hermes에서 직접 전달하지 않는다.'},
        {'command':'history','note':'과거 이력 인덱스와 각 작업의 상태·요청·결과를 읽는다. 손상되거나 누락된 기록 하나로 전체 조회가 실패할 수 있다. Hermes는 별도 history-observe로 기록 상태만 조회한다.'},
        {'command':'active','note':'active.json과 저장된 작업 상태를 읽는다. running은 기록상 상태이며 실제 프로세스 또는 GPU 점유 확인이 아니다.'},
        {'command':'history-delete','note':'원 서비스에서 선택한 종료 작업의 입력 사본·중간 산출물·결과·로그와 인덱스를 삭제한다. 숨김 처리가 아니며 Hermes는 직접 실행하지 않는다.'},
        {'command':'history-reset','note':'원 서비스에서 검증된 전체 작업 폴더와 인덱스를 삭제한다. 실행·대기 또는 상태 미확인 작업이 있으면 거부하며 Hermes는 직접 실행하지 않는다.'},
        {'command':'anchor-save','note':'원 서비스는 좌표 검수 이력을 저장하거나 apply_registered 선택 시 등록 애니메이션·등록부·프런트 잠금을 갱신한다. Hermes의 시트 앵커 편집은 별도 sheet-update 경로다.'},
        {'command':'anchor-history-reset','note':'원 서비스는 해당 앵커 이력을 숨김 처리하며 원본 파일은 보존한다. Hermes는 직접 연결하지 않는다.'},
        {'command':'sprite-save','note':'원 서비스는 별도 정렬 편집 프로젝트와 시트 결과를 로컬 이력에 저장한다. Hermes의 등록 원본 시트 저장과 다른 기능이다.'},
        {'command':'sprite-history-reset','note':'원 서비스는 편집 프로젝트 이력을 숨기며 파일을 보존한다. Hermes는 직접 연결하지 않는다.'},
        {'command':'sprite-history-delete','note':'원 서비스는 선택한 편집 프로젝트 이력을 숨기며 파일을 보존한다. Hermes는 직접 연결하지 않는다.'},
        {'command':'sheet-auto','note':'원 서비스는 입력 PNG에서 분리된 캐릭터 경계를 CPU로 추정한다. 자동 결과 검수가 필요하며 Hermes는 이 명령을 직접 연결하지 않는다.'},
        {'command':'sheet-export','note':'원 서비스는 입력 프레임과 앵커로 임시 시트·좌표 기록을 생성한다. Hermes 시트 검토에서 사용하며 등록 원본 저장과 다르다.'},
        {'command':'sheet-gif','note':'원 서비스는 임시 시트 내보내기를 이용해 정렬 검수 GIF를 만든다. Hermes 재생 검토에 연결되며 게임 렌더링과는 다르다.'},
        {'command':'sheet-update','note':'원 서비스는 등록된 원본 시트·메타데이터·등록부·프런트 잠금을 갱신한다. 변경 대상의 잠금 항목 누락·중복을 거부한다. Hermes는 별도 검토와 접수 ID를 요구한다. 시트·앵커 변경은 에셋 저장소의 공용 잠금을 사용한다. 잠금을 사용하지 않는 외부 편집과 강제 종료 복구는 보장하지 않는다.'},
    ],
    'music-heartmula': [
        {'command':'prepare','note':'원 서비스의 모델 준비는 GPU 대기열에 작업을 등록한다. 숨겨진 원본 작업까지 중복 확인하며 상태 확인 불가 시 거부한다. Hermes의 모델 준비는 별도 download-model을 선택해 파일을 내려받는다.'},
        {'command':'download-model','note':'Hermes 모델 준비가 선택하는 파일 다운로드다. 대기·실행·일시정지 음악 작업과 충돌하면 시작을 거부한다. GPU 준비나 실제 생성 검증 완료를 뜻하지 않는다.'},
    ],
    'sfx-dasheng-audiogen': [
        {'command':'prepare','note':'원 서비스의 모델 준비는 GPU 대기열에 작업을 등록한다. 숨겨진 원본 작업까지 중복 확인하며 상태 확인 불가 시 거부한다. Hermes의 모델 준비는 별도 download-model을 선택해 파일을 내려받는다.'},
        {'command':'download-model','note':'Hermes 모델 준비가 선택하는 파일 다운로드다. 대기·실행·일시정지 음악 작업과 충돌하면 시작을 거부한다. GPU 준비나 실제 생성 검증 완료를 뜻하지 않는다.'},
    ],
    'flux-seamless': [
        {'command':'generate','note':'새 작업은 512×512, 참조 이미지 없음, global-periodic-v1 방식과 16스텝만 허용한다.'},
    ],
    'wan22-vace': [
        {'command':'resume','note':'저장된 model_profile이 official-bf16-resident-v1이 아닌 과거 작업은 재개할 수 없다. 입력을 검토해 새 작업을 접수한다.'},
    ],
    'wan22-fun-control': [
        {'command':'generate','note':'시작·종료 이미지 자체 확장, 참조 전용 모드, RGB 영상 직접 입력과 타일 VAE는 폐기됐다. 포즈 영상·참조 이미지와 일반 VAE 등 현재 입력 계약을 확인한다.'},
        {'command':'resume','note':'폐기된 시작·종료 이미지, 참조 전용 또는 RGB 입력을 사용한 과거 작업은 재개할 수 없다. 기존 결과는 조회할 수 있다.'},
    ],
}


def list_management_service_registration():
    """공용 등록을 읽되 사용 가능 여부나 실행 권한으로 간주하지 않는다."""
    from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, inspect_management_policy_rejection, inspect_registered_model_operation, ARCHIVED_QWEN_IMAGE_SERVICES
    from tools.review.common.model_management_catalog import MODEL_PREPARATION_SERVICES
    from generators.music.service_constants import AUDIO_SERVICE_NAMES, inspect_retired_audio_rejection
    from tools.review.domains.character_animation.retirement_policy import inspect_animation_retirement_policy
    from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
    from tools.review.domains.hermes_agent.audio_operations import HERMES_AUDIO_SERVICES
    from tools.review.domains.hermes_agent.video_operations import HERMES_VIDEO_SERVICES
    from tools.review.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES,SOURCE_HISTORY_AUDIO_SERVICES
    current_image_history_services=set(FLUX_IMAGE_PROFILE_RECORDS)|set(ARCHIVED_QWEN_IMAGE_SERVICES)|{'flux-expression','floor-tile'}
    current_service_records=[]
    for current_service_name,current_command_names in sorted(MANAGEMENT_SERVICE_COMMANDS.items()):
        current_blocked_commands=[]
        for current_command_name in current_command_names:
            current_rejection_reason=inspect_management_policy_rejection(current_service_name,current_command_name)
            if current_rejection_reason:
                current_blocked_commands.append({'command':current_command_name,'reason':current_rejection_reason})
        current_owner_blocks=[]
        for current_command_name in current_command_names:
            current_owner_reason=(inspect_animation_retirement_policy(current_command_name) if current_service_name=='character-animation' else inspect_retired_audio_rejection(current_service_name,current_command_name))
            if current_owner_reason:
                current_owner_blocks.append({'command':current_command_name,'reason':current_owner_reason})
        from tools.review.domains.hermes_agent.priority_observer import inspect_hermes_priority_retirement
        current_priority_reason=inspect_hermes_priority_retirement(current_service_name) if 'prioritize' in current_command_names else None
        current_limit_records=list(HERMES_SERVICE_CONDITIONAL_LIMITATIONS.get(current_service_name,[]))
        if 'history-reset-preview' in current_command_names and current_service_name in (current_image_history_services|set(AUDIO_SERVICE_NAMES)|set(HERMES_VIDEO_SERVICES)|{'kimodo','prompt-translation'}):
            current_cleanup_note=('종료된 작업만 정리 후보로 표시하고 실행·대기 또는 확인 불가 항목은 제외한다.' if current_service_name=='kimodo' else '전체 정리 대상과 실행·대기 등 차단 항목을 표시한다.')
            current_limit_records.append({'command':'history-reset-preview','note':'원 서비스에서 삭제 없이 숨긴 이력까지 정리 대상을 확인한다. '+current_cleanup_note+' Hermes는 경로 없는 요약만 조회하며 실제 삭제는 지원하지 않는다. 상태를 다시 확인해야 한다.'})
        if (current_service_name in current_image_history_services or current_service_name in AUDIO_SERVICE_NAMES) and 'cancel' in current_command_names:
            current_limit_records.append({'command':'cancel','note':'원 서비스는 중지 요청을 기록하며 검수 대기 작업은 취소 상태로 변경한다. 요청 접수는 실제 GPU 프로세스 종료 확인이 아니다.'})
        if current_service_name=='character-animation' and 'cancel' in current_command_names:
            current_limit_records.append({'command':'cancel','note':'원 서비스는 대기·실행 기록에 중지 요청을 남긴다. 응답의 running은 실제 GPU 프로세스 생존이나 종료 확인이 아니다.'})
        if current_service_name in AUDIO_SERVICE_NAMES and 'active' in current_command_names:
            current_limit_records.append({'command':'active','note':'원 서비스 이력의 대기·실행 기록 중 첫 작업 ID를 반환하며 실제 GPU 프로세스 생존이나 종료를 확인하지 않는다.'})
        if current_service_name in FLUX_IMAGE_PROFILE_RECORDS and 'model-status' in current_command_names:
            current_limit_records.append({'command':'model-status','note':'공식 모델 파일 크기와 준비 기록을 확인한다. 전체 해시·GPU 실행과 한국어 번역 준비는 별도 확인하며 준비 표시는 생성 성공을 보장하지 않는다.'})
        if current_service_name=='flux-expression' and 'model-status' in current_command_names:
            current_limit_records.append({'command':'model-status','note':'모델 구성 요소의 존재를 확인한다. 전체 해시·GPU 실행과 한국어 번역 준비는 별도이며 준비 표시는 생성 성공을 보장하지 않는다.'})
        if current_service_name in ARCHIVED_QWEN_IMAGE_SERVICES and 'model-status' in current_command_names:
            current_limit_records.append({'command':'model-status','note':'과거 모델 파일·환경 상태를 확인할 수 있으나 신규 생성·재개·모델 준비는 게이트웨이에서 차단된다.'})
        if current_service_name in current_image_history_services and 'status' in current_command_names:
            current_limit_records.append({'command':'status','note':'원 서비스는 저장된 작업 상태와 로그 끝 최대 12,000바이트를 읽는다. 실제 GPU 프로세스의 생존이나 종료는 확인하지 않는다.'})
        if current_service_name in current_image_history_services and 'active' in current_command_names:
            current_limit_records.append({'command':'active','note':'원 서비스 이력의 대기·실행 기록 중 첫 작업을 반환한다. running도 대기를 포함하며 실제 GPU 프로세스 생존이나 종료를 확인하지 않는다.'})
        if (current_service_name in AUDIO_SERVICE_NAMES or current_service_name=='prompt-translation') and 'logs' in current_command_names:
            current_limit_records.append({'command':'logs','note':'원 서비스는 작업 로그의 마지막 최대 16,000바이트를 텍스트로 반환한다. Hermes 원본 이력 관측에는 로그가 포함되지 않는다.'})
        if (current_service_name in current_image_history_services or current_service_name in (*HERMES_VIDEO_SERVICES,'kimodo')) and 'logs' in current_command_names:
            current_limit_records.append({'command':'logs','note':'원 서비스는 작업 로그 파일 전체를 텍스트로 반환한다. Hermes 원본 이력 관측에는 로그가 포함되지 않는다.'})
        if current_service_name in (*HERMES_VIDEO_SERVICES,'kimodo'):
            for current_observe_command in ('active','history','status'):
                if current_observe_command in current_command_names:
                    current_limit_records.append({'command':current_observe_command,'note':'원 서비스는 조회 중 중단 작업 상태를 복구해 기록을 변경할 수 있다. 활성 기록은 실제 GPU 프로세스 전체의 생존·종료를 보장하지 않는다.'})
        if current_service_name in AUDIO_SERVICE_NAMES and 'history' in current_command_names:
            current_limit_records.append({'command':'history','note':'원 서비스 이력은 각 작업 상태와 로그 끝부분을 함께 읽는다. Hermes 원본 이력 관측은 로그를 포함하지 않는다.'})
        if current_service_name in current_image_history_services and 'history' in current_command_names:
            current_limit_records.append({'command':'history','note':'원 서비스 이력은 대기·실행 중 작업의 로그 끝부분을 읽는다. Hermes 원본 이력 관측은 로그를 포함하지 않는다.'})
        for current_unlinked_command in ('resume','history-delete','history-reset','writer-delete'):
            if current_unlinked_command in current_command_names and not (current_unlinked_command=='resume' and current_service_name in ('music-heartmula','sfx-dasheng-audiogen','prompt-translation','kimodo')):
                current_unlinked_note='Hermes에서는 이 명령을 직접 실행할 수 없습니다. 원 서비스의 정책과 대상을 확인하세요.'
                if current_unlinked_command=='resume' and (current_service_name in HERMES_VIDEO_SERVICES or current_service_name in FLUX_IMAGE_PROFILE_RECORDS):
                    current_unlinked_note+=' 저장 입력을 확인하는 별도 재개 검토와 확인 후 접수는 Hermes에서 지원합니다.'
                if current_service_name=='writer-agent' and current_unlinked_command=='writer-delete':
                    current_unlinked_note='Hermes에서는 이 명령을 직접 실행할 수 없습니다. 원 서비스는 작업과 대기열 종료 상태 및 실행 잠금을 확인하고 기록을 휴지통으로 이동합니다. 원본 적용 복구 중인 기록은 삭제할 수 없습니다.'
                if any(current_block_record['command']==current_unlinked_command for current_block_record in current_blocked_commands):
                    current_unlinked_note+=' 관리 게이트웨이에서도 차단됩니다.'
                if any(current_block_record['command']==current_unlinked_command for current_block_record in current_owner_blocks):
                    current_unlinked_note+=' 원 서비스에서도 차단됩니다.'
                current_limit_records.append({'command':current_unlinked_command,'note':current_unlinked_note})
        if current_service_name in ('billboard-generator','building-generator'):
            current_limit_records.append({'command':'history-observe','note':'통합 빌보드 작업 경로는 빌보드 서비스로 확인하며 건물 호환 요청인지 구분하지 못한다. 과거 건물 전용 경로는 건물 서비스로 확인한다. 경로가 다른 예약은 직접 확인한다.'})
        if current_priority_reason:
            current_limit_records.append({'command':'prioritize','note':'Hermes는 폐기된 작업을 우선 실행하지 않습니다. '+current_priority_reason})
        if current_service_name in FLUX_IMAGE_PROFILE_RECORDS and current_service_name!='flux-seamless' and 'generate' in current_command_names:
            current_minimum_references=FLUX_IMAGE_PROFILE_RECORDS[current_service_name][4]
            current_reference_note='첫 참조 이미지가 필요하며 최대 2장' if current_minimum_references else '참조 이미지는 최대 2장'
            current_step_note='이고 1~50스텝을 허용한다.' if current_service_name=='flux-character' else '이고 16스텝만 허용한다.'
            current_limit_records.append({'command':'generate','note':current_reference_note+current_step_note})
        if current_service_name=='flux-expression' and 'generate' in current_command_names:
            current_limit_records.append({'command':'generate','note':'등록된 표정과 얼굴 참조 이미지 1장이 필요하며 16스텝만 허용한다.'})
        current_hermes_links=[]
        if current_service_name in HERMES_AUDIO_SERVICES:
            current_hermes_links=['hermes-audio-proposal','hermes-delegate-audio','hermes-audio-status','hermes-audio-history','hermes-audio-source-status','hermes-audio-source-history','hermes-audio-cancel']
            current_hermes_links.extend(['hermes-audio-resume-preview','hermes-audio-resume-submit','hermes-audio-resume-receipt'])
        elif current_service_name in HERMES_VIDEO_SERVICES:
            current_hermes_links=['hermes-video-proposal','hermes-delegate-video','hermes-video-source-status','hermes-video-status','hermes-video-history','hermes-video-cancel']
        elif current_service_name in FLUX_IMAGE_PROFILE_RECORDS or current_service_name=='flux-expression':
            current_hermes_links=['hermes-delegate-flux-profile','hermes-flux-source-status','hermes-flux-profile-status','hermes-flux-profile-history','hermes-flux-profile-cancel','hermes-service-receipt']
            if current_service_name!='flux-image':current_hermes_links.append('hermes-flux-proposal')
            if current_service_name=='flux-expression':current_hermes_links.append('hermes-expression-catalog')
        elif current_service_name=='kimodo':
            current_hermes_links=['hermes-kimodo-keyframe-source-review','hermes-kimodo-keyframe-save','hermes-kimodo-keyframe-receipt','hermes-video-source-status','hermes-kimodo-source-frame','hermes-kimodo-resume-proposal','hermes-kimodo-resume-preview','hermes-kimodo-resume-submit','hermes-kimodo-resume-receipt','hermes-kimodo-proposal','hermes-kimodo-build-status','hermes-delegate-kimodo','hermes-delegation-status','hermes-delegation-job-status','hermes-delegation-history','hermes-delegation-cancel','hermes-kimodo-keyframes','hermes-kimodo-keyframe-preview','hermes-kimodo-keyframe-validate']
        elif current_service_name=='hermes-agent':
            current_hermes_links=['hermes-capabilities','hermes-service-registration','hermes-session-list','hermes-session-read','hermes-session-view','hermes-history','hermes-detail']
        elif current_service_name=='writer-agent':
            current_hermes_links=['hermes-writer-index-status','hermes-writer-proposal','hermes-delegate-writer','hermes-writer-status','hermes-writer-search-paths','hermes-writer-job-search-paths','hermes-writer-job-review','hermes-writer-job-material','hermes-writer-history','hermes-writer-cancel','hermes-writer-reservation-preview','hermes-writer-reservation-recover','hermes-writer-reservation-receipt','hermes-writer-apply']
        elif current_service_name=='prompt-translation':
            current_hermes_links=['hermes-translation-evidence','hermes-delegate-translation','hermes-translation-status','hermes-translation-history','hermes-translation-cancel']
            current_hermes_links.extend(['hermes-translation-resume-preview','hermes-translation-resume-submit','hermes-translation-resume-receipt'])
        elif current_service_name=='map-assets':
            current_hermes_links=['hermes-content-database-status','hermes-map-database-receipt','hermes-building-catalog','hermes-building-preview','hermes-building-save','hermes-building-receipt','hermes-billboard-catalog','hermes-billboard-load','hermes-billboard-preview','hermes-billboard-save','hermes-effect-catalog','hermes-effect-detail','hermes-effect-preview','hermes-effect-save','hermes-effect-register-preview','hermes-effect-register','hermes-waypoint-preview','hermes-waypoint-replace','hermes-field-load','hermes-field-region','hermes-field-preview','hermes-field-save','hermes-city-source','hermes-city-load','hermes-city-preview','hermes-city-save']
        elif current_service_name=='character-animation':
            current_hermes_links=['hermes-character-source-status','hermes-sprite-pending-status','hermes-sprite-catalog','hermes-sprite-detail','hermes-sprite-preview','hermes-sprite-save','hermes-sprite-playback','hermes-sprite-clip-playback']
        elif current_service_name=='model-downloads':
            current_hermes_links=['hermes-model-inventory','hermes-model-download-status']
        if current_service_name in ('dwpose','wan22-animate2','wan22-vace','wan22-fun-control'):
            current_hermes_links.extend(['hermes-video-resume-proposal','hermes-video-resume-preview','hermes-video-resume-submit','hermes-video-resume-receipt'])
        if current_service_name in FLUX_IMAGE_PROFILE_RECORDS:
            current_hermes_links.extend(['hermes-flux-resume-proposal','hermes-flux-resume-preview','hermes-flux-resume-submit','hermes-flux-resume-receipt'])
        from tools.review.domains.hermes_agent.delegation_store import list_hermes_service_receipt_names
        if current_service_name in list_hermes_service_receipt_names() and 'hermes-service-receipt' not in current_hermes_links:
            current_hermes_links.append('hermes-service-receipt')
        if 'prioritize' in current_command_names and not current_priority_reason and not any(item['command']=='prioritize' for item in current_blocked_commands):
            current_hermes_links.extend(['hermes-priority-preview','hermes-priority-submit','hermes-priority-receipt'])
        from tools.review.domains.hermes_agent.image_source_operations import IMAGE_SOURCE_SERVICES
        if current_service_name in IMAGE_SOURCE_SERVICES:current_hermes_links.append('hermes-image-source-status')
        if current_service_name in (*SOURCE_HISTORY_AUDIO_SERVICES,*HERMES_VIDEO_SERVICES,*FLUX_IMAGE_PROFILE_RECORDS,'flux-expression','kimodo','prompt-translation','qwen-21','qwen-21-circular','mannequin-generator','prop-generator','vegetation-generator','expression','seamless-tile','floor-tile','billboard-generator','building-generator'):
            current_hermes_links.extend(['hermes-generator-reservation-inspect','hermes-generator-reservation-recover','hermes-generator-reservation-receipt'])
        if 'history-reset-preview' in current_command_names and not any(current_block_record['command']=='history-reset-preview' for current_block_record in (*current_blocked_commands,*current_owner_blocks)):
            current_hermes_links.append('hermes-cleanup-preview')
        if current_service_name in SOURCE_HISTORY_GENERATOR_SERVICES:
            current_hermes_links.append('hermes-generator-source-history')
        if current_service_name in SOURCE_HISTORY_AUDIO_SERVICES and current_service_name not in HERMES_AUDIO_SERVICES:
            current_hermes_links.append('hermes-audio-source-history')
        if current_service_name=='flux-image':
            current_hermes_links.extend(['hermes-delegate-flux-image','hermes-flux-delegation-status','hermes-flux-delegation-history','hermes-flux-delegation-cancel','hermes-flux-proposal'])
        if current_service_name=='map-assets':
            current_hermes_links.extend(['hermes-world-map','hermes-billboard-proposal','hermes-billboard-receipt','hermes-building-proposal','hermes-effect-proposal','hermes-effect-receipt','hermes-effect-register-receipt','hermes-waypoint-receipt','hermes-field-proposal','hermes-field-receipt','hermes-field-history','hermes-city-proposal','hermes-city-receipt','hermes-city-history'])
        if current_service_name=='character-animation':
            current_hermes_links.extend(['hermes-sprite-proposal','hermes-sprite-receipt'])
        if current_service_name=='writer-agent':
            current_hermes_links.extend(['hermes-writer-apply-status','hermes-writer-apply-history'])
        if current_service_name=='prompt-translation':
            current_hermes_links.append('hermes-translation-proposal')
        if current_service_name in ('map-review','character-review'):
            current_hermes_links.extend(['hermes-capture-status','hermes-capture-proposal'])
        if current_service_name in {current_model_name for _,current_model_name in MODEL_PREPARATION_SERVICES}:
            current_hermes_links.extend(['hermes-model-readiness','hermes-model-prepare-status','hermes-model-prepare-history'])
            if inspect_registered_model_operation(current_service_name,current_command_names,'prepare') is not None:
                current_hermes_links.append('hermes-model-prepare')
        current_service_records.append({'service':current_service_name,'commands':list(current_command_names),'availability':'unverified','gateway_blocked':current_blocked_commands,'known_service_blocked':current_owner_blocks,'conditional_limitations':current_limit_records,'hermes_links':current_hermes_links})
    return {'version':1,'services':current_service_records,'note':'게이트웨이의 명시적 차단과 확인된 음악·캐릭터 애니메이션 서비스 폐기 정책을 표시합니다. 표시된 조건부 제한은 전체 목록이 아닙니다. 그 밖의 소유 서비스 정책·실행 가능 여부와 Hermes 권한은 미확인입니다. 실행 범위는 Hermes 기능 목록을 확인하세요.'}


def search_management_service_registration(current_search_request):
    """등록 서비스와 확인된 차단을 제한된 페이지로 검색한다."""
    if not isinstance(current_search_request,dict) or set(current_search_request)-{'query','offset','limit'}:
        raise ValueError('서비스 검색 필드 오류')
    current_query_text=current_search_request.get('query','')
    current_offset_value=current_search_request.get('offset',0)
    current_limit_value=current_search_request.get('limit',5)
    if not isinstance(current_query_text,str) or len(current_query_text)>100 or type(current_offset_value) is not int or current_offset_value<0 or type(current_limit_value) is not int or not 1<=current_limit_value<=10:
        raise ValueError('서비스 검색 범위 오류')
    current_catalog_value=list_management_service_registration()
    current_query_text=current_query_text.strip().casefold()
    current_capability_labels={current_record['command']:current_record['label'] for current_record in list_hermes_capability_catalog()['records']}
    current_matching_records=[current_record for current_record in current_catalog_value['services'] if not current_query_text or current_query_text in ' '.join((current_record['service'],*current_record['commands'],*current_record['hermes_links'],*(current_capability_labels.get(current_link_name,'') for current_link_name in current_record['hermes_links']),*(current_item['reason'] for current_item in current_record['gateway_blocked']),*(current_item['reason'] for current_item in current_record['known_service_blocked']),*(current_item['note'] for current_item in current_record['conditional_limitations']))).casefold()]
    current_page_records=current_matching_records[current_offset_value:current_offset_value+current_limit_value]
    current_next_offset=current_offset_value+len(current_page_records)
    return {'version':current_catalog_value['version'],'services':current_page_records,'total':len(current_matching_records),'offset':current_offset_value,'next_offset':current_next_offset if current_next_offset<len(current_matching_records) else None,'note':current_catalog_value['note']}

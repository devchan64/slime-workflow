"""Hermes가 제공하는 주요 관리 기능의 범위와 영향 안내."""

HERMES_CAPABILITY_RECORDS = (
    {'command':'hermes-generator-source-history','label':'생성·번역 원본 이력','required':['service'],'optional':['offset','limit','snapshot'],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'generator_source_history','note':'기록 상태만 읽는다. 건물 호환 경로는 빌보드 이력을 공유한다. 중단 작업 복구를 실행하지 않으며 실제 생존과 결과는 별도 확인한다.'},
    {'command':'hermes-audio-source-history','label':'음악·효과음 원본 이력','required':['service'],'optional':['offset','limit','snapshot'],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'audio_source_history','note':'Hermes 접수 이외의 원본 이력도 기록 상태만 읽는다. 실제 작업 생존과 결과는 별도다.'},
    {'command':'hermes-kimodo-build-status','label':'Kimodo MIGraphX 빌드 기록','required':[],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'kimodo_build_status','note':'최근 빌드 기록만 읽는다. 캐시 유효성과 작업 생존은 별도 확인한다.'},
    {'command':'hermes-capabilities','label':'Hermes 기능 목록','required':[],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp','isolated_fixed_bridge'],'result':'capability_catalog','note':'게이트웨이 등록과 목록의 차이를 함께 표시한다.'},
    {'command':'hermes-session-create','label':'대화 세션 생성','required':['session_id'],'optional':[],'effect':'write','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'session','note':'같은 세션 ID로 재시도할 수 있다.'},
    {'command':'hermes-session-read','label':'대화 세션 기록 조회','required':['session_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['mcp'],'result':'session','note':'저장된 세션 기록을 읽는다.'},
    {'command':'hermes-session-list','label':'대화 세션 목록','required':[],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'session_list','note':'최근 세션과 잘림 여부를 반환한다.'},
    {'command':'hermes-session-view','label':'대화 및 작업 상태 조회','required':['session_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'session_view','note':'최근 메시지와 연결된 작업 상태를 제공한다.'},
    {'command':'hermes-submit','label':'격리 코딩 작업 접수','required':['request_id','prompt'],'optional':['verification_modules'],'effect':'enqueue','gpu':'exclusive','retry':'request_id','interfaces':['gui','mcp'],'result':'hermes_job_id','note':'동일 접수 ID와 입력은 기존 작업을 반환한다.'},
    {'command':'hermes-detail','label':'격리 작업 상세 조회','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'hermes_job_detail','note':'상태와 답변·diff·검증 결과를 반환한다.'},
    {'command':'hermes-history','label':'격리 작업 이력 조회','required':[],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'hermes_history','note':'최근 작업 최대 100건을 반환한다.'},
    {'command':'hermes-cancel','label':'격리 작업 중지 요청','required':['id'],'optional':[],'effect':'cancel_request','gpu':'none','retry':'check_status','interfaces':['gui','mcp'],'result':'cancel_request_status','note':'중지 요청과 실제 프로세스 종료는 구분한다.'},
    {'command':'hermes-delegation-history','label':'Kimodo 위임 접수 이력','required':[],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'receipt_history','note':'Kimodo 위임 접수 기록만 확인한다.'},
    {'command':'hermes-video-proposal','label':'동작·영상 위임 제안 읽기','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'untrusted_video_proposal','note':'서비스·모드·지시만 읽는다. 사용자가 첨부하고 기존 검증을 완료해야 한다.'},
    {'command':'hermes-delegate-video','label':'동작·영상 작업 위임','required':['request_id','service','request'],'optional':[],'effect':'enqueue','gpu':'queued','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'video_receipt','note':'DWPose와 Wan 3개 생성기의 입력·첨부 검증과 공용 GPU 대기열을 사용한다.'},
    {'command':'hermes-video-status','label':'동작·영상 작업 상태','required':['request_id','service'],'optional':[],'effect':'recovery_possible','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'video_status','note':'중단 작업 복구가 따를 수 있으며 검증된 동일 출처 결과만 반환한다.'},
    {'command':'hermes-video-history','label':'동작·영상 접수 이력','required':['service'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'video_receipts','note':'선택 서비스의 Hermes 접수만 표시한다.'},
    {'command':'hermes-video-cancel','label':'동작·영상 작업 중지','required':['request_id','service','job_id'],'optional':[],'effect':'cancel_request','gpu':'none','retry':'check_status','interfaces':['gui','mcp'],'result':'video_cancel','note':'접수 기록과 일치하는 작업만 중지 요청한다.'},
    {'command':'hermes-audio-proposal','label':'음악·효과음 위임 제안 읽기','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'untrusted_audio_proposal','note':'완료된 답변의 제안을 서비스별 입력 계약으로 검증한다. 생성은 하지 않는다.'},
    {'command':'hermes-delegate-audio','label':'음악·효과음 생성 위임','required':['request_id','service','request'],'optional':[],'effect':'enqueue','gpu':'queued','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'audio_receipt','note':'HeartMuLa와 Dasheng의 기존 입력 검증·공용 GPU 대기열을 사용한다.'},
    {'command':'hermes-audio-status','label':'음악·효과음 작업 상태','required':['request_id','service'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'audio_status','note':'검증된 동일 출처 결과 경로만 반환한다.'},
    {'command':'hermes-audio-history','label':'음악·효과음 접수 이력','required':['service'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'audio_receipts','note':'선택한 서비스의 Hermes 접수만 표시한다.'},
    {'command':'hermes-audio-cancel','label':'음악·효과음 작업 중지','required':['request_id','service','job_id'],'optional':[],'effect':'cancel_request','gpu':'none','retry':'check_status','interfaces':['gui','mcp'],'result':'audio_cancel','note':'접수 기록과 일치하는 작업만 중지 요청한다.'},
    {'command':'hermes-delegate-flux-profile','label':'FLUX 프로필 생성 위임','required':['request_id','service','request'],'optional':[],'effect':'enqueue','gpu':'queued','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'flux_profile_receipt','note':'8개 이미지 프로필과 별도 표정 생성기의 참조·크기 검증과 GPU 대기열을 사용한다.'},
    {'command':'hermes-flux-profile-status','label':'FLUX 프로필 작업 상태','required':['request_id','service'],'optional':[],'effect':'recovery_possible','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'flux_profile_status','note':'해당 생성기의 작업 복구 동작이 따를 수 있다.'},
    {'command':'hermes-flux-profile-history','label':'FLUX 프로필 접수 이력','required':['service'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'flux_profile_history','note':'서비스가 일치하는 Hermes 접수만 표시한다.'},
    {'command':'hermes-flux-profile-cancel','label':'FLUX 프로필 작업 중지','required':['request_id','service','job_id'],'optional':[],'effect':'cancel_request','gpu':'none','retry':'check_status','interfaces':['gui','mcp'],'result':'flux_profile_cancel','note':'접수 기록과 일치하는 프로필 작업만 중지 요청한다.'},
    {'command':'hermes-writer-apply','label':'확인한 작가 제안 적용','required':['request_id','writer_request_id','job_id','proposal_hash'],'optional':[],'effect':'write','gpu':'none','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'writer_apply_receipt','note':'전체 diff와 제안 해시를 확인해야 하며 문서 원본을 변경한다.'},
    {'command':'hermes-writer-apply-status','label':'작가 제안 적용 접수 확인','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'writer_apply_receipt','note':'접수 기록만 확인한다.'},
    {'command':'hermes-writer-apply-history','label':'작가 제안 적용 이력','required':[],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'writer_apply_history','note':'Hermes의 적용 기록만 조회한다.'},
    {'command':'hermes-delegate-writer','label':'작가 AI 작업 위임','required':['request_id','request'],'optional':[],'effect':'enqueue','gpu':'queued','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'writer_receipt','note':'문서 색인·작성·중복 검토를 기존 GPU 대기열로 접수한다.'},
    {'command':'hermes-writer-status','label':'작가 AI 작업·제안 조회','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'writer_review','note':'제안 diff는 크기 제한이 있으며 전체 근거와 적용은 작가 AI 화면에서 확인한다.'},
    {'command':'hermes-writer-reservation-recover','label':'작가 GPU 예약 정리','required':['request_id','job_id','review_sha256','outside_processes_checked'],'optional':[],'effect':'write','gpu':'none','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'writer_reservation_receipt','note':'검토한 그룹을 강제 종료한 뒤 예약을 해제한다. 별도 그룹 GPU 프로세스 확인이 필요하다.'},
    {'command':'hermes-writer-reservation-receipt','label':'작가 GPU 예약 정리 접수 확인','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'writer_reservation_receipt','note':'응답 유실 시 확인하며 미확인 작업을 재실행하지 않는다.'},
    {'command':'hermes-writer-reservation-preview','label':'작가 GPU 예약 복구 가능 여부','required':['job_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'writer_reservation_preview','note':'실행기와 작업자 신원만 검토한다. 종료·예약 삭제는 하지 않는다.'},
    {'command':'hermes-writer-cancel','label':'작가 AI 작업 중지 요청','required':['request_id','job_id'],'optional':[],'effect':'cancel_request','gpu':'none','retry':'check_status','interfaces':['gui','mcp'],'result':'writer_cancel','note':'접수와 작업 ID를 확인하고 중지를 요청한다. 실제 종료는 별도 확인한다.'},
    {'command':'hermes-writer-history','label':'작가 AI 위임 이력','required':[],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'writer_receipt_history','note':'Hermes의 작가 AI 접수만 표시한다.'},
    {'command':'hermes-translation-proposal','label':'번역 위임 제안 읽기','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'untrusted_translation_proposal','note':'완료된 답변의 단일 제안을 기존 번역 정책으로 검증한다. 번역을 실행하지 않는다.'},
    {'command':'hermes-delegate-translation','label':'프롬프트 번역 위임','required':['request_id','request'],'optional':[],'effect':'enqueue','gpu':'queued','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'translation_receipt','note':'기존 용어 검증과 GPU 대기열을 사용한다.'},
    {'command':'hermes-translation-status','label':'번역 작업과 검토 결과','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'translation_status','note':'결과와 용어·조건 점검을 반환한다.'},
    {'command':'hermes-translation-history','label':'번역 위임 이력','required':[],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'translation_receipt_history','note':'Hermes를 통한 번역 접수만 표시한다.'},
    {'command':'hermes-translation-cancel','label':'번역 작업 중지','required':['request_id','job_id'],'optional':[],'effect':'cancel_request','gpu':'none','retry':'check_status','interfaces':['gui','mcp'],'result':'cancel_request_status','note':'접수와 일치하는 번역 작업에 중지를 요청한다.'},
    {'command':'hermes-field-proposal','label':'야외 맵 셀 변경 제안 읽기','required':['id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'untrusted_field_proposal','note':'완료된 답변의 셀 제안만 읽으며 원본 리비전과 맵 검증은 별도다.'},
    {'command':'hermes-field-region', 'label':'야외 맵 영역과 배치 조회', 'required':['map'], 'optional':['column','row','width','height','offset','limit','revision'], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['mcp','isolated_fixed_bridge'], 'result':'field_region_page', 'note':'원본 영역과 오브젝트를 제한 조회한다. blocked는 실제 최종 통행 판정이 아니다.'},
    {'command':'hermes-city-load','label':'도시 맵 원본 읽기','required':['map'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'city_map_document','note':'콘텐츠 DB와 로컬 잠금이 필요하다.'},
    {'command':'hermes-city-preview','label':'도시 맵 초안 검증','required':['draft'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'city_preview_token','note':'원장 세대·리비전과 공간 검증 후 로컬 임시 초안을 남긴다.'},
    {'command':'hermes-city-save','label':'도시 맵 초안 저장','required':['request_id','draft','token'],'optional':[],'effect':'write','gpu':'none','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'city_save_receipt','note':'검증된 도시 원장을 콘텐츠 DB에 저장한다.'},
    {'command':'hermes-city-receipt','label':'도시 맵 저장 확인','required':['request_id'],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'city_save_receipt','note':'저장 접수만 확인한다.'},
    {'command':'hermes-city-history','label':'도시 맵 저장 이력','required':[],'optional':[],'effect':'local_bookkeeping','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'city_save_history','note':'최근 접수 중 손상된 기록은 제외한다.'},
    {'command':'hermes-field-receipt', 'label':'야외 맵 저장 접수 확인', 'required':['request_id'], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'field_save_receipt', 'note':'원본은 변경하지 않는다. 확인 불가 시 원본을 살펴본다.'},
    {'command':'hermes-field-history', 'label':'야외 맵 저장 이력', 'required':[], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'field_save_history', 'note':'최근 접수 기록만 읽으며 손상된 기록은 제외한다.'},
    {'command':'hermes-field-load', 'label':'야외 맵 편집 원본 읽기', 'required':['map'], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'field_map_document', 'note':'기존 맵 편집기의 원본·리비전을 읽으며 로컬 잠금 파일을 만들 수 있다.'},
    {'command':'hermes-field-preview', 'label':'야외 맵 초안 검증', 'required':['draft'], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'field_preview_token', 'note':'기존 편집 검증을 사용하며 로컬 임시 초안 기록을 생성한다.'},
    {'command':'hermes-field-save', 'label':'야외 맵 초안 저장', 'required':['request_id','draft','token'], 'optional':[], 'effect':'write', 'gpu':'none', 'retry':'request_id_or_unknown', 'interfaces':['gui','mcp'], 'result':'field_save_receipt', 'note':'초안 재검증 후 원본·등록부·소비자 잠금 및 카탈로그가 변경될 수 있다.'},
    {'command':'hermes-content-database-status', 'label':'콘텐츠 DB와 원장 반영 상태', 'required':[], 'optional':[], 'effect':'read', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp','isolated_fixed_bridge'], 'result':'content_database_generation_status', 'note':'콘텐츠 서비스의 DB 세대와 원장 반영 상태를 조회한다. 연결 실패는 미확인이다.'},
    {'command':'hermes-model-prepare-history', 'label':'모델 준비 접수 이력', 'required':[], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'preparation_receipt_history', 'note':'최근 접수 기록을 읽는다. 손상된 기록은 제외한다.'},
    {'command':'hermes-model-prepare', 'label':'모델 준비 요청', 'required':['request_id','service'], 'optional':[], 'effect':'enqueue', 'gpu':'service_dependent', 'retry':'request_id_or_unknown', 'interfaces':['gui','mcp'], 'result':'preparation_receipt', 'note':'다운로드·디스크 사용 및 서비스별 GPU 작업이 발생할 수 있다. 기존 정책을 적용하며 완료는 별도 확인한다.'},
    {'command':'hermes-model-prepare-status', 'label':'모델 준비 접수 확인', 'required':['request_id','service'], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'preparation_receipt', 'note':'접수 기록만 확인한다. 모델 완료 상태는 별도 조회한다.'},
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
    {'command':'hermes-sprite-save','label':'스프라이트 앵커 저장','required':['request_id','draft','token','review_sha256'],'optional':[],'effect':'write','gpu':'none','retry':'request_id_or_unknown','interfaces':['gui','mcp'],'result':'sprite_anchor_receipt','note':'검토 후 시트·좌표맵·등록부·프런트 잠금을 갱신한다.'},
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
    {'command':'hermes-model-inventory', 'label':'모델 파일 보유량 조회', 'required':[], 'optional':[], 'effect':'read', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp','isolated_fixed_bridge'], 'result':'model_file_counts_and_sizes', 'note':'파일 존재는 준비 완료나 해시 검증을 뜻하지 않는다.'},
    {'command':'hermes-management-status', 'label':'관리 상태 조회', 'required':[], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp','isolated_fixed_bridge'], 'result':'model_gpu_queue_and_recent_jobs', 'note':'최근 작업 조회에 로컬 잠금이 따른다. Kimodo 활성 상태는 기록 기준이며 GPU 관측은 캐시될 수 있다.'},
    {'command':'hermes-session-submit', 'label':'대화·격리 작업 접수', 'required':['session_id','request_id','prompt'], 'optional':['verification_modules'], 'effect':'enqueue', 'gpu':'exclusive', 'retry':'request_id', 'interfaces':['gui','mcp'], 'result':'hermes_job_id', 'note':'동일 ID와 입력의 재접수만 허용한다.'},
    {'command':'hermes-kimodo-keyframe-validate','label':'Kimodo 키프레임 배치 검증','required':['keyframes','frames'],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'kimodo_keyframe_validation','note':'원본과 골격 구조를 검증한다. 접수 시 다시 검증한다.'},
    {'command':'hermes-kimodo-keyframe-preview','label':'Kimodo 키프레임 검증 미리보기','required':['keyframe_id'],'optional':[],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'kimodo_keyframe_preview','note':'기존 서비스의 모션·골격·이미지 해시 검증을 사용한다.'},
    {'command':'hermes-kimodo-keyframes','label':'Kimodo 키프레임 목록','required':[],'optional':['query','offset','limit','snapshot'],'effect':'read','gpu':'none','retry':'safe','interfaces':['gui','mcp'],'result':'kimodo_keyframe_catalog','note':'기록의 ID·태그·원본 프레임만 제공한다. 해시와 실제 동작은 Kimodo에서 확인한다.'},
    {'command':'hermes-kimodo-proposal', 'label':'Kimodo 제안 읽기', 'required':['id'], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'validated_untrusted_proposal', 'note':'제안은 실행되지 않는다.'},
    {'command':'hermes-delegate-kimodo', 'label':'Kimodo 생성 위임', 'required':['request_id','request'], 'optional':[], 'effect':'enqueue', 'gpu':'queued', 'retry':'request_id_or_unknown', 'interfaces':['gui','mcp'], 'result':'receipt_and_job_id', 'note':'화면은 입력과 GPU 사용 확인 후 접수한다. 응답 불확실 시 재실행하지 않는다.'},
    {'command':'hermes-delegation-status', 'label':'위임 접수 확인', 'required':['request_id'], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'receipt', 'note':'생성 작업을 실행하지 않는다.'},
    {'command':'hermes-delegation-job-status', 'label':'Kimodo 작업 상태', 'required':['request_id'], 'optional':[], 'effect':'recovery_possible', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'receipt_and_job_status', 'note':'MCP는 접수 ID로 조회한다. 화면은 같은 Kimodo 상태 명령을 작업 ID로 조회하며 중단 작업 복구가 발생할 수 있다.'},
    {'command':'hermes-delegation-cancel', 'label':'위임 작업 중지', 'required':['request_id','job_id'], 'optional':[], 'effect':'cancel_request', 'gpu':'none', 'retry':'check_status', 'interfaces':['gui','mcp'], 'result':'cancel_request_status', 'note':'확인한 작업에 중지를 요청하며 실제 종료는 별도다.'},
    {'command':'hermes-diff', 'label':'격리 변경 전체 조회', 'required':['id','offset','limit'], 'optional':[], 'effect':'local_bookkeeping', 'gpu':'none', 'retry':'safe', 'interfaces':['gui','mcp'], 'result':'base64_byte_chunk', 'note':'종료된 작업의 바이트 조각을 읽는다.'},
)


HERMES_FIELD_SCHEMAS = {
    'keyframes': {'type':'array','minItems':1,'validation':'Kimodo 키프레임 배치 계약'},
    'frames': {'type':'integer','minimum':1,'note':'생성할 총 출력 프레임'},
    'keyframe_id': {'type':'string','pattern':'^[a-f0-9]{32}$'},
    'writer_request_id': {'type':'string','pattern':'^[A-Za-z0-9_-]{8,80}$'},
    'proposal_hash': {'type':'string','pattern':'^[a-f0-9]{64}$'},
    'column': {'type':'integer','minimum':0,'maximum':10000},
    'row': {'type':'integer','minimum':0,'maximum':10000},
    'width': {'type':'integer','minimum':1,'maximum':16},
    'height': {'type':'integer','minimum':1,'maximum':16},
    'revision': {'type':'string','maxLength':4096},
    'clip': {'type':'string','minLength':1,'maxLength':200},
    'fps': {'type':'integer','enum':[4,6,8,12,16,24,30]},
    'snapshot': {'type':'string','pattern':'^[a-f0-9]{64}$','note':'후속 프레임 페이지에 첫 조회에서 받은 값'},
    'path': {'type':'string','maxLength':512},
    'texture': {'type':'string','pattern':'^[a-z][a-z0-9-]{0,95}$'},
    'review_sha256': {'type':'string','pattern':'^[a-f0-9]{64}$'},
    'draft': {'type':'object','validation':'map-assets map-edit-preview'},
    'token': {'type':'string','pattern':'^[a-f0-9]{64}$'},
    'map': {'type':'string','pattern':'^[a-z0-9][a-z0-9-]{0,95}$'},
    'category': {'type':'string','enum':['vegetation','herbaceous','large-trees','rocks-minerals','props']},
    'query': {'type':'string','maxLength':100,'pattern':r'^[^\x00-\x1f]*$'},
    'service': {'type':'string', 'note':'명령별 관리 서비스 식별자'},
    'session_id': {'type':'string', 'pattern':'^[0-9a-f]{32}$'},
    'outside_processes_checked': {'type':'boolean','const':True,'note':'별도 그룹 GPU 프로세스 확인'},
    'request_id': {'type':'string', 'pattern':'^[A-Za-z0-9_-]{8,80}$'},
    'prompt': {'type':'string', 'minLength':1, 'maxLength':8000},
    'verification_modules': {'type':'array', 'items':{'type':'string'}, 'maxItems':5, 'note':'공용 회귀 모듈 허용 목록'},
    'id': {'type':'string', 'pattern':'^\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}-\\d{2}-[a-f0-9]{8}$'},
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
        if current_command_name == 'hermes-service-registration':
            current_payload_schema['properties']['limit'] = {'type':'integer','minimum':1,'maximum':10}
        if current_command_name == 'hermes-submit':
            current_payload_schema['properties']['prompt'] = {'type':'string','minLength':1,'maxLength':12000}
        if current_command_name == 'hermes-effect-detail':
            current_payload_schema['properties']['id'] = {'type':'string','pattern':'^[a-z][a-z0-9-]{0,95}$'}
        if current_command_name in ('hermes-billboard-catalog', 'hermes-building-catalog', 'hermes-effect-catalog', 'hermes-sprite-catalog', 'hermes-sprite-detail', 'hermes-kimodo-keyframes', 'hermes-audio-source-history', 'hermes-generator-source-history'):
            current_payload_schema['properties']['limit'] = {'type':'integer','minimum':1,'maximum':30}
        if current_command_name == 'hermes-billboard-catalog':
            current_payload_schema['properties']['category'] = {'anyOf':[HERMES_FIELD_SCHEMAS['category'],{'type':'null'}]}
        if current_command_name in ('hermes-sprite-detail', 'hermes-kimodo-keyframes', 'hermes-audio-source-history', 'hermes-generator-source-history'):
            current_payload_schema['properties']['snapshot'] = {'anyOf':[HERMES_FIELD_SCHEMAS['snapshot'],{'type':'null'}]}
        if current_command_name in ('hermes-sprite-detail','hermes-audio-source-history','hermes-generator-source-history'):
            current_payload_schema['allOf'] = [{'if':{'required':['offset'],'properties':{'offset':{'minimum':1}}},'then':{'required':['snapshot'],'properties':{'snapshot':HERMES_FIELD_SCHEMAS['snapshot']}}}]
        if current_command_name == 'hermes-field-region':
            current_payload_schema['properties']['revision'] = {'anyOf':[{'type':'string','minLength':1,'maxLength':4096},{'type':'null'}]}
            current_payload_schema['properties']['offset'] = {'type':'integer','minimum':0,'maximum':100000}
            current_payload_schema['properties']['limit'] = {'type':'integer','minimum':1,'maximum':30}
        if current_command_name in ('hermes-writer-cancel','hermes-writer-reservation-preview','hermes-writer-reservation-recover'):
            current_payload_schema['properties']['job_id'] = {'type':'string','pattern':'^[0-9]{8}-[0-9]{6}-[a-f0-9]{8}$'}
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
        if 'service' in current_field_names and (current_command_name.startswith('hermes-video-') or current_command_name == 'hermes-delegate-video'):
            current_payload_schema['properties']['service'] = {'type':'string','enum':['dwpose','wan22-animate2','wan22-fun-control','wan22-vace']}
        if current_command_name == 'hermes-delegate-video':
            current_payload_schema['properties']['request'] = {'type':'object','validation':'해당 동작·영상 생성기의 validate_generation_request'}
        if 'service' in current_field_names and (current_command_name.startswith('hermes-audio-') or current_command_name == 'hermes-delegate-audio'):
            current_payload_schema['properties']['service'] = {'type':'string','enum':['music-heartmula','sfx-dasheng-audiogen']}
        if current_command_name == 'hermes-audio-source-history':
            from generators.music.service_constants import AUDIO_SERVICE_NAMES
            current_payload_schema['properties']['service'] = {'type':'string','enum':list(AUDIO_SERVICE_NAMES)}
        if current_command_name == 'hermes-delegate-audio':
            current_payload_schema['properties']['request'] = {'type':'object','validation':'generators.music.contracts.validate_music_request'}
        if 'service' in current_field_names and (current_command_name.startswith('hermes-flux-profile-') or current_command_name == 'hermes-delegate-flux-profile'):
            from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
            current_payload_schema['properties']['service'] = {'type':'string','enum':[*FLUX_IMAGE_PROFILE_RECORDS,'flux-expression']}
        if current_command_name == 'hermes-delegate-flux-profile':
            current_payload_schema['properties']['request'] = {'type':'object','validation':'해당 FLUX 이미지 프로필 또는 표정 생성기의 validate_generation_request'}
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
    return {'version':1, 'records':current_catalog_records, 'unlisted_commands':current_unlisted_commands, 'note':'목록에 없는 등록 명령은 지원이나 권한이 확인된 기능으로 간주하지 않는다. 표시된 인터페이스도 별도 사용자 인증·역할 권한 체계를 의미하지 않으며 입력 검증과 확인은 기존 서비스 및 클라이언트가 수행한다.'}


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
    from generators.music.service_constants import inspect_retired_audio_rejection
    from tools.review.domains.character_animation.retirement_policy import inspect_animation_retirement_policy
    from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
    from tools.review.domains.hermes_agent.audio_operations import HERMES_AUDIO_SERVICES
    from tools.review.domains.hermes_agent.video_operations import HERMES_VIDEO_SERVICES
    from tools.review.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES,SOURCE_HISTORY_AUDIO_SERVICES
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
        current_limit_records=list(HERMES_SERVICE_CONDITIONAL_LIMITATIONS.get(current_service_name,[]))
        if current_service_name in FLUX_IMAGE_PROFILE_RECORDS and current_service_name!='flux-seamless' and 'generate' in current_command_names:
            current_minimum_references=FLUX_IMAGE_PROFILE_RECORDS[current_service_name][4]
            current_reference_note='첫 참조 이미지가 필요하며 최대 2장' if current_minimum_references else '참조 이미지는 최대 2장'
            current_limit_records.append({'command':'generate','note':current_reference_note+'이고 16스텝만 허용한다.'})
        if current_service_name=='flux-expression' and 'generate' in current_command_names:
            current_limit_records.append({'command':'generate','note':'등록된 표정과 얼굴 참조 이미지 1장이 필요하며 16스텝만 허용한다.'})
        current_hermes_links=[]
        if current_service_name in HERMES_AUDIO_SERVICES:
            current_hermes_links=['hermes-delegate-audio','hermes-audio-status','hermes-audio-history','hermes-audio-source-history','hermes-audio-cancel']
        elif current_service_name in HERMES_VIDEO_SERVICES:
            current_hermes_links=['hermes-delegate-video','hermes-video-status','hermes-video-history','hermes-video-cancel']
        elif current_service_name in FLUX_IMAGE_PROFILE_RECORDS or current_service_name=='flux-expression':
            current_hermes_links=['hermes-delegate-flux-profile','hermes-flux-profile-status','hermes-flux-profile-history','hermes-flux-profile-cancel']
        elif current_service_name=='kimodo':
            current_hermes_links=['hermes-kimodo-build-status','hermes-delegate-kimodo','hermes-delegation-job-status','hermes-delegation-history','hermes-delegation-cancel','hermes-kimodo-keyframes','hermes-kimodo-keyframe-preview','hermes-kimodo-keyframe-validate']
        elif current_service_name=='writer-agent':
            current_hermes_links=['hermes-delegate-writer','hermes-writer-status','hermes-writer-history','hermes-writer-cancel','hermes-writer-reservation-preview','hermes-writer-reservation-recover','hermes-writer-reservation-receipt','hermes-writer-apply']
        elif current_service_name=='prompt-translation':
            current_hermes_links=['hermes-delegate-translation','hermes-translation-status','hermes-translation-history','hermes-translation-cancel']
        elif current_service_name=='map-assets':
            current_hermes_links=['hermes-content-database-status','hermes-building-catalog','hermes-building-preview','hermes-building-save','hermes-building-receipt','hermes-billboard-catalog','hermes-billboard-load','hermes-billboard-preview','hermes-billboard-save','hermes-effect-catalog','hermes-effect-detail','hermes-effect-preview','hermes-effect-save','hermes-effect-register-preview','hermes-effect-register','hermes-waypoint-preview','hermes-waypoint-replace','hermes-field-load','hermes-field-region','hermes-field-preview','hermes-field-save','hermes-city-load','hermes-city-preview','hermes-city-save']
        elif current_service_name=='character-animation':
            current_hermes_links=['hermes-sprite-catalog','hermes-sprite-detail','hermes-sprite-preview','hermes-sprite-save','hermes-sprite-playback','hermes-sprite-clip-playback']
        elif current_service_name=='model-downloads':
            current_hermes_links=['hermes-model-inventory']
        if current_service_name in SOURCE_HISTORY_GENERATOR_SERVICES:
            current_hermes_links.append('hermes-generator-source-history')
        if current_service_name in SOURCE_HISTORY_AUDIO_SERVICES and current_service_name not in HERMES_AUDIO_SERVICES:
            current_hermes_links.append('hermes-audio-source-history')
        if current_service_name=='flux-image':
            current_hermes_links.extend(['hermes-delegate-flux-image','hermes-flux-delegation-status','hermes-flux-delegation-history','hermes-flux-delegation-cancel','hermes-flux-proposal'])
        if current_service_name=='map-assets':
            current_hermes_links.extend(['hermes-billboard-proposal','hermes-billboard-receipt','hermes-effect-proposal','hermes-effect-receipt','hermes-effect-register-receipt','hermes-waypoint-receipt','hermes-field-proposal','hermes-field-receipt','hermes-field-history','hermes-city-receipt','hermes-city-history'])
        if current_service_name=='character-animation':
            current_hermes_links.extend(['hermes-sprite-proposal','hermes-sprite-receipt'])
        if current_service_name=='writer-agent':
            current_hermes_links.extend(['hermes-writer-apply-status','hermes-writer-apply-history'])
        if current_service_name=='prompt-translation':
            current_hermes_links.append('hermes-translation-proposal')
        if current_service_name in {current_model_name for _,current_model_name in MODEL_PREPARATION_SERVICES}:
            current_hermes_links.extend(['hermes-model-readiness','hermes-model-prepare-status'])
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
    current_matching_records=[current_record for current_record in current_catalog_value['services'] if not current_query_text or current_query_text in ' '.join((current_record['service'],*current_record['commands'],*current_record['hermes_links'],*(current_capability_labels.get(current_link_name,'') for current_link_name in current_record['hermes_links']))).casefold()]
    current_page_records=current_matching_records[current_offset_value:current_offset_value+current_limit_value]
    current_next_offset=current_offset_value+len(current_page_records)
    return {'version':current_catalog_value['version'],'services':current_page_records,'total':len(current_matching_records),'offset':current_offset_value,'next_offset':current_next_offset if current_next_offset<len(current_matching_records) else None,'note':current_catalog_value['note']}

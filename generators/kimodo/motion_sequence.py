"""명시한 구간 프레임을 공식 순차 프롬프트 입력으로 검증한다."""

def resolve_motion_segments(current_prompt_text,current_total_frames,current_segment_frames=None):
    if current_segment_frames is None:
        return [current_prompt_text],[current_total_frames]
    current_prompt_segments=[current_prompt_line.strip() for current_prompt_line in current_prompt_text.splitlines() if current_prompt_line.strip()]
    if not isinstance(current_segment_frames,list) or not 2<=len(current_segment_frames)<=10 or len(current_prompt_segments)!=len(current_segment_frames):
        raise ValueError('순차 생성은 줄마다 프롬프트 하나와 같은 개수의 구간 프레임(2~10개)이 필요합니다.')
    if any(type(current_frame_count) is not int or not 30<=current_frame_count<=300 for current_frame_count in current_segment_frames):
        raise ValueError('구간 프레임은 각각 30~300 정수여야 합니다.')
    if sum(current_segment_frames)!=current_total_frames:
        raise ValueError('구간 프레임 합계는 전체 프레임 수와 같아야 합니다.')
    return current_prompt_segments,current_segment_frames

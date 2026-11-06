"""순차 생성 중 구간 밖의 전신 제약을 빈 제약으로 안전하게 전달한다."""
from contextlib import contextmanager


@contextmanager
def support_empty_sequence_constraints(current_constraint_class):
    """공식 crop_move가 빈 관절 배열에서 방향을 계산하지 않도록 범위를 한정한다."""
    current_original_crop = current_constraint_class.crop_move

    class EmptyFullBodyConstraint(current_constraint_class):
        def __init__(self, current_frame_indices):
            self.frame_indices = current_frame_indices

        def update_constraints(self, current_data_record, current_index_record):
            return None

    def crop_sequence_constraint(current_constraint_value, current_start_frame, current_end_frame):
        current_selected_mask = (current_constraint_value.frame_indices >= current_start_frame) & (current_constraint_value.frame_indices < current_end_frame)
        if not current_selected_mask.any().item():
            return EmptyFullBodyConstraint(current_constraint_value.frame_indices[current_selected_mask])
        return current_original_crop(current_constraint_value,current_start_frame,current_end_frame)

    current_constraint_class.crop_move = crop_sequence_constraint
    try:
        yield
    finally:
        current_constraint_class.crop_move = current_original_crop

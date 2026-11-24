"""MiniMax H3 저장 입력 복원."""
from generators.minimax_h3.contracts import validate_request
from workflow.common.video_input_restore import load_video_saved_input


def load_saved_input(root,job):
    allowed={'action','prompt','width','height','frames','steps','seed'}
    return load_video_saved_input(root,job,'minimax-h3-i2v',allowed,validate_request)

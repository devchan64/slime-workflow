"""Animate 공용 영상 작업 서비스 연결."""
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager
from generators.wan_animate.contracts import ANIMATE_JOB_STORAGE, validate_animate_request, validate_animate_assets

class AnimateGenerationManager(ReferenceVideoGenerationManager):
 def __init__(self):
  super().__init__('/wan22-animate',ANIMATE_JOB_STORAGE,'generators/wan_animate/worker.py',validate_animate_request,validate_animate_assets)

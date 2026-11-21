"""기존 페이지 import 호환 경로."""
import sys
from generators.wan_animate2.page import interface as current_interface_module
sys.modules[__name__] = current_interface_module

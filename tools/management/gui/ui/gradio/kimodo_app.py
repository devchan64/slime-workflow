"""기존 Kimodo 페이지 import 호환 경로."""
import sys
from generators.kimodo.page import interface as current_interface_module
sys.modules[__name__] = current_interface_module

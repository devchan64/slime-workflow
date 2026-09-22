"""각 제작 단계를 실행하고 bpy 종료 정체 없이 성공/실패를 반환한다."""
import os,runpy,sys,traceback
from pathlib import Path
process_exit_value=0
try:
 script_source_path=Path(sys.argv[1]).resolve()
 sys.path.insert(0,str(script_source_path.parent))
 runpy.run_path(str(script_source_path),run_name='__main__')
except BaseException:
 traceback.print_exc();process_exit_value=1
finally:
 sys.stdout.flush();sys.stderr.flush();os._exit(process_exit_value)

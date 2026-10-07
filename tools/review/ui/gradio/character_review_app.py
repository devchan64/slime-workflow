"""작은 검수 맵에서 캐릭터 표현을 비교하는 Gradio 페이지."""
import argparse
from map_review_app import build_map_review_interface

if __name__=='__main__':
    current_argument_parser=argparse.ArgumentParser()
    current_argument_parser.add_argument('--port',type=int,required=True)
    current_argument_parser.add_argument('--review-port',type=int,required=True)
    current_argument_parser.add_argument('--owner-pid',type=int,required=True)
    current_argument_parser.add_argument('--root-path',default='/management/frame/character-review/')
    current_argument_values=current_argument_parser.parse_args()
    build_map_review_interface(current_argument_values.review_port,character_review_enabled=True).queue().launch(server_name='127.0.0.1',server_port=current_argument_values.port,root_path=current_argument_values.root_path,allowed_paths=[])

"""MoMask HumanML3D-22 관절 모션을 4방향 8샘플 포즈 시트로 렌더한다."""
from pathlib import Path
import argparse
import json
import numpy as np
from PIL import Image, ImageDraw

DIRECTIONS = {"down_left": 45, "down_right": -45, "up_left": 135, "up_right": -135}
EDGES = ((0,1),(0,2),(0,3),(1,4),(2,5),(3,6),(4,7),(5,8),(6,9),(7,10),(8,11),(9,12),(12,13),(12,14),(12,15),(13,16),(14,17),(16,18),(17,19),(18,20),(19,21))

def render(motion_path, output_root, sample_indices=None, frame_duration_ms=300):
    joints=np.load(motion_path)["joints"]
    if joints.ndim!=3 or joints.shape[1:]!=(22,3): raise ValueError("HumanML3D-22 관절 모션이 필요합니다.")
    sample_indices=np.array(sample_indices if sample_indices is not None else np.linspace(0,len(joints)-1,8,dtype=int), dtype=int)
    if len(sample_indices) < 1 or sample_indices.min() < 0 or sample_indices.max() >= len(joints): raise ValueError("유효한 샘플 인덱스가 필요합니다.")
    output_root=Path(output_root); output_root.mkdir(parents=True,exist_ok=True)
    for direction, angle in DIRECTIONS.items():
        radians=np.deg2rad(angle); x=joints[:,:,0]*np.cos(radians)-joints[:,:,2]*np.sin(radians); y=joints[:,:,1]
        min_x,max_x=x.min(),x.max(); min_y,max_y=y.min(),y.max(); scale=min(390/(max_x-min_x+1e-6),420/(max_y-min_y+1e-6))
        column_count=4; row_count=(len(sample_indices)+column_count-1)//column_count
        sheet=Image.new("RGB",(512*column_count,512*row_count),(12,23,17)); draw=ImageDraw.Draw(sheet)
        for cell,frame in enumerate(sample_indices):
            column, row=cell%column_count,cell//column_count; ox,oy=column*512,row*512
            draw.rectangle((ox+8,oy+8,ox+504,oy+504),outline=(62,110,77),width=2)
            points=[(ox+256+(x[frame,index]-(min_x+max_x)/2)*scale,oy+456-(y[frame,index]-min_y)*scale) for index in range(22)]
            for a,b in EDGES: draw.line((points[a],points[b]),fill=(139,228,167),width=5)
            for point in points: draw.ellipse((point[0]-5,point[1]-5,point[0]+5,point[1]+5),fill=(235,247,237))
            draw.text((ox+18,oy+18),f"{direction} · source {frame+1:02d}",fill=(198,229,207))
        sheet.save(output_root/f"{direction}.png")
    manifest={"schema_version":1,"kind":"momask-joint-pose-sheets","source_frames":len(joints),"sample_indices":sample_indices.tolist(),"directions":list(DIRECTIONS),"sheet_size":[2048,512*((len(sample_indices)+3)//4)],"cell_size":[512,512],"frame_duration_ms":frame_duration_ms}
    (output_root/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--motion",type=Path,required=True); parser.add_argument("--output-dir",type=Path,required=True); parser.add_argument("--sample-indices"); parser.add_argument("--frame-duration-ms",type=int,default=300); args=parser.parse_args(); render(args.motion,args.output_dir, [int(value) for value in args.sample_indices.split(",")] if args.sample_indices else None, args.frame_duration_ms)

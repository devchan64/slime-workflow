"""HumanML3D-22 모션을 관절 리그 미리보기 프레임으로 렌더한다."""
from pathlib import Path
import argparse
import math
import numpy as np
from PIL import Image, ImageDraw

DIRECTIONS = {"down_left": 45, "down_right": -45, "up_left": 135, "up_right": -135}
# 골반·척추·목을 중심으로 사지와 머리를 연결한다. OpenPose 색상 맵과 구분되는 리그 미리보기다.
BONES = ((0,3,20),(3,6,25),(6,9,29),(9,12,34),(12,15,48),(9,13,19),(13,16,15),(16,18,11),(18,20,9),(9,14,19),(14,17,15),(17,19,11),(19,21,9),(0,1,28),(1,4,22),(4,7,15),(7,10,10),(0,2,28),(2,5,22),(5,8,15),(8,11,10))

def render(motion_path, output_root, sample_indices):
    joints=np.load(motion_path)["joints"]
    if joints.ndim != 3 or joints.shape[1:] != (22,3): raise ValueError("HumanML3D-22 관절 모션이 필요합니다.")
    if not sample_indices or min(sample_indices)<0 or max(sample_indices)>=len(joints): raise ValueError("유효한 샘플 인덱스가 필요합니다.")
    output_root=Path(output_root)
    for direction,angle in DIRECTIONS.items():
        radians=math.radians(angle);x=joints[:,:,0]*math.cos(radians)-joints[:,:,2]*math.sin(radians);y=joints[:,:,1]
        min_x,max_x,min_y,max_y=x.min(),x.max(),y.min(),y.max();scale=min(330/(max_x-min_x+1e-6),390/(max_y-min_y+1e-6));target=output_root/direction;target.mkdir(parents=True,exist_ok=True)
        for number,frame in enumerate(sample_indices,1):
            image=Image.new("RGB",(512,512),(18,28,23));draw=ImageDraw.Draw(image)
            points=[(256+(x[frame,i]-(min_x+max_x)/2)*scale,456-(y[frame,i]-min_y)*scale) for i in range(22)]
            for start,end,width in BONES: draw.line((points[start],points[end]),fill=(197,214,202),width=width)
            for i,point in enumerate(points):
                radius=13 if i==15 else 6;draw.ellipse((point[0]-radius,point[1]-radius,point[0]+radius,point[1]+radius),fill=(101,159,117),outline=(225,239,228),width=2)
            draw.text((18,18),f"RIG · {direction} · frame {frame+1:02d}",fill=(207,232,213))
            image.save(target/f"rig-{number:04d}.png")

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--motion",type=Path,required=True);parser.add_argument("--output-dir",type=Path,required=True);parser.add_argument("--sample-indices",required=True);args=parser.parse_args()
    render(args.motion,args.output_dir,[int(value) for value in args.sample_indices.split(',')])

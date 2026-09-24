"""HumanML3D-22 관절 모션을 방향별 OpenPose 참조 이미지로 렌더한다."""
from pathlib import Path
import argparse
import math
import numpy as np
from PIL import Image, ImageDraw

DIRECTIONS = {"down_left": 45, "down_right": -45, "up_left": 135, "up_right": -135}
EDGES = ((0,1),(0,2),(0,3),(1,4),(2,5),(3,6),(4,7),(5,8),(6,9),(7,10),(8,11),(9,12),(12,13),(12,14),(12,15),(13,16),(14,17),(16,18),(17,19),(18,20),(19,21))
PALETTE = ((255,0,0),(255,85,0),(255,170,0),(255,255,0),(170,255,0),(85,255,0),(0,255,0),(0,255,85),(0,255,170),(0,255,255),(0,170,255),(0,85,255),(0,0,255),(85,0,255),(170,0,255),(255,0,255),(255,0,170),(255,0,85),(255,255,255),(170,170,255),(255,170,170))

def render(motion_path, output_root, sample_indices):
    joints = np.load(motion_path)["joints"]
    if joints.ndim != 3 or joints.shape[1:] != (22, 3):
        raise ValueError("HumanML3D-22 관절 모션이 필요합니다.")
    if not sample_indices or min(sample_indices) < 0 or max(sample_indices) >= len(joints):
        raise ValueError("유효한 샘플 인덱스가 필요합니다.")
    output_root = Path(output_root)
    for direction, angle in DIRECTIONS.items():
        radians = math.radians(angle)
        x = joints[:,:,0] * math.cos(radians) - joints[:,:,2] * math.sin(radians)
        y = joints[:,:,1]
        min_x, max_x, min_y, max_y = x.min(), x.max(), y.min(), y.max()
        scale = min(360/(max_x-min_x+1e-6), 410/(max_y-min_y+1e-6))
        target = output_root / direction
        target.mkdir(parents=True, exist_ok=True)
        for number, frame in enumerate(sample_indices, 1):
            image = Image.new("RGB", (512,512), (0,0,0))
            draw = ImageDraw.Draw(image)
            points = [(256+(x[frame,index]-(min_x+max_x)/2)*scale,456-(y[frame,index]-min_y)*scale) for index in range(22)]
            for edge_index, (start,end) in enumerate(EDGES):
                draw.line((points[start],points[end]), fill=PALETTE[edge_index % len(PALETTE)], width=7)
            for index, point in enumerate(points):
                draw.ellipse((point[0]-7,point[1]-7,point[0]+7,point[1]+7), fill=PALETTE[index % len(PALETTE)])
            image.save(target / f"openpose-{number:04d}.png")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sample-indices", required=True)
    args = parser.parse_args()
    render(args.motion, args.output_dir, [int(value) for value in args.sample_indices.split(",")])

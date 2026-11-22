"""Render eight depth-buffered orthographic views of a Z-up mesh."""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import trimesh
from workflow.domains.unirig_experiment.render_combat import raster


def main(source, output, colored):
    mesh = trimesh.load(source, force='mesh', process=False)
    if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
        raise ValueError('Invalid mesh')
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    vertices -= (vertices.min(axis=0) + vertices.max(axis=0)) / 2
    extent = np.ptp(vertices, axis=0).max()
    if extent <= 0: raise ValueError('Empty extent')
    faces = np.asarray(mesh.faces, dtype=np.int32)
    shade = np.clip(.55 + .45 * np.abs(mesh.face_normals @ np.array([.4, -.6, .69])), 0, 1)
    if colored:
        base = np.asarray(mesh.visual.vertex_colors)[:, :3][faces].mean(axis=1)
    else:
        base = np.full((len(faces),3), 190.0)
    colors = (base * shade[:, None]).clip(0,255).astype(np.uint8)
    sheet = Image.new('RGB', (2048, 1024), (240,240,240))
    for index in range(8):
        angle = index * np.pi / 4
        right = np.array([np.cos(angle), np.sin(angle), 0.0])
        toward = np.array([-np.sin(angle), np.cos(angle), 0.0])
        points = np.stack((vertices @ right, vertices[:,2]), axis=1) * (440 / extent) + [256,256]
        points[:,1] = 512-points[:,1]
        view = Image.fromarray(raster(points, vertices @ toward, faces, colors))
        ImageDraw.Draw(view).text((12,12), f'view {index+1}', fill=(20,20,20))
        sheet.paste(view, ((index % 4) * 512, (index // 4) * 512))
    sheet.save(output)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--colored', action='store_true')
    args=parser.parse_args()
    main(args.source,args.output,args.colored)

"""원본 관절 위치를 정면·측면으로 투영한다. 모션 보정은 하지 않는다."""
PREVIEW_IMAGE_WIDTH = 640
PREVIEW_IMAGE_HEIGHT = 480
PREVIEW_PANEL_WIDTH = 320
PREVIEW_PANEL_MARGIN = 24


def render_kimodo_frames(current_joint_positions,current_joint_parents):
    import numpy as np
    from PIL import Image,ImageDraw
    current_minimum_position = current_joint_positions.min(axis=(0,1))
    current_maximum_position = current_joint_positions.max(axis=(0,1))
    current_center_position = (current_minimum_position+current_maximum_position)/2
    current_extent_values = np.maximum(current_maximum_position-current_minimum_position,0.1)
    current_render_scale = min((PREVIEW_PANEL_WIDTH-2*PREVIEW_PANEL_MARGIN)/max(current_extent_values[0],current_extent_values[2]),(PREVIEW_IMAGE_HEIGHT-4*PREVIEW_PANEL_MARGIN)/current_extent_values[1])
    current_preview_frames = []
    for current_frame_index,current_frame_joints in enumerate(current_joint_positions):
        current_preview_image = Image.new('RGB',(PREVIEW_IMAGE_WIDTH,PREVIEW_IMAGE_HEIGHT),'#f2f2f2')
        current_drawing_context = ImageDraw.Draw(current_preview_image)
        for current_panel_index,current_horizontal_axis in enumerate((0,2)):
            current_panel_center = PREVIEW_PANEL_WIDTH*(current_panel_index+0.5)
            current_screen_points = [(float(current_panel_center+(current_joint[ current_horizontal_axis]-current_center_position[current_horizontal_axis])*current_render_scale),float(PREVIEW_IMAGE_HEIGHT/2-(current_joint[1]-current_center_position[1])*current_render_scale)) for current_joint in current_frame_joints]
            for current_joint_index,current_parent_index in enumerate(current_joint_parents):
                if current_parent_index >= 0:
                    current_drawing_context.line([current_screen_points[current_parent_index],current_screen_points[current_joint_index]],fill='#145887',width=3)
            current_drawing_context.text((current_panel_index*PREVIEW_PANEL_WIDTH+12,12),'FRONT (X/Y)' if current_panel_index==0 else 'SIDE (Z/Y)',fill='black')
        current_drawing_context.text((12,PREVIEW_IMAGE_HEIGHT-24),f'{current_frame_index+1}/{len(current_joint_positions)}  SOMA77  30fps',fill='black')
        current_preview_frames.append(np.asarray(current_preview_image))
    return current_preview_frames

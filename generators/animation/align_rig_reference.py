"""단색 배경의 리그 입력을 캐릭터 실루엣 범위에 정렬한다."""
from PIL import Image, ImageChops

def align_rig_reference(character_image_value, pose_image_value):
    if character_image_value.size!=(512,512) or pose_image_value.size!=(512,512):raise ValueError('512×512 입력만 지원합니다.')
    character_rgb_image=character_image_value.convert('RGB')
    pose_rgb_image=pose_image_value.convert('RGB')
    def find_foreground_bounds(source_image_value, background_rgb_value):
        difference_image_value=ImageChops.difference(source_image_value,Image.new('RGB',source_image_value.size,background_rgb_value))
        foreground_mask_image=difference_image_value.convert('L').point(lambda channel_value:255 if channel_value>35 else 0)
        foreground_bounds_value=foreground_mask_image.getbbox()
        if foreground_bounds_value is None:raise ValueError('전경 실루엣을 찾을 수 없습니다.')
        return foreground_bounds_value
    character_bounds_value=find_foreground_bounds(character_rgb_image,'white')
    pose_bounds_value=find_foreground_bounds(pose_rgb_image,'black')
    target_width_value=character_bounds_value[2]-character_bounds_value[0]
    target_height_value=character_bounds_value[3]-character_bounds_value[1]
    aligned_pose_image=Image.new('RGB',pose_rgb_image.size,'black')
    aligned_pose_image.paste(pose_rgb_image.crop(pose_bounds_value).resize((target_width_value,target_height_value),Image.Resampling.LANCZOS),character_bounds_value[:2])
    return aligned_pose_image,{'method':'silhouette-bounds-v1','character_bounds':character_bounds_value,'pose_bounds':pose_bounds_value,'scale_x':target_width_value/(pose_bounds_value[2]-pose_bounds_value[0]),'scale_y':target_height_value/(pose_bounds_value[3]-pose_bounds_value[1]),'limitation':'전체 실루엣 범위 정렬이며 관절별 체형 리타깃은 아님; 동일 방향 대기 포즈 검증용'}

"""ANNY 손가락을 손바닥 안쪽으로 굽히는 고정 주먹 자세."""
import math
from mathutils import Vector, Quaternion

FINGER_CURL_DEGREES=(65,80,55)
THUMB_CURL_DEGREES=(25,35,30)

def build_fist_rotations(character_rig_object):
    finger_rotation_values={}
    for hand_side_label in ('L','R'):
        wrist_bone_value=character_rig_object.data.bones['wrist.'+hand_side_label]
        index_bone_value=character_rig_object.data.bones['finger2-1.'+hand_side_label]
        pinky_bone_value=character_rig_object.data.bones['finger5-1.'+hand_side_label]
        palm_length_direction=((index_bone_value.head_local+pinky_bone_value.head_local)/2-wrist_bone_value.head_local).normalized()
        palm_width_direction=(pinky_bone_value.head_local-index_bone_value.head_local).normalized()
        palm_inward_normal=palm_length_direction.cross(palm_width_direction).normalized()
        torso_inward_direction=Vector((-wrist_bone_value.head_local.x,0,0))
        if palm_inward_normal.dot(torso_inward_direction)<0:palm_inward_normal=-palm_inward_normal
        for finger_number_value in range(1,6):
            for finger_segment_index in range(1,4):
                finger_bone_name=f'finger{finger_number_value}-{finger_segment_index}.{hand_side_label}'
                finger_bone_value=character_rig_object.data.bones[finger_bone_name]
                finger_length_direction=(finger_bone_value.tail_local-finger_bone_value.head_local).normalized()
                finger_bend_axis=finger_length_direction.cross(palm_inward_normal).normalized()
                local_bend_axis=finger_bone_value.matrix_local.to_quaternion().inverted()@finger_bend_axis
                curl_angle_values=THUMB_CURL_DEGREES if finger_number_value==1 else FINGER_CURL_DEGREES
                finger_rotation_values[finger_bone_name]=Quaternion(local_bend_axis,math.radians(curl_angle_values[finger_segment_index-1]))
    return finger_rotation_values

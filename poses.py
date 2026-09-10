POSES = {

    "neutral": {
        "left_eye_scale_y": 1.0,
        "right_eye_scale_y": 1.0,

        "left_pupil_x": 0,
        "left_pupil_y": 0,

        "right_pupil_x": 0,
        "right_pupil_y": 0,
    },

    "happy": {
        "left_eye_scale_y": 0.88,
        "right_eye_scale_y": 0.88,

        "left_pupil_x": 0,
        "left_pupil_y": -2,

        "right_pupil_x": 0,
        "right_pupil_y": -2,
    },

    "angry": {
        "left_eye_scale_y": 0.82,
        "right_eye_scale_y": 0.82,

        "left_pupil_x": 0,
        "left_pupil_y": 1,

        "right_pupil_x": 0,
        "right_pupil_y": 1,
    },

    "sad": {
        "left_eye_scale_y": 0.92,
        "right_eye_scale_y": 0.92,

        "left_pupil_x": 0,
        "left_pupil_y": 3,

        "right_pupil_x": 0,
        "right_pupil_y": 3,
    }
}


def set_pose(state, pose_name):

    if pose_name not in POSES:
        return

    pose = POSES[pose_name]

    for key, value in pose.items():
        setattr(state, key, value)

    state.pose = pose_name
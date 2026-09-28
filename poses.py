POSES = {

    "neutral": {
        "eye_scale_y": 1.0,
        "pupil_x": 0,
        "pupil_y": 0,
    },

    "happy": {
        "eye_scale_y": 0.88,
        "pupil_x": 0,
        "pupil_y": -2,
    },

    "angry": {
        "eye_scale_y": 0.82,
        "pupil_x": 0,
        "pupil_y": 1,
    },

    "sad": {
        "eye_scale_y": 0.92,
        "pupil_x": 0,
        "pupil_y": 3,
    }
}


def set_pose(state, pose_name):

    if pose_name not in POSES:
        return

    pose = POSES[pose_name]

    # These are targets, not the displayed values - CharacterState
    # eases eye scale and pupil position toward them every frame
    # (see CharacterState.update_smoothing), so switching emotions
    # doesn't snap.
    #
    # pose_left/right_eye_target is read every frame by IdleAnimator
    # to decide what to ease the displayed eye scale toward when not
    # mid-blink, so a pose change mid-blink resolves correctly on
    # its own once the blink finishes.

    state.pose_left_eye_target = pose["eye_scale_y"]
    state.pose_right_eye_target = pose["eye_scale_y"]

    state.target_pose_left_pupil_x = pose["pupil_x"]
    state.target_pose_left_pupil_y = pose["pupil_y"]

    state.target_pose_right_pupil_x = pose["pupil_x"]
    state.target_pose_right_pupil_y = pose["pupil_y"]

    state.pose = pose_name

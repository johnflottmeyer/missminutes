POSES = {

    "neutral": {
        "eye_scale_y": 1.0,
        "pupil_x": 0,
        "pupil_y": 0,
        "left_upper_arm": -18,
        "left_lower_arm": -10,
        "right_upper_arm": 18,
        "right_lower_arm": 10,
        "left_upper_leg": -8,
        "left_lower_leg": 3,
        "right_upper_leg": 8,
        "right_lower_leg": -3,
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

    # Limb targets. Poses without explicit limb values keep the
    # neutral stance for now; we'll give each emotion its own body
    # language after the base proportions are visually approved.
    neutral = POSES["neutral"]
    for name in (
        "left_upper_arm", "left_lower_arm",
        "right_upper_arm", "right_lower_arm",
        "left_upper_leg", "left_lower_leg",
        "right_upper_leg", "right_lower_leg"
    ):
        setattr(
            state,
            "target_" + name,
            pose.get(name, neutral[name])
        )

    state.pose = pose_name

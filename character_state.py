import math


# ==========================
# SMOOTHING RATES
# ==========================
# Higher = closes the gap to target faster. These are tuned by feel,
# not derived from anything physical - adjust freely.
#
# Modeled as an exponential approach: after 1/rate seconds the
# displayed value has closed about 63% of the remaining distance to
# its target, regardless of frame rate (unlike a fixed per-frame
# step, which speeds up or slows down if FPS changes).

MOUTH_ATTACK_RATE = 34.0     # mouth opening - fast, a mouth opens quickly
MOUTH_RELEASE_RATE = 20.0    # mouth closing - a touch slower, softer

EYE_RATE = 26.0              # eyelid scale - covers both blinks and
                              # expression changes with one rate

POSE_PUPIL_RATE = 12.0       # pupil offset from the current emotion
IDLE_PUPIL_RATE = 10.0       # pupil offset from idle wandering


def _approach(current, target, rate, dt):

    if rate <= 0:
        return target

    blend = 1.0 - math.exp(-rate * dt)

    return current + (target - current) * blend


class CharacterState:

    def __init__(self):

        # ==========================
        # POSITION
        # ==========================

        self.x = 157
        self.y = 250


        # ==========================
        # FACE / MOUTH
        # ==========================
        # mouth_shape switches instantly - it's one of a handful of
        # drawn shapes, not something that benefits from blending
        # into a shape it isn't. mouth_open eases toward
        # target_mouth_open every frame instead, which is what
        # actually reads as a moving mouth rather than a slideshow.

        self.mouth_shape = "REST"

        self.mouth_open = 0.0
        self.target_mouth_open = 0.0


        # ==========================
        # EYES - RESTING SHAPE (FROM POSE)
        # ==========================
        # pose_*_eye_target holds the current emotion's resting
        # eyelid scale. It's written only by poses.set_pose() and
        # only ever read elsewhere, so it always reflects "what this
        # emotion looks like when not blinking", even if something
        # asks mid-blink.

        self.pose_left_eye_target = 1.0
        self.pose_right_eye_target = 1.0


        # ==========================
        # EYES - DISPLAYED SCALE
        # ==========================
        # target_left/right_eye_scale_y is recomputed every frame by
        # IdleAnimator: the blink-closed value while a blink is in
        # progress, otherwise pose_*_eye_target. left/right_eye_scale_y
        # is the smoothed result renderer.py actually draws.

        self.target_left_eye_scale_y = 1.0
        self.target_right_eye_scale_y = 1.0

        self.left_eye_scale_y = 1.0
        self.right_eye_scale_y = 1.0


        # ==========================
        # PUPILS - TWO INDEPENDENT SOURCES
        # ==========================
        # Final pupil position is the current emotion's own offset
        # plus a separate idle "wander" offset, added together each
        # frame. Previously idle's look-around code overwrote the
        # pose's pupil offset outright, so e.g. "sad" eyes would pop
        # back to a neutral look every time idle glanced around or
        # recentered. Keeping the two sources separate means idle
        # wandering rides on top of whatever the current emotion
        # already looks like, instead of replacing it.

        self.target_pose_left_pupil_x = 0.0
        self.target_pose_left_pupil_y = 0.0

        self.target_pose_right_pupil_x = 0.0
        self.target_pose_right_pupil_y = 0.0

        self.pose_left_pupil_x = 0.0
        self.pose_left_pupil_y = 0.0

        self.pose_right_pupil_x = 0.0
        self.pose_right_pupil_y = 0.0

        self.target_idle_left_pupil_x = 0.0
        self.target_idle_left_pupil_y = 0.0

        self.target_idle_right_pupil_x = 0.0
        self.target_idle_right_pupil_y = 0.0

        self.idle_left_pupil_x = 0.0
        self.idle_left_pupil_y = 0.0

        self.idle_right_pupil_x = 0.0
        self.idle_right_pupil_y = 0.0


        # ==========================
        # PUPILS - DISPLAYED (pose + idle)
        # ==========================
        # renderer.py only ever reads these four fields - it has no
        # idea pupil position is a blend of two sources underneath.

        self.left_pupil_x = 0.0
        self.left_pupil_y = 0.0

        self.right_pupil_x = 0.0
        self.right_pupil_y = 0.0


        # ==========================
        # CURRENT EXPRESSION
        # ==========================

        self.pose = "neutral"


    # ==========================
    # SMOOTHING
    # ==========================

    def update_smoothing(self, dt):
        """
        Eases every displayed value toward its current target and
        recomputes the pupil blend. Call this once per frame, after
        idle/poses/speech have updated their targets for the frame,
        and before drawing.
        """

        # ----------------------------------
        # Mouth (asymmetric attack/release)
        # ----------------------------------

        if self.target_mouth_open > self.mouth_open:
            mouth_rate = MOUTH_ATTACK_RATE
        else:
            mouth_rate = MOUTH_RELEASE_RATE

        self.mouth_open = _approach(
            self.mouth_open,
            self.target_mouth_open,
            mouth_rate,
            dt
        )


        # ----------------------------------
        # Eyes
        # ----------------------------------

        self.left_eye_scale_y = _approach(
            self.left_eye_scale_y,
            self.target_left_eye_scale_y,
            EYE_RATE,
            dt
        )

        self.right_eye_scale_y = _approach(
            self.right_eye_scale_y,
            self.target_right_eye_scale_y,
            EYE_RATE,
            dt
        )


        # ----------------------------------
        # Pupils - pose baseline
        # ----------------------------------

        self.pose_left_pupil_x = _approach(
            self.pose_left_pupil_x,
            self.target_pose_left_pupil_x,
            POSE_PUPIL_RATE,
            dt
        )

        self.pose_left_pupil_y = _approach(
            self.pose_left_pupil_y,
            self.target_pose_left_pupil_y,
            POSE_PUPIL_RATE,
            dt
        )

        self.pose_right_pupil_x = _approach(
            self.pose_right_pupil_x,
            self.target_pose_right_pupil_x,
            POSE_PUPIL_RATE,
            dt
        )

        self.pose_right_pupil_y = _approach(
            self.pose_right_pupil_y,
            self.target_pose_right_pupil_y,
            POSE_PUPIL_RATE,
            dt
        )


        # ----------------------------------
        # Pupils - idle wander
        # ----------------------------------

        self.idle_left_pupil_x = _approach(
            self.idle_left_pupil_x,
            self.target_idle_left_pupil_x,
            IDLE_PUPIL_RATE,
            dt
        )

        self.idle_left_pupil_y = _approach(
            self.idle_left_pupil_y,
            self.target_idle_left_pupil_y,
            IDLE_PUPIL_RATE,
            dt
        )

        self.idle_right_pupil_x = _approach(
            self.idle_right_pupil_x,
            self.target_idle_right_pupil_x,
            IDLE_PUPIL_RATE,
            dt
        )

        self.idle_right_pupil_y = _approach(
            self.idle_right_pupil_y,
            self.target_idle_right_pupil_y,
            IDLE_PUPIL_RATE,
            dt
        )


        # ----------------------------------
        # Pupils - final blend (what renderer.py reads)
        # ----------------------------------

        self.left_pupil_x = (
            self.pose_left_pupil_x
            + self.idle_left_pupil_x
        )

        self.left_pupil_y = (
            self.pose_left_pupil_y
            + self.idle_left_pupil_y
        )

        self.right_pupil_x = (
            self.pose_right_pupil_x
            + self.idle_right_pupil_x
        )

        self.right_pupil_y = (
            self.pose_right_pupil_y
            + self.idle_right_pupil_y
        )

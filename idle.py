import random


# ==========================
# BLINK TIMING
# ==========================

BLINK_CLOSED_SCALE = 0.08

BLINK_CLOSE_TIME = 0.05
BLINK_HOLD_TIME = 0.05
BLINK_OPEN_TIME = 0.06


class IdleAnimator:

    def __init__(self):

        # Look timing
        self.look_timer = 0.0
        self.action_timer = 0.0
        self.next_action = random.uniform(1.5, 3.5)

        # Blink timing - a small state machine (closing -> held ->
        # opening -> none) instead of an instant on/off, so the
        # eyelid eases shut and back open rather than a hard cut.
        self.blink_timer = 0.0
        self.next_blink = random.uniform(2.0, 4.5)
        self.blink_phase = "none"


    @property
    def blinking(self):
        return self.blink_phase != "none"


    def update(self, state, dt, speaking=False):

        # ==========================
        # BLINK
        # ==========================
        # Writes into state.target_left/right_eye_scale_y every
        # frame; CharacterState eases the displayed scale toward
        # whichever target this produces, using the same smoothing
        # pass that handles ordinary expression changes. There's no
        # save/restore of a snapshot - "not blinking" always means
        # "ease toward whatever the current pose says", read fresh
        # each frame, so a pose change mid-blink just resolves
        # itself once the blink ends instead of needing special
        # handling.

        self.blink_timer += dt

        if self.blink_phase == "none":

            if self.blink_timer >= self.next_blink:

                self.blink_phase = "closing"
                self.blink_timer = 0.0

        elif self.blink_phase == "closing":

            if self.blink_timer >= BLINK_CLOSE_TIME:

                self.blink_phase = "held"
                self.blink_timer = 0.0

        elif self.blink_phase == "held":

            if self.blink_timer >= BLINK_HOLD_TIME:

                self.blink_phase = "opening"
                self.blink_timer = 0.0

        elif self.blink_phase == "opening":

            if self.blink_timer >= BLINK_OPEN_TIME:

                self.blink_phase = "none"
                self.blink_timer = 0.0

                self.next_blink = random.uniform(2.0, 4.5)


        if self.blink_phase in ("closing", "held"):

            state.target_left_eye_scale_y = BLINK_CLOSED_SCALE
            state.target_right_eye_scale_y = BLINK_CLOSED_SCALE

        else:

            state.target_left_eye_scale_y = state.pose_left_eye_target
            state.target_right_eye_scale_y = state.pose_right_eye_target


        # ==========================
        # DON'T DO LARGE IDLE LOOKS
        # WHILE SPEAKING
        # ==========================

        if speaking:
            return


        # ==========================
        # RETURN EYES TO CENTER
        # ==========================
        # This only resets the idle wander offset, not the current
        # emotion's own pupil position (see character_state.py) -
        # so recentering after a glance doesn't erase e.g. "sad"
        # eyes back to a neutral look.

        if self.look_timer > 0:

            self.look_timer -= dt

            if self.look_timer <= 0:

                state.target_idle_left_pupil_x = 0
                state.target_idle_left_pupil_y = 0

                state.target_idle_right_pupil_x = 0
                state.target_idle_right_pupil_y = 0


        # ==========================
        # RANDOM IDLE LOOK
        # ==========================

        self.action_timer += dt

        if self.action_timer >= self.next_action:

            self.action_timer = 0.0

            self.next_action = random.uniform(
                1.8,
                4.0
            )

            action = random.choice([
                "look_left",
                "look_right",
                "look_up",
                "look_down",
                "center"
            ])


            if action == "look_left":

                state.target_idle_left_pupil_x = -5
                state.target_idle_right_pupil_x = -5

                state.target_idle_left_pupil_y = 0
                state.target_idle_right_pupil_y = 0

                self.look_timer = 0.8


            elif action == "look_right":

                state.target_idle_left_pupil_x = 5
                state.target_idle_right_pupil_x = 5

                state.target_idle_left_pupil_y = 0
                state.target_idle_right_pupil_y = 0

                self.look_timer = 0.8


            elif action == "look_up":

                state.target_idle_left_pupil_x = 0
                state.target_idle_right_pupil_x = 0

                state.target_idle_left_pupil_y = -4
                state.target_idle_right_pupil_y = -4

                self.look_timer = 0.7


            elif action == "look_down":

                state.target_idle_left_pupil_x = 0
                state.target_idle_right_pupil_x = 0

                state.target_idle_left_pupil_y = 4
                state.target_idle_right_pupil_y = 4

                self.look_timer = 0.6


            elif action == "center":

                state.target_idle_left_pupil_x = 0
                state.target_idle_left_pupil_y = 0

                state.target_idle_right_pupil_x = 0
                state.target_idle_right_pupil_y = 0

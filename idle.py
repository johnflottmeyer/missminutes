import random


class IdleAnimator:

    def __init__(self):

        # Look timing
        self.look_timer = 0.0
        self.action_timer = 0.0
        self.next_action = random.uniform(1.5, 3.5)

        # Blink timing
        self.blink_timer = 0.0
        self.next_blink = random.uniform(2.0, 4.5)

        self.blinking = False

        # Remember expression eye shape
        self.saved_left_eye_scale = 1.0
        self.saved_right_eye_scale = 1.0


    def update(self, state, dt, speaking=False):

        # ==========================
        # BLINK
        # ==========================

        self.blink_timer += dt

        if not self.blinking:

            if self.blink_timer >= self.next_blink:

                self.blinking = True
                self.blink_timer = 0.0

                # Remember current expression eye shape
                self.saved_left_eye_scale = state.left_eye_scale_y
                self.saved_right_eye_scale = state.right_eye_scale_y

                # Close eyes
                state.left_eye_scale_y = 0.08
                state.right_eye_scale_y = 0.08

        else:

            # Keep eyes closed briefly
            if self.blink_timer >= 0.12:

                self.blinking = False
                self.blink_timer = 0.0

                # Restore expression eye shape
                state.left_eye_scale_y = self.saved_left_eye_scale
                state.right_eye_scale_y = self.saved_right_eye_scale

                self.next_blink = random.uniform(
                    2.0,
                    4.5
                )


        # ==========================
        # DON'T DO LARGE IDLE LOOKS
        # WHILE SPEAKING
        # ==========================

        if speaking:
            return


        # ==========================
        # RETURN EYES TO CENTER
        # ==========================

        if self.look_timer > 0:

            self.look_timer -= dt

            if self.look_timer <= 0:

                state.left_pupil_x = 0
                state.left_pupil_y = 0

                state.right_pupil_x = 0
                state.right_pupil_y = 0


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

                state.left_pupil_x = -5
                state.right_pupil_x = -5

                state.left_pupil_y = 0
                state.right_pupil_y = 0

                self.look_timer = 0.8


            elif action == "look_right":

                state.left_pupil_x = 5
                state.right_pupil_x = 5

                state.left_pupil_y = 0
                state.right_pupil_y = 0

                self.look_timer = 0.8


            elif action == "look_up":

                state.left_pupil_x = 0
                state.right_pupil_x = 0

                state.left_pupil_y = -4
                state.right_pupil_y = -4

                self.look_timer = 0.7


            elif action == "look_down":

                state.left_pupil_x = 0
                state.right_pupil_x = 0

                state.left_pupil_y = 4
                state.right_pupil_y = 4

                self.look_timer = 0.6


            elif action == "center":

                state.left_pupil_x = 0
                state.left_pupil_y = 0

                state.right_pupil_x = 0
                state.right_pupil_y = 0
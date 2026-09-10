import random


class SpeechAnimator:

    def __init__(self):

        self.text = ""
        self.index = 0

        self.timer = 0.0
        self.next_change = 0.08

        self.speaking = False

        # Remember the current mouth so
        # consonants can hold it instead
        # of constantly changing shape.
        self.current_shape = "REST"
        self.current_open = 0.0


    # ==========================
    # START
    # ==========================

    def start(self, text):

        if not text:
            return

        self.text = text.lower()
        self.index = 0

        self.timer = 0.0
        self.next_change = 0.03

        self.speaking = True

        self.current_shape = "REST"
        self.current_open = 0.0


    # ==========================
    # STOP
    # ==========================

    def stop(self, state):

        self.speaking = False

        self.current_shape = "REST"
        self.current_open = 0.0

        state.mouth_shape = "REST"
        state.mouth_open = 0.0

        state.left_pupil_x = 0
        state.left_pupil_y = 0

        state.right_pupil_x = 0
        state.right_pupil_y = 0


    # ==========================
    # SET MOUTH
    # ==========================

    def set_mouth(
        self,
        state,
        shape,
        openness,
        duration
    ):

        self.current_shape = shape
        self.current_open = openness

        state.mouth_shape = shape
        state.mouth_open = openness

        self.next_change = duration


    # ==========================
    # HOLD CURRENT MOUTH
    # ==========================

    def hold_mouth(
        self,
        state,
        duration
    ):

        state.mouth_shape = self.current_shape
        state.mouth_open = self.current_open

        self.next_change = duration


    # ==========================
    # UPDATE
    # ==========================

    def update(self, state, dt):

        if not self.speaking:
            return


        self.timer += dt

        if self.timer < self.next_change:
            return

        self.timer = 0.0


        # ==========================
        # END OF TEXT
        # ==========================

        if self.index >= len(self.text):

            self.stop(state)
            return


        remaining = self.text[
            self.index:
        ]

        char = remaining[0]


        # ==========================
        # PUNCTUATION
        # ==========================

        if char in ".!?":

            self.index += 1

            self.set_mouth(
                state,
                "REST",
                0.0,
                0.16
            )

            return


        if char in ",;:":

            self.index += 1

            self.set_mouth(
                state,
                "REST",
                0.0,
                0.09
            )

            return


        # ==========================
        # SPACE BETWEEN WORDS
        # ==========================

        if char.isspace():

            self.index += 1

            # Very short reset.
            # We don't want a visible
            # stop after every word.

            self.set_mouth(
                state,
                "REST",
                0.0,
                0.035
            )

            return


        # ==========================
        # THREE-LETTER CHUNKS
        # ==========================

        three = remaining[:3]


        # ING
        if three == "ing":

            self.index += 3

            self.set_mouth(
                state,
                "EE",
                0.24,
                0.115
            )

            return


        # ==========================
        # TWO-LETTER CHUNKS
        # ==========================

        two = remaining[:2]


        # --------------------------
        # SH / CH
        # --------------------------

        if two in (
            "sh",
            "ch"
        ):

            self.index += 2

            self.set_mouth(
                state,
                "OH",
                0.22,
                0.085
            )

            return


        # --------------------------
        # TH
        # --------------------------

        if two == "th":

            self.index += 2

            self.set_mouth(
                state,
                "FV",
                0.14,
                0.075
            )

            return


        # --------------------------
        # PH
        # --------------------------

        if two == "ph":

            self.index += 2

            self.set_mouth(
                state,
                "FV",
                0.14,
                0.075
            )

            return


        # --------------------------
        # EE SOUNDS
        # --------------------------

        if two in (
            "ee",
            "ea",
            "ie"
        ):

            self.index += 2

            self.set_mouth(
                state,
                "EE",
                0.26,
                0.12
            )

            return


        # --------------------------
        # ROUND SOUNDS
        # --------------------------

        if two in (
            "oo",
            "ou"
        ):

            self.index += 2

            self.set_mouth(
                state,
                "OH",
                0.42,
                0.125
            )

            return


        # --------------------------
        # OW
        # --------------------------

        if two == "ow":

            self.index += 2

            self.set_mouth(
                state,
                "OH",
                0.48,
                0.13
            )

            return


        # --------------------------
        # OPEN / DIPHTHONG
        # --------------------------

        if two in (
            "ai",
            "ay"
        ):

            self.index += 2

            self.set_mouth(
                state,
                "AA",
                0.44,
                0.12
            )

            return


        if two in (
            "au",
            "aw"
        ):

            self.index += 2

            self.set_mouth(
                state,
                "AA",
                0.48,
                0.125
            )

            return


        # --------------------------
        # OY / OI
        # --------------------------

        if two in (
            "oy",
            "oi"
        ):

            self.index += 2

            self.set_mouth(
                state,
                "OH",
                0.38,
                0.12
            )

            return


        # ==========================
        # SINGLE LETTER
        # ==========================

        self.index += 1


        # --------------------------
        # M / B / P
        # --------------------------

        if char in "mbp":

            self.set_mouth(
                state,
                "MBP",
                0.02,
                0.055
            )


        # --------------------------
        # F / V
        # --------------------------

        elif char in "fv":

            self.set_mouth(
                state,
                "FV",
                0.14,
                0.060
            )


        # --------------------------
        # A
        # --------------------------

        elif char == "a":

            self.set_mouth(
                state,
                "AA",
                0.44,
                0.095
            )


        # --------------------------
        # E / I
        # --------------------------

        elif char in "ei":

            self.set_mouth(
                state,
                "EE",
                0.24,
                0.090
            )


        # --------------------------
        # O / U
        # --------------------------

        elif char in "ou":

            self.set_mouth(
                state,
                "OH",
                0.38,
                0.095
            )


        # --------------------------
        # W
        # --------------------------

        elif char == "w":

            self.set_mouth(
                state,
                "OH",
                0.24,
                0.060
            )


        # --------------------------
        # R
        # --------------------------

        elif char == "r":

            # R changes the lips slightly,
            # but doesn't need a big motion.

            self.set_mouth(
                state,
                "OH",
                0.20,
                0.055
            )


        # --------------------------
        # L / Y
        # --------------------------

        elif char in "ly":

            self.set_mouth(
                state,
                "EE",
                0.18,
                0.055
            )


        # ==========================
        # OTHER CONSONANTS
        # ==========================

        else:

            # This is the big change:
            #
            # T, D, K, G, N, S, etc.
            # usually don't need the lips
            # to jump into a totally new
            # visible shape.
            #
            # Hold whatever the mouth was
            # already doing.

            self.hold_mouth(
                state,
                random.uniform(
                    0.035,
                    0.055
                )
            )
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

        # Older compatibility value
        self.mouth = 0.20

        self.mouth_width = 28
        self.mouth_y = 25

        # New viseme-style mouth system
        self.mouth_shape = "REST"
        self.mouth_open = 0.0


        # ==========================
        # EYES
        # ==========================

        self.left_eye_scale_y = 1.0
        self.right_eye_scale_y = 1.0

        self.left_pupil_x = 0
        self.left_pupil_y = 0

        self.right_pupil_x = 0
        self.right_pupil_y = 0


        # ==========================
        # BLINK
        # ==========================

        self.left_blink = 0.0
        self.right_blink = 0.0


        # ==========================
        # ARMS
        # ==========================

        self.left_upper = 0
        self.left_lower = 0

        self.right_upper = 0
        self.right_lower = 0


        # ==========================
        # CURRENT EXPRESSION
        # ==========================

        self.pose = "neutral"
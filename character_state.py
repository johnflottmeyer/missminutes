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
        # CURRENT EXPRESSION
        # ==========================

        self.pose = "neutral"
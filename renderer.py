import math
import pygame


# ==========================
# COLORS
# ==========================

BLACK = (0, 0, 0)

FACE_ORANGE = (244, 151, 28)
FACE_EDGE = (184, 72, 24)

EYE_WHITE = (255, 247, 218)
EYE_OUTLINE = (163, 67, 28)

PUPIL_DARK = (67, 39, 25)
PUPIL_ORANGE = (205, 82, 24)

MOUTH_COLOR = (120, 48, 25)

TEETH_COLOR = (255, 244, 220)
TONGUE_COLOR = (188, 73, 52)


# ==========================
# HEAD
# ==========================

HEAD_RADIUS = 110


def draw_head(surface, cx, cy):

    pygame.draw.circle(
        surface,
        FACE_EDGE,
        (cx, cy),
        HEAD_RADIUS + 4
    )

    pygame.draw.circle(
        surface,
        FACE_ORANGE,
        (cx, cy),
        HEAD_RADIUS
    )


# ==========================
# CLOCK MARKINGS
# ==========================

def draw_clock_marks(surface, cx, cy):

    mark_color = FACE_EDGE

    for hour in range(12):

        angle = math.radians(
            hour * 30 - 90
        )

        if hour % 3 == 0:

            outer_r = 94
            inner_r = 80
            width = 6

        else:

            outer_r = 92
            inner_r = 84
            width = 4


        x1 = (
            cx
            + math.cos(angle)
            * inner_r
        )

        y1 = (
            cy
            + math.sin(angle)
            * inner_r
        )

        x2 = (
            cx
            + math.cos(angle)
            * outer_r
        )

        y2 = (
            cy
            + math.sin(angle)
            * outer_r
        )


        pygame.draw.line(
            surface,
            mark_color,
            (
                int(x1),
                int(y1)
            ),
            (
                int(x2),
                int(y2)
            ),
            width
        )


# ==========================
# EYE
# ==========================

def draw_eye(
    surface,
    x,
    y,
    width,
    height,
    lash_side="left"
):

    points = [

        (
            x,
            y - height * 0.50
        ),

        (
            x - width * 0.28,
            y - height * 0.43
        ),

        (
            x - width * 0.46,
            y - height * 0.18
        ),

        (
            x - width * 0.50,
            y + height * 0.10
        ),

        (
            x - width * 0.42,
            y + height * 0.34
        ),

        (
            x - width * 0.22,
            y + height * 0.48
        ),

        (
            x,
            y + height * 0.52
        ),

        (
            x + width * 0.24,
            y + height * 0.47
        ),

        (
            x + width * 0.43,
            y + height * 0.30
        ),

        (
            x + width * 0.48,
            y + height * 0.04
        ),

        (
            x + width * 0.38,
            y - height * 0.25
        ),

        (
            x + width * 0.20,
            y - height * 0.44
        )
    ]


    points = [

        (
            int(px),
            int(py)
        )

        for px, py in points
    ]


    pygame.draw.polygon(
        surface,
        EYE_OUTLINE,
        points
    )


    inner = []


    for px, py in points:

        dx = px - x
        dy = py - y

        inner.append(
            (
                int(
                    x + dx * 0.88
                ),

                int(
                    y + dy * 0.90
                )
            )
        )


    pygame.draw.polygon(
        surface,
        EYE_WHITE,
        inner
    )


    lash_y = int(
        y - height * 0.42
    )


    if lash_side == "left":

        pygame.draw.line(
            surface,
            EYE_OUTLINE,
            (
                int(
                    x - width * 0.28
                ),
                lash_y
            ),
            (
                int(
                    x - width * 0.43
                ),
                lash_y - 9
            ),
            3
        )

        pygame.draw.line(
            surface,
            EYE_OUTLINE,
            (
                int(
                    x - width * 0.13
                ),
                lash_y - 3
            ),
            (
                int(
                    x - width * 0.18
                ),
                lash_y - 13
            ),
            3
        )

        pygame.draw.line(
            surface,
            EYE_OUTLINE,
            (
                int(
                    x + width * 0.03
                ),
                lash_y - 4
            ),
            (
                int(
                    x + width * 0.05
                ),
                lash_y - 14
            ),
            3
        )

    else:

        pygame.draw.line(
            surface,
            EYE_OUTLINE,
            (
                int(
                    x + width * 0.28
                ),
                lash_y
            ),
            (
                int(
                    x + width * 0.43
                ),
                lash_y - 9
            ),
            3
        )

        pygame.draw.line(
            surface,
            EYE_OUTLINE,
            (
                int(
                    x + width * 0.13
                ),
                lash_y - 3
            ),
            (
                int(
                    x + width * 0.18
                ),
                lash_y - 13
            ),
            3
        )

        pygame.draw.line(
            surface,
            EYE_OUTLINE,
            (
                int(
                    x - width * 0.03
                ),
                lash_y - 4
            ),
            (
                int(
                    x - width * 0.05
                ),
                lash_y - 14
            ),
            3
        )


# ==========================
# PUPIL
# ==========================

def draw_pupil(
    surface,
    x,
    y
):

    pupil_width = 19
    pupil_height = 37


    pygame.draw.ellipse(
        surface,
        PUPIL_DARK,
        (
            int(
                x - pupil_width / 2
            ),

            int(
                y - pupil_height / 2
            ),

            pupil_width,
            pupil_height
        )
    )


    pygame.draw.ellipse(
        surface,
        PUPIL_ORANGE,
        (
            int(x - 7),
            int(y + 5),
            14,
            10
        )
    )


    wedge = [

        (
            int(x + 9),
            int(y - 11)
        ),

        (
            int(x - 1),
            int(y - 5)
        ),

        (
            int(x + 9),
            int(y - 1)
        )
    ]


    pygame.draw.polygon(
        surface,
        EYE_WHITE,
        wedge
    )


# ==========================
# NOSE
# ==========================

def draw_nose(
    surface,
    cx,
    cy
):

    pygame.draw.circle(
        surface,
        FACE_EDGE,
        (
            cx,
            cy
        ),
        6
    )


# ==========================
# REST MOUTH
# ==========================

def draw_rest_mouth(
    surface,
    cx,
    cy
):

    points = [

        (
            cx - 29,
            cy + 26
        ),

        (
            cx - 20,
            cy + 28
        ),

        (
            cx - 10,
            cy + 29
        ),

        (
            cx,
            cy + 30
        ),

        (
            cx + 10,
            cy + 29
        ),

        (
            cx + 20,
            cy + 26
        ),

        (
            cx + 27,
            cy + 22
        )
    ]


    pygame.draw.lines(
        surface,
        MOUTH_COLOR,
        False,
        points,
        4
    )


# ==========================
# MOUTH SHAPES
# ==========================

def draw_mouth(
    surface,
    cx,
    cy,
    shape,
    openness
):

    openness = max(
        0.0,
        min(
            1.0,
            openness
        )
    )


    # ==========================
    # REST
    # ==========================

    if shape == "REST":

        draw_rest_mouth(
            surface,
            cx,
            cy
        )

        return


    # ==========================
    # MBP
    # CLOSED LIPS
    # ==========================

    if shape == "MBP":

        pygame.draw.line(
            surface,
            MOUTH_COLOR,
            (
                cx - 22,
                cy + 28
            ),
            (
                cx + 22,
                cy + 28
            ),
            4
        )

        return


    # ==========================
    # EE
    # WIDE + THIN
    # ==========================

    if shape == "EE":

        mouth_width = 56

        mouth_height = max(
            5,
            int(
                8
                + openness * 12
            )
        )


        pygame.draw.ellipse(
            surface,
            MOUTH_COLOR,
            (
                cx - mouth_width // 2,
                cy + 23,
                mouth_width,
                mouth_height
            )
        )


        teeth_height = max(
            2,
            mouth_height // 3
        )


        pygame.draw.rect(
            surface,
            TEETH_COLOR,
            (
                cx - 20,
                cy + 24,
                40,
                teeth_height
            )
        )

        return


    # ==========================
    # AA
    # WIDE + OPEN
    # ==========================

    if shape == "AA":

        mouth_width = 48

        mouth_height = max(
            10,
            int(
                10
                + openness * 30
            )
        )


        pygame.draw.ellipse(
            surface,
            MOUTH_COLOR,
            (
                cx - mouth_width // 2,
                int(
                    cy + 28
                    - mouth_height / 2
                ),
                mouth_width,
                mouth_height
            )
        )


        tongue_height = max(
            3,
            mouth_height // 4
        )


        pygame.draw.ellipse(
            surface,
            TONGUE_COLOR,
            (
                cx - 13,
                int(
                    cy + 29
                    + mouth_height * 0.12
                ),
                26,
                tongue_height
            )
        )

        return


    # ==========================
    # OH
    # ROUND
    # ==========================

    if shape == "OH":

        mouth_width = max(
            18,
            int(
                20
                + openness * 16
            )
        )

        mouth_height = max(
            14,
            int(
                16
                + openness * 25
            )
        )


        pygame.draw.ellipse(
            surface,
            MOUTH_COLOR,
            (
                cx - mouth_width // 2,
                int(
                    cy + 28
                    - mouth_height / 2
                ),
                mouth_width,
                mouth_height
            )
        )

        return


    # ==========================
    # FV
    # TEETH AGAINST LOWER LIP
    # ==========================

    if shape == "FV":

        mouth_width = 46
        mouth_height = 12


        pygame.draw.ellipse(
            surface,
            MOUTH_COLOR,
            (
                cx - mouth_width // 2,
                cy + 23,
                mouth_width,
                mouth_height
            )
        )


        pygame.draw.rect(
            surface,
            TEETH_COLOR,
            (
                cx - 18,
                cy + 23,
                36,
                4
            )
        )

        return


    # Fallback
    draw_rest_mouth(
        surface,
        cx,
        cy
    )


# ==========================
# CHARACTER
# ==========================

def draw_character(
    surface,
    state
):

    cx = int(
        state.x
    )

    cy = int(
        state.y
    )


    draw_head(
        surface,
        cx,
        cy
    )


    draw_clock_marks(
        surface,
        cx,
        cy
    )


    LEFT_EYE_X = (
        cx - 30
    )

    RIGHT_EYE_X = (
        cx + 30
    )

    EYE_Y = (
        cy - 22
    )

    EYE_WIDTH = 43
    EYE_HEIGHT = 60


    draw_eye(
        surface,
        LEFT_EYE_X,
        EYE_Y,
        EYE_WIDTH,
        int(
            EYE_HEIGHT
            * state.left_eye_scale_y
        ),
        "left"
    )


    draw_eye(
        surface,
        RIGHT_EYE_X,
        EYE_Y,
        EYE_WIDTH,
        int(
            EYE_HEIGHT
            * state.right_eye_scale_y
        ),
        "right"
    )


    # ==========================
    # PUPILS
    # ==========================

    if (
        state.left_eye_scale_y
        > 0.15
    ):

        draw_pupil(
            surface,
            LEFT_EYE_X
            + state.left_pupil_x,
            EYE_Y
            + state.left_pupil_y
        )


    if (
        state.right_eye_scale_y
        > 0.15
    ):

        draw_pupil(
            surface,
            RIGHT_EYE_X
            + state.right_pupil_x,
            EYE_Y
            + state.right_pupil_y
        )


    draw_nose(
        surface,
        cx,
        cy + 4
    )


    # ==========================
    # MOUTH
    # ==========================

    draw_mouth(
        surface,
        cx,
        cy,
        state.mouth_shape,
        state.mouth_open
    )
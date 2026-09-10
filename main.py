import math
import os
import sys
import json
import fcntl
import queue
import threading
import subprocess
from datetime import datetime

import pygame

from renderer import draw_character
from character_state import CharacterState
from poses import set_pose
from idle import IdleAnimator
from speech import SpeechAnimator


# ==========================
# CONFIG
# ==========================

FPS = 30

CANVAS_WIDTH = 315
CANVAS_HEIGHT = 500

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

SPEECH_QUEUE_FILE = os.path.join(
    BASE_DIR,
    "speech_queue.txt"
)

LOG_DIR = os.path.join(
    BASE_DIR,
    "logs"
)

SPEECH_LOG_FILE = os.path.join(
    LOG_DIR,
    "speech.log"
)

ESPEAK_SPEED = 160

SPEECH_CHECK_INTERVAL = 0.10


# ==========================
# LOG DIRECTORY
# ==========================

os.makedirs(
    LOG_DIR,
    exist_ok=True
)


# ==========================
# INIT
# ==========================

pygame.init()

display_info = pygame.display.Info()

SCREEN_WIDTH = display_info.current_w
SCREEN_HEIGHT = display_info.current_h

screen = pygame.display.set_mode(
    (
        SCREEN_WIDTH,
        SCREEN_HEIGHT
    ),
    pygame.FULLSCREEN
)

pygame.mouse.set_visible(False)

canvas = pygame.Surface(
    (
        CANVAS_WIDTH,
        CANVAS_HEIGHT
    )
)

clock = pygame.time.Clock()


# ==========================
# SUBTITLE FONT
# ==========================

subtitle_font = pygame.font.Font(
    None,
    22
)


# ==========================
# CHARACTER STATE
# ==========================

state = CharacterState()

set_pose(
    state,
    "neutral"
)

float_time = 0.0


# ==========================
# ANIMATORS
# ==========================

idle_animator = IdleAnimator()
speech_animator = SpeechAnimator()


# ==========================
# SPEECH STATE
# ==========================

audio_queue = queue.Queue()

speech_check_timer = 0.0

current_speech_text = ""

audio_speaking = False

speech_state_lock = threading.Lock()

shutdown_event = threading.Event()


# ==========================
# LOGGING
# ==========================

def log_speech(event, text):

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    line = (
        f"{timestamp} "
        f"{event}: "
        f"{text}\n"
    )

    try:

        with open(
            SPEECH_LOG_FILE,
            "a"
        ) as file:

            file.write(
                line
            )

    except Exception as error:

        print(
            "Speech log error:",
            error,
            flush=True
        )


# ==========================
# AUDIO WORKER
# ==========================

def audio_worker():

    global current_speech_text
    global audio_speaking


    while not shutdown_event.is_set():

        try:

            text = audio_queue.get(
                timeout=0.25
            )

        except queue.Empty:

            continue


        if text is None:

            audio_queue.task_done()
            break


        with speech_state_lock:

            current_speech_text = text
            audio_speaking = True


        print(
            "Speaking:",
            text,
            flush=True
        )

        log_speech(
            "SPEAKING",
            text
        )


        try:

            # ----------------------------------
            # Generate WAV stream with espeak-ng
            # ----------------------------------

            espeak_process = subprocess.Popen(
                [
                    "espeak-ng",
                    "-s",
                    str(ESPEAK_SPEED),
                    "--stdout",
                    text
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )


            # ----------------------------------
            # Send stream to ALSA
            # ----------------------------------

            aplay_process = subprocess.Popen(
                [
                    "aplay"
                ],
                stdin=espeak_process.stdout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )


            # Parent does not need this copy.
            espeak_process.stdout.close()


            # ----------------------------------
            # Wait for audio to finish
            # ----------------------------------

            aplay_process.wait()

            espeak_process.wait()


            log_speech(
                "FINISHED",
                text
            )


        except Exception as error:

            print(
                "Audio worker error:",
                error,
                flush=True
            )

            log_speech(
                "ERROR",
                f"{text} | {error}"
            )


        finally:

            with speech_state_lock:

                audio_speaking = False
                current_speech_text = ""


            audio_queue.task_done()


# ==========================
# START AUDIO WORKER
# ==========================

audio_thread = threading.Thread(
    target=audio_worker,
    daemon=True
)

audio_thread.start()


# ==========================
# ADD SPEECH
# ==========================

def queue_speech(text):

    if not text:
        return


    print(
        "Received:",
        text,
        flush=True
    )

    log_speech(
        "RECEIVED",
        text
    )


    audio_queue.put(
        text
    )


# ==========================
# LOAD SPEECH FILE QUEUE
# ==========================

def load_speech_queue(dt):

    global speech_check_timer


    speech_check_timer += dt


    if (
        speech_check_timer
        < SPEECH_CHECK_INTERVAL
    ):
        return


    speech_check_timer = 0.0


    if not os.path.exists(
        SPEECH_QUEUE_FILE
    ):
        return


    try:

        with open(
            SPEECH_QUEUE_FILE,
            "r+"
        ) as file:

            fcntl.flock(
                file,
                fcntl.LOCK_EX
            )


            lines = file.readlines()


            file.seek(0)
            file.truncate()


            fcntl.flock(
                file,
                fcntl.LOCK_UN
            )


        for line in lines:

            line = line.strip()


            if not line:
                continue


            # MCP writes JSON strings.
            # Plain terminal text also works.

            try:

                text = json.loads(
                    line
                )

            except Exception:

                text = line


            if text:

                queue_speech(
                    text
                )


    except Exception as error:

        print(
            "Speech queue read error:",
            error,
            flush=True
        )


# ==========================
# SYNC MOUTH TO AUDIO STATE
# ==========================

def update_speech_animation():

    with speech_state_lock:

        speaking = audio_speaking
        text = current_speech_text


    # Start animation when actual audio starts.
    if speaking:

        if not speech_animator.speaking:

            speech_animator.start(
                text
            )


    # Stop animation when audio finishes.
    else:

        if speech_animator.speaking:

            speech_animator.stop(
                state
            )


# ==========================
# WORD WRAP
# ==========================

def wrap_text(text, font, max_width):

    words = text.split()

    lines = []

    current_line = ""


    for word in words:

        test_line = word

        if current_line:

            test_line = (
                current_line
                + " "
                + word
            )


        width = font.size(
            test_line
        )[0]


        if width <= max_width:

            current_line = test_line

        else:

            if current_line:

                lines.append(
                    current_line
                )

            current_line = word


    if current_line:

        lines.append(
            current_line
        )


    return lines


# ==========================
# DRAW SUBTITLES
# ==========================

def draw_subtitles():

    with speech_state_lock:

        text = current_speech_text


    if not text:

        return


    max_width = CANVAS_WIDTH - 30

    lines = wrap_text(
        text,
        subtitle_font,
        max_width
    )


    # Limit how much of the screen subtitles
    # can occupy.
    lines = lines[-5:]


    line_height = 21

    total_height = (
        len(lines)
        * line_height
    )


    start_y = (
        CANVAS_HEIGHT
        - total_height
        - 12
    )


    for index, line in enumerate(lines):

        text_surface = subtitle_font.render(
            line,
            True,
            WHITE
        )


        text_rect = text_surface.get_rect()

        text_rect.centerx = (
            CANVAS_WIDTH // 2
        )

        text_rect.y = (
            start_y
            + index * line_height
        )


        # Small black backing makes text readable
        # if it overlaps the character.

        background_rect = text_rect.inflate(
            8,
            4
        )

        pygame.draw.rect(
            canvas,
            BLACK,
            background_rect
        )


        canvas.blit(
            text_surface,
            text_rect
        )


# ==========================
# TEST SPEECH
# ==========================

TEST_LINES = [

    "Well hey there, sugar.",

    "Maybe we should take a little trip through the TVA.",

    "Now hold on just a minute.",

    "Looks like we've got ourselves a variant.",

    "Don't you worry. Miss Minutes has everything under control."

]

test_line_index = 0


# ==========================
# DRAW FRAME
# ==========================

def draw_frame(dt):

    global float_time


    canvas.fill(
        BLACK
    )


    # ==========================
    # FLOAT
    # ==========================

    float_time += dt

    state.x = (
        CANVAS_WIDTH // 2
    )

    state.y = (
        CANVAS_HEIGHT // 2
        + math.sin(
            float_time * 2.0
        ) * 4
    )


    # ==========================
    # LOAD NEW SPEECH
    # ==========================

    load_speech_queue(
        dt
    )


    # ==========================
    # SYNC SPEECH ANIMATION
    # ==========================

    update_speech_animation()


    # ==========================
    # ANIMATION UPDATES
    # ==========================

    speech_animator.update(
        state,
        dt
    )


    with speech_state_lock:

        speaking = audio_speaking


    idle_animator.update(
        state,
        dt,
        speaking
    )


    # ==========================
    # DRAW CHARACTER
    # ==========================

    draw_character(
        canvas,
        state
    )


    # ==========================
    # DRAW SUBTITLES
    # ==========================

    draw_subtitles()


    # ==========================
    # PHYSICAL DISPLAY
    # ==========================

    screen.fill(
        BLACK
    )


    canvas_x = (
        SCREEN_WIDTH
        - CANVAS_WIDTH
    ) // 2


    canvas_y = (
        SCREEN_HEIGHT
        - CANVAS_HEIGHT
    ) // 2


    screen.blit(
        canvas,
        (
            canvas_x,
            canvas_y
        )
    )


    pygame.display.flip()


# ==========================
# MAIN LOOP
# ==========================

def main():

    global test_line_index

    running = True


    while running:

        dt = (
            clock.tick(FPS)
            / 1000.0
        )


        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                running = False


            elif event.type == pygame.KEYDOWN:


                # ==========================
                # EXIT
                # ==========================

                if event.key == pygame.K_ESCAPE:

                    running = False


                # ==========================
                # EXPRESSIONS
                # ==========================

                elif event.key == pygame.K_1:

                    set_pose(
                        state,
                        "neutral"
                    )


                elif event.key == pygame.K_2:

                    set_pose(
                        state,
                        "happy"
                    )


                elif event.key == pygame.K_3:

                    set_pose(
                        state,
                        "angry"
                    )


                elif event.key == pygame.K_4:

                    set_pose(
                        state,
                        "sad"
                    )


                # ==========================
                # TEST SPEECH
                # ==========================

                elif event.key == pygame.K_SPACE:

                    queue_speech(
                        TEST_LINES[
                            test_line_index
                        ]
                    )


                    test_line_index += 1


                    if (
                        test_line_index
                        >= len(TEST_LINES)
                    ):

                        test_line_index = 0


        draw_frame(
            dt
        )


    # ==========================
    # SHUT DOWN AUDIO WORKER
    # ==========================

    shutdown_event.set()

    audio_queue.put(
        None
    )


    pygame.quit()

    sys.exit()


# ==========================
# START
# ==========================

if __name__ == "__main__":

    main()
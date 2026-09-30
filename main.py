import math
import os
import sys
import json
import time
import fcntl
import queue
import tempfile
import threading
import subprocess
from datetime import datetime

import pygame

from renderer import draw_character
from character_state import CharacterState
from poses import set_pose
from idle import IdleAnimator
from speech import SpeechAnimator
from audio_analysis import analyze_wav


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

# Which TTS engine generates the WAV that gets analyzed for lip-sync
# and played through aplay. Both are fast/local, no network or heavy
# model involved, so neither should reintroduce the delay that made
# Piper unusable.
#   "espeak-ng" - what's been running; clearly robotic but instant.
#   "pico2wave" - SVOX Pico, still lightweight, noticeably less
#                 robotic prosody. Requires the libttspico-utils
#                 package (apt) on the Pi - not installed by default.
# Flip this one line to A/B them; everything else (queueing,
# analysis, playback, lip-sync) is unchanged either way.
TTS_ENGINE = "espeak-ng"

PICO2WAVE_LANGUAGE = "en-US"

SPEECH_CHECK_INTERVAL = 0.10

# Print average FPS to the console once a second. Pure diagnostic -
# on a Pi 3B this is the fastest way to tell whether roughness is a
# dropped-frames problem (fix that first) or an animation-logic
# problem (the frame rate is fine, the motion itself needs work).
FPS_LOG_INTERVAL = 1.0


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
# FIXED CANVAS PLACEMENT
# ==========================
# The canvas position on screen never changes, so it's computed once
# here instead of every frame. The letterbox bars around it are
# filled black once, before the loop starts, instead of re-filling
# the full screen at full resolution every frame - only the canvas
# region itself needs to be redrawn each frame.

CANVAS_X = (
    SCREEN_WIDTH
    - CANVAS_WIDTH
) // 2

CANVAS_Y = (
    SCREEN_HEIGHT
    - CANVAS_HEIGHT
) // 2

screen.fill(BLACK)
pygame.display.flip()


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
# Everything under speech_state_lock is written by audio_worker()
# (a background thread) and read by the main pygame thread. Only
# the background thread writes to these fields; only the main
# thread calls into speech_animator - that split is what makes the
# lock sufficient without also needing to guard speech_animator
# itself.

audio_queue = queue.Queue()

speech_check_timer = 0.0

current_speech_text = ""
current_speech_start_time = None
current_speech_duration = None
current_speech_envelope = None
current_speech_envelope_window = None

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
# TTS SYNTHESIS
# ==========================

def _synthesize_espeak_ng(text):

    result = subprocess.run(
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

    return result.stdout


def _synthesize_pico2wave(text):

    # pico2wave has no --stdout option - it only writes a WAV to a
    # file path, so we hand it a temp file and read the bytes back.
    # Runs in the same worker thread as espeak-ng did, so this stays
    # off the main/render thread either way.
    with tempfile.NamedTemporaryFile(
        suffix=".wav",
        delete=False
    ) as temp_file:

        temp_path = temp_file.name

    try:

        subprocess.run(
            [
                "pico2wave",
                "-l",
                PICO2WAVE_LANGUAGE,
                "-w",
                temp_path,
                text
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        with open(temp_path, "rb") as wav_file:
            return wav_file.read()

    finally:

        try:
            os.remove(temp_path)
        except OSError:
            pass


def synthesize_wav(text):
    """
    Generate a WAV for `text` using whichever engine TTS_ENGINE
    selects. Returns raw WAV bytes, or raises on failure (callers
    already wrap this in a try/except).
    """

    if TTS_ENGINE == "pico2wave":
        return _synthesize_pico2wave(text)

    return _synthesize_espeak_ng(text)


# ==========================
# AUDIO WORKER
# ==========================

def audio_worker():

    global current_speech_text
    global current_speech_start_time
    global current_speech_duration
    global current_speech_envelope
    global current_speech_envelope_window
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
            # Generate the full WAV in memory first (instead of
            # streaming straight into aplay) so its real duration
            # and loudness can be measured before/while it plays.
            # Both supported engines are lightweight, non-neural
            # synthesizers - generating a sentence takes at most a
            # few tens of milliseconds even on a Pi 3B, so this
            # doesn't reintroduce the kind of delay Piper caused.
            # ----------------------------------

            wav_bytes = synthesize_wav(text)


            duration, envelope, envelope_window = analyze_wav(
                wav_bytes
            )


            # ----------------------------------
            # Publish speech state BEFORE launching aplay, and
            # capture start_time right at that point - this is the
            # closest available proxy for "when the audio actually
            # started", used to drive the mouth off a wall clock
            # instead of accumulated per-frame dt (which drifted on
            # long sentences in the old version).
            # ----------------------------------

            start_time = time.monotonic()

            with speech_state_lock:

                current_speech_text = text
                current_speech_start_time = start_time
                current_speech_duration = duration
                current_speech_envelope = envelope
                current_speech_envelope_window = envelope_window
                audio_speaking = True


            aplay_process = subprocess.Popen(
                [
                    "aplay"
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            aplay_process.communicate(
                input=wav_bytes
            )


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
                current_speech_start_time = None
                current_speech_duration = None
                current_speech_envelope = None
                current_speech_envelope_window = None


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


            # MCP writes JSON objects: {"text": ..., "emotion": ...}.
            # Older or hand-written entries may just be a JSON
            # string or plain text - handle all three shapes
            # without erroring.

            text = None
            emotion = None

            try:

                parsed = json.loads(
                    line
                )

                if isinstance(parsed, dict):

                    text = parsed.get("text")
                    emotion = parsed.get("emotion")

                elif isinstance(parsed, str):

                    text = parsed

            except Exception:

                text = line


            if text:

                if emotion:

                    set_pose(
                        state,
                        emotion
                    )

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
    """
    Detects speaking-state transitions and starts/stops
    speech_animator accordingly. This (and speech_animator itself)
    only ever runs on the main thread - audio_worker only writes the
    shared fields above, it never touches speech_animator directly.
    """

    with speech_state_lock:

        speaking = audio_speaking
        text = current_speech_text
        start_time = current_speech_start_time
        duration = current_speech_duration
        envelope = current_speech_envelope
        envelope_window = current_speech_envelope_window


    # Start animation when actual audio starts.
    if speaking:

        if not speech_animator.speaking:

            speech_animator.start_audio(
                text,
                duration,
                envelope,
                envelope_window,
                start_time=start_time
            )


    # Stop animation when audio finishes. speech_animator normally
    # already stops itself once its own elapsed-time tracking passes
    # the clip's duration, but this flag-driven stop is the ultimate
    # authority - it also covers cases like duration analysis having
    # failed, or aplay exiting earlier or later than expected.
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
# SUBTITLE CACHE
# ==========================
# Rendering text and word-wrapping it are both real costs when done
# every frame at 30 FPS. The subtitle text only actually changes
# when speech does, so cache the wrapped/rendered surfaces and only
# rebuild them when current_speech_text is different from last time.

_subtitle_cache_text = None
_subtitle_cache_surfaces = []


def get_subtitle_surfaces(text):

    global _subtitle_cache_text
    global _subtitle_cache_surfaces


    if text == _subtitle_cache_text:
        return _subtitle_cache_surfaces


    max_width = CANVAS_WIDTH - 30

    lines = wrap_text(
        text,
        subtitle_font,
        max_width
    )

    lines = lines[-5:]


    surfaces = [

        subtitle_font.render(
            line,
            True,
            WHITE
        )

        for line in lines
    ]


    _subtitle_cache_text = text
    _subtitle_cache_surfaces = surfaces


    return surfaces


# ==========================
# DRAW SUBTITLES
# ==========================

def draw_subtitles():

    with speech_state_lock:

        text = current_speech_text


    if not text:

        return


    surfaces = get_subtitle_surfaces(
        text
    )


    line_height = 21

    total_height = (
        len(surfaces)
        * line_height
    )


    start_y = (
        CANVAS_HEIGHT
        - total_height
        - 12
    )


    for index, text_surface in enumerate(surfaces):

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
# FPS LOGGING
# ==========================

_fps_log_timer = 0.0


def log_fps(dt):

    global _fps_log_timer

    _fps_log_timer += dt

    if _fps_log_timer < FPS_LOG_INTERVAL:
        return

    _fps_log_timer = 0.0

    print(
        f"FPS: {clock.get_fps():.1f}",
        flush=True
    )


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
    # Order matters: speech and idle set *targets* for the frame,
    # then state.update_smoothing() eases the displayed values
    # toward whatever was just set. Smoothing must run after both.

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


    state.update_smoothing(
        dt
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
    # The letterbox bars around the canvas never change, so only the
    # canvas region is redrawn each frame (see CANVAS_X/CANVAS_Y -
    # the full-screen black fill happens once, before the loop
    # starts).

    screen.blit(
        canvas,
        (
            CANVAS_X,
            CANVAS_Y
        )
    )


    pygame.display.flip()


    log_fps(
        dt
    )


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

import re
import math
import os
import sys
import json
import time
import fcntl
import queue
import atexit
import select
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

# Tells the MCP server (a separate process) whether Miss Minutes is
# talking right now, and when she last stopped. The server uses it to
# drop replies AIPI makes to her OWN voice picked up by its mic,
# which is what causes the "answering herself" loop.
SPEECH_STATUS_FILE = os.path.join(
    BASE_DIR,
    "speech_status.json"
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
# and played through aplay.
#   "espeak-ng" - clearly robotic but instant.
#   "pico2wave" - SVOX Pico, still lightweight, noticeably less
#                 robotic prosody. Installed from the Debian
#                 libttspico-utils .debs (not in Raspberry Pi OS's
#                 own repo). Uses the SOX_EFFECTS vintage filter below.
#   "piper"     - neural voice, by far the most natural. Runs as one
#                 long-lived process with the voice model kept
#                 loaded (reloading it per line is what made Piper
#                 too slow before), and replies are spoken sentence
#                 by sentence so the first sentence starts while the
#                 rest are still being generated. Falls back to
#                 pico2wave if Piper fails.
# Flip this one line to A/B them; everything else (queueing,
# analysis, playback, lip-sync) is unchanged either way.
TTS_ENGINE = "piper"

PICO2WAVE_LANGUAGE = "en-US"

# ==========================
# PIPER
# ==========================
# PIPER_VOICE: on a Pi 3B, "low" / "x_low" quality voices generate
# several times faster than "medium". If the first sentence still
# takes too long to start, download e.g. en_US-amy-low.onnx (and its
# .onnx.json) into ~/piper/voices and point this at it.
#
# PIPER_LENGTH_SCALE: speaking speed. 1.0 = normal, lower = faster
# (0.9 is a little quicker), higher = slower.

PIPER_DIR = os.path.expanduser("~/piper")

PIPER_BIN = os.path.join(PIPER_DIR, "piper")

PIPER_VOICE = os.path.join(
    PIPER_DIR,
    "voices",
    "en_US-hfc_female-medium.onnx"
)

PIPER_LENGTH_SCALE = 1.0

# Longest we'll wait for Piper to produce one sentence before giving
# up on it, restarting it, and using pico2wave for that sentence.
PIPER_TIMEOUT = 30.0

# Optional sox effects for Piper's voice. Empty = Piper's natural
# voice. For the vintage TV sound without changing her pitch, try:
#   ["highpass", "300", "lowpass", "3500"]
PIPER_SOX_EFFECTS = []

# Sentence fragments shorter than this (characters) are joined to the
# next one, so "Oh!" or "Well," don't become their own clip with a
# gap after them.
MIN_SENTENCE_CHARS = 12

# The first clip of every reply is cut short at a comma (or ; : -)
# when it can be, so Piper only has to generate a few words before
# Miss Minutes starts talking - e.g. "Well, sugar," plays while the
# rest of the sentence is still being generated. Lower = she starts
# sooner; higher = fewer breaks in her first sentence.
FIRST_CHUNK_CHARS = 30

# The very first clip may be as short as this (e.g. "Alright,"), since
# for that one clip starting quickly matters more than an extra pause.
FIRST_CHUNK_MIN_CHARS = 6

# Later sentences longer than this are also split at commas, so one
# long sentence can't make her stall mid-reply waiting on Piper.
MAX_CHUNK_CHARS = 80

# ==========================
# VOICE EFFECT (SOX)
# ==========================
# Post-processes the pico2wave output with sox for a vintage
# "old TV speaker" Miss Minutes sound. Requires: sudo apt install sox
# If sox is missing or fails, the plain pico voice is used instead,
# so speech never goes silent because of the effect.
#
# Tuning:
#   pitch    - in cents (100 = one semitone). Higher = squeakier.
#   tempo    - speed multiplier without changing pitch (1.0 = normal).
#   highpass - cuts bass below this Hz. Higher = thinner/tinnier.
#   lowpass  - cuts treble above this Hz. Lower = more muffled/radio.
# Set SOX_EFFECTS = [] to turn the effect off entirely.
SOX_EFFECTS = [
    "pitch", "250",
    "tempo", "1.05",
    "highpass", "300",
    "lowpass", "3500"
]

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
# Everything under speech_state_lock is written by play_worker()
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
# SPEECH STATUS (FOR ECHO GUARD)
# ==========================

def write_speech_status(speaking):
    """
    Records whether audio is playing right now, plus (when it stops)
    the wall-clock time it stopped, for the MCP server's echo guard.
    Written to a temp file and renamed so the server never reads a
    half-written file. Never raises - a status write failing must
    not interrupt speech.
    """

    status = {
        "speaking": bool(speaking),
        "updated_at": time.time()
    }

    temp_path = SPEECH_STATUS_FILE + ".tmp"

    try:

        with open(temp_path, "w") as file:
            json.dump(status, file)

        os.replace(
            temp_path,
            SPEECH_STATUS_FILE
        )

    except Exception as error:

        print(
            "Speech status write error:",
            error,
            flush=True
        )


write_speech_status(False)


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

    # sox writes its processed output to a second temp file rather
    # than a pipe: a WAV written to a pipe can't have its length
    # filled into the header, and analyze_wav() relies on that
    # header to measure the clip's real duration for lip-sync.
    fx_path = temp_path.replace(
        ".wav",
        "_fx.wav"
    )

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

        out_path = temp_path

        if SOX_EFFECTS:

            try:

                subprocess.run(
                    ["sox", temp_path, fx_path] + SOX_EFFECTS,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )

                out_path = fx_path

            except (OSError, subprocess.CalledProcessError) as error:

                # sox missing or failed - still speak with the plain
                # pico voice rather than going silent.
                print(
                    "sox effect failed, using plain voice:",
                    error,
                    flush=True
                )

        with open(out_path, "rb") as wav_file:
            return wav_file.read()

    finally:

        for path in (temp_path, fx_path):

            try:
                os.remove(path)
            except OSError:
                pass


def _apply_sox(wav_bytes, effects):
    """
    Run a WAV through sox with the given effects. Goes via temp
    files (not pipes) so the output WAV header carries the real
    length. Returns the original bytes unchanged if effects is empty
    or sox fails, so an effect problem never silences speech.
    """

    if not effects:
        return wav_bytes

    in_fd, in_path = tempfile.mkstemp(suffix=".wav")
    out_path = in_path.replace(".wav", "_fx.wav")

    try:

        with os.fdopen(in_fd, "wb") as in_file:
            in_file.write(wav_bytes)

        subprocess.run(
            ["sox", in_path, out_path] + list(effects),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        with open(out_path, "rb") as out_file:
            return out_file.read()

    except (OSError, subprocess.CalledProcessError) as error:

        print(
            "sox effect failed, using plain voice:",
            error,
            flush=True
        )

        return wav_bytes

    finally:

        for path in (in_path, out_path):

            try:
                os.remove(path)
            except OSError:
                pass


# ==========================
# PIPER (LONG-LIVED PROCESS)
# ==========================
# Piper's --output_dir mode reads one line of text at a time from
# stdin, writes each to its own WAV file, and prints that file's path
# on stdout. Keeping one Piper process alive means the voice model is
# loaded once at startup instead of on every line - on a Pi 3B that
# reload alone was a couple of seconds per reply.

class PiperEngine:

    def __init__(self):

        self.process = None
        self.lock = threading.Lock()

        self.out_dir = os.path.join(
            tempfile.gettempdir(),
            "missminutes_piper"
        )

        os.makedirs(
            self.out_dir,
            exist_ok=True
        )

        self.log_path = os.path.join(
            LOG_DIR,
            "piper.log"
        )


    def _start(self):

        env = dict(os.environ)

        env["LD_LIBRARY_PATH"] = (
            PIPER_DIR
            + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
        )

        log_file = open(self.log_path, "ab")

        self.process = subprocess.Popen(
            [
                PIPER_BIN,
                "--model", PIPER_VOICE,
                "--output_dir", self.out_dir,
                "--length_scale", str(PIPER_LENGTH_SCALE),
                "--sentence_silence", "0"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=log_file,
            cwd=PIPER_DIR,
            env=env
        )

        log_file.close()

        print("Piper started", flush=True)


    def stop(self):

        if self.process and self.process.poll() is None:

            try:
                self.process.kill()
            except OSError:
                pass

        self.process = None


    def synthesize(self, text):
        """
        Returns WAV bytes for one line of text. Raises on failure or
        timeout (after restarting Piper so the next call gets a
        fresh process).
        """

        line = " ".join(text.split())

        if not line:
            raise ValueError("empty text")

        with self.lock:

            if self.process is None or self.process.poll() is not None:
                self._start()

            try:

                self.process.stdin.write(
                    (line + "\n").encode("utf-8")
                )
                self.process.stdin.flush()

                ready, _, _ = select.select(
                    [self.process.stdout],
                    [],
                    [],
                    PIPER_TIMEOUT
                )

                if not ready:
                    raise TimeoutError(
                        f"Piper took over {PIPER_TIMEOUT:.0f}s"
                    )

                wav_path = self.process.stdout.readline().decode(
                    "utf-8",
                    "replace"
                ).strip()

                if not wav_path:
                    raise RuntimeError(
                        "Piper exited - see logs/piper.log"
                    )

            except Exception:

                self.stop()
                raise

        try:

            with open(wav_path, "rb") as wav_file:
                return wav_file.read()

        finally:

            try:
                os.remove(wav_path)
            except OSError:
                pass


piper_engine = PiperEngine()

atexit.register(piper_engine.stop)


def _synthesize_piper(text):

    try:

        wav_bytes = piper_engine.synthesize(text)

    except Exception as error:

        print(
            "Piper failed, using pico2wave for this line:",
            error,
            flush=True
        )

        return _synthesize_pico2wave(text)

    return _apply_sox(
        wav_bytes,
        PIPER_SOX_EFFECTS
    )


def _warm_up_piper():
    """
    Start Piper and run one throwaway line at startup, so loading
    the model (and the first, slowest inference) happens before
    anyone talks to Miss Minutes rather than on her first reply.
    """

    try:
        piper_engine.synthesize("Hi.")
        print("Piper warmed up", flush=True)
    except Exception as error:
        print("Piper warm-up failed:", error, flush=True)


# ==========================
# SENTENCE SPLITTING
# ==========================

_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


def split_sentences(text):
    """
    Splits a reply into sentences so speech can start after the
    first one is generated instead of after the whole reply. Short
    fragments are joined to the following sentence.
    """

    pieces = [
        piece.strip()
        for piece in _SENTENCE_END.split(text.strip())
        if piece.strip()
    ]

    sentences = []
    carry = ""

    for piece in pieces:

        combined = (carry + " " + piece).strip() if carry else piece

        if len(combined) < MIN_SENTENCE_CHARS:
            carry = combined
        else:
            sentences.append(combined)
            carry = ""

    if carry:

        if sentences:
            sentences[-1] = sentences[-1] + " " + carry
        else:
            sentences.append(carry)

    return sentences


_CLAUSE_BREAK = re.compile(r"(?<=[,;:—–])\s+|\s+-\s+")


def _split_clauses(sentence, first_limit, limit):
    """
    Splits one sentence at clause breaks (commas etc.) into chunks
    of at most `limit` characters - the first chunk at most
    `first_limit` - without ever making a chunk shorter than
    MIN_SENTENCE_CHARS. A single clause longer than the limit is
    left whole rather than cut mid-phrase.
    """

    parts = [
        part.strip()
        for part in _CLAUSE_BREAK.split(sentence)
        if part.strip()
    ]

    chunks = []
    current = ""

    for part in parts:

        opening = not chunks and first_limit < limit

        cap = first_limit if opening else limit

        min_len = (
            FIRST_CHUNK_MIN_CHARS
            if opening
            else MIN_SENTENCE_CHARS
        )

        candidate = (current + " " + part) if current else part

        if (
            current
            and len(candidate) > cap
            and len(current) >= min_len
        ):
            chunks.append(current)
            current = part
        else:
            current = candidate

    if current:
        chunks.append(current)

    return chunks


def split_into_chunks(text):
    """
    The clips a reply is actually spoken in: its sentences, with
    the reply's first clip kept short (FIRST_CHUNK_CHARS) and any
    long sentence broken at commas (MAX_CHUNK_CHARS). Short first
    clips are what make Piper usable on a Pi 3B - generation time
    grows with text length, so a few words start playing far sooner
    than a whole sentence.
    """

    chunks = []

    for index, sentence in enumerate(split_sentences(text)):

        first_limit = (
            FIRST_CHUNK_CHARS
            if index == 0
            else MAX_CHUNK_CHARS
        )

        chunks.extend(
            _split_clauses(
                sentence,
                first_limit,
                MAX_CHUNK_CHARS
            )
        )

    return chunks


def synthesize_wav(text):
    """
    Generate a WAV for `text` using whichever engine TTS_ENGINE
    selects. Returns raw WAV bytes, or raises on failure (callers
    already wrap this in a try/except).
    """

    if TTS_ENGINE == "piper":
        return _synthesize_piper(text)

    if TTS_ENGINE == "pico2wave":
        return _synthesize_pico2wave(text)

    return _synthesize_espeak_ng(text)


# ==========================
# AUDIO PIPELINE
# ==========================
# Two background threads, so generating the next sentence overlaps
# with playing the current one:
#
#   synth_worker: takes whole replies from audio_queue, splits them
#     into sentences, generates + measures each WAV, and hands them
#     to play_queue in order.
#   play_worker: takes ready sentences from play_queue and plays
#     them, publishing the speech state that drives the mouth and
#     subtitles.
#
# So the wait before Miss Minutes starts talking is only the time to
# generate her FIRST sentence, not her whole reply. With the fast
# engines (espeak-ng, pico2wave) this changes nothing noticeable;
# with Piper it's the difference between usable and not.
#
# Everything under speech_state_lock is still written only by the
# background side (play_worker) and read by the main pygame thread.

# Bounded so generation can't run arbitrarily far ahead of playback
# (memory on a Pi 3B), while still keeping a sentence or two ready.
play_queue = queue.Queue(
    maxsize=3
)


def synth_worker():

    while not shutdown_event.is_set():

        try:

            text = audio_queue.get(
                timeout=0.25
            )

        except queue.Empty:

            continue


        if text is None:

            audio_queue.task_done()
            play_queue.put(None)
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


        reply_start = time.monotonic()
        first_chunk = True


        for sentence in split_into_chunks(text):

            try:

                # ----------------------------------
                # Generate the full WAV for this chunk in memory
                # (instead of streaming straight into aplay) so its
                # real duration and loudness can be measured for
                # lip-sync before it plays.
                # ----------------------------------

                synth_start = time.monotonic()

                wav_bytes = synthesize_wav(sentence)

                duration, envelope, envelope_window = analyze_wav(
                    wav_bytes
                )

                # ----------------------------------
                # Timing diagnostics (pygame.log). "x realtime" is
                # generation time / audio length: under 1.0 means the
                # engine keeps ahead of playback, over 1.0 means there
                # will be gaps between chunks.
                # ----------------------------------

                synth_time = time.monotonic() - synth_start

                if duration:

                    print(
                        f"TTS: {synth_time:.2f}s to make "
                        f"{duration:.2f}s of audio "
                        f"({synth_time / duration:.2f}x realtime): "
                        f"{sentence}",
                        flush=True
                    )

                if first_chunk:

                    print(
                        "TTS: first audio ready "
                        f"{time.monotonic() - reply_start:.2f}s "
                        "after reply arrived",
                        flush=True
                    )

                    first_chunk = False

                play_queue.put(
                    (
                        sentence,
                        wav_bytes,
                        duration,
                        envelope,
                        envelope_window
                    )
                )

            except Exception as error:

                print(
                    "Synthesis error:",
                    error,
                    flush=True
                )

                log_speech(
                    "ERROR",
                    f"{sentence} | {error}"
                )


        audio_queue.task_done()


def play_worker():

    global current_speech_text
    global current_speech_start_time
    global current_speech_duration
    global current_speech_envelope
    global current_speech_envelope_window
    global audio_speaking


    while True:

        item = play_queue.get()


        if item is None:

            play_queue.task_done()
            break


        sentence, wav_bytes, duration, envelope, envelope_window = item


        try:

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

                current_speech_text = sentence
                current_speech_start_time = start_time
                current_speech_duration = duration
                current_speech_envelope = envelope
                current_speech_envelope_window = envelope_window
                audio_speaking = True


            write_speech_status(True)


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
                sentence
            )


        except Exception as error:

            print(
                "Audio worker error:",
                error,
                flush=True
            )

            log_speech(
                "ERROR",
                f"{sentence} | {error}"
            )


        finally:

            write_speech_status(False)

            with speech_state_lock:

                audio_speaking = False
                current_speech_text = ""
                current_speech_start_time = None
                current_speech_duration = None
                current_speech_envelope = None
                current_speech_envelope_window = None


            play_queue.task_done()


# ==========================
# START AUDIO PIPELINE
# ==========================

if TTS_ENGINE == "piper":

    threading.Thread(
        target=_warm_up_piper,
        daemon=True
    ).start()


synth_thread = threading.Thread(
    target=synth_worker,
    daemon=True
)

play_thread = threading.Thread(
    target=play_worker,
    daemon=True
)

synth_thread.start()
play_thread.start()


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
    only ever runs on the main thread - play_worker only writes the
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

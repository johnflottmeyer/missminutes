import time


# ==========================
# TUNING
# ==========================

# Shifts mouth-shape lookup slightly ahead of the audio clock to
# help hide output latency (time between deciding a frame and it
# actually reaching the speaker). Purely a feel constant - raise it
# if the mouth still looks like it's trailing the sound, lower it
# if it looks like it's leading too much.
AUDIO_LOOKAHEAD = 0.06

# Shortest time (seconds) any one mouth shape stays on screen.
# The letter-by-letter tokenizer produces shapes as short as
# ~35 ms (a single space between words), which at 30 FPS is about
# one frame - the mouth was flickering between shapes faster than
# the eye can follow, which reads as jittery rather than as speech.
# Segments shorter than this are merged into their neighbor, so
# quick consonants and word gaps become a small dip in openness
# instead of a snap shut. Raise for a smoother/lazier mouth, lower
# for a more articulate/busier one. 0 disables merging.
MIN_SHAPE_HOLD = 0.09


# ==========================
# TEXT -> MOUTH SHAPE TOKENS
# ==========================

def _tokenize(text):
    """
    Walks the text once and yields (shape, openness, duration)
    triples, using the same letter/digraph heuristics the original
    per-character timer used.

    shape=None means "hold whatever the previous real shape was" -
    used for consonants (t, d, k, g, n, s, ...) that don't need the
    mouth to jump to a new visible position. Callers resolve this
    with _resolve_holds() before using the tokens for timing.

    duration is a relative weight, in seconds, matching the original
    tuned values. In fallback mode (no audio to measure) these are
    used directly as real-time timings. In audio-driven mode they're
    rescaled to fit the real, measured length of the clip - see
    _build_timeline() - so only their relative sizes matter there.
    """

    text = text.lower()

    index = 0
    length = len(text)

    while index < length:

        remaining = text[index:]
        char = remaining[0]

        # ------------------------------
        # Punctuation / whitespace
        # ------------------------------

        if char in ".!?":
            index += 1
            yield ("REST", 0.0, 0.16)
            continue

        if char in ",;:":
            index += 1
            yield ("REST", 0.0, 0.09)
            continue

        if char.isspace():
            index += 1
            yield ("REST", 0.0, 0.035)
            continue

        # ------------------------------
        # Three-letter chunks
        # ------------------------------

        three = remaining[:3]

        if three == "ing":
            index += 3
            yield ("EE", 0.24, 0.115)
            continue

        # ------------------------------
        # Two-letter chunks
        # ------------------------------

        two = remaining[:2]

        if two in ("sh", "ch"):
            index += 2
            yield ("OH", 0.22, 0.085)
            continue

        if two == "th":
            index += 2
            yield ("FV", 0.14, 0.075)
            continue

        if two == "ph":
            index += 2
            yield ("FV", 0.14, 0.075)
            continue

        if two in ("ee", "ea", "ie"):
            index += 2
            yield ("EE", 0.26, 0.12)
            continue

        if two in ("oo", "ou"):
            index += 2
            yield ("OH", 0.42, 0.125)
            continue

        if two == "ow":
            index += 2
            yield ("OH", 0.48, 0.13)
            continue

        if two in ("ai", "ay"):
            index += 2
            yield ("AA", 0.44, 0.12)
            continue

        if two in ("au", "aw"):
            index += 2
            yield ("AA", 0.48, 0.125)
            continue

        if two in ("oy", "oi"):
            index += 2
            yield ("OH", 0.38, 0.12)
            continue

        # ------------------------------
        # Single letter
        # ------------------------------

        index += 1

        if char in "mbp":
            yield ("MBP", 0.02, 0.055)

        elif char in "fv":
            yield ("FV", 0.14, 0.060)

        elif char == "a":
            yield ("AA", 0.44, 0.095)

        elif char in "ei":
            yield ("EE", 0.24, 0.090)

        elif char in "ou":
            yield ("OH", 0.38, 0.095)

        elif char == "w":
            yield ("OH", 0.24, 0.060)

        elif char == "r":
            yield ("OH", 0.20, 0.055)

        elif char in "ly":
            yield ("EE", 0.18, 0.055)

        else:

            # t, d, k, g, n, s, etc. - hold the previous shape
            # rather than jumping to a new one for every consonant.
            yield (None, None, 0.045)


def _resolve_holds(tokens):
    """
    Replaces shape=None ("hold previous") placeholders with the
    actual shape/openness that was current at that point, so the
    result is a plain list of concrete (shape, openness, duration)
    triples.
    """

    resolved = []

    last_shape = "REST"
    last_openness = 0.0

    for shape, openness, duration in tokens:

        if shape is None:
            shape = last_shape
            openness = last_openness

        resolved.append((shape, openness, duration))

        last_shape = shape
        last_openness = openness

    return resolved


def _merge_short_segments(tokens, min_hold):
    """
    Merges (shape, openness, duration) tokens so that none (except
    possibly the very last) is shorter than min_hold seconds.

    When two tokens merge, the merged token keeps the shape of
    whichever one lasted longer (the more visible of the two), and
    its openness becomes their duration-weighted average - so a
    35 ms word gap between two open vowels becomes a slight dip in
    openness rather than the mouth slamming shut for one frame.

    Durations here must already be in the units min_hold uses
    (real seconds in audio-driven mode, fallback timer seconds
    otherwise).
    """

    if min_hold <= 0 or not tokens:
        return list(tokens)

    merged = []

    cur_shape, cur_open, cur_dur = tokens[0]

    for shape, openness, duration in tokens[1:]:

        if cur_dur < min_hold:

            total = cur_dur + duration

            if total > 0:
                cur_open = (
                    cur_open * cur_dur
                    + openness * duration
                ) / total

            if duration > cur_dur:
                cur_shape = shape

            cur_dur = total

        else:

            merged.append((cur_shape, cur_open, cur_dur))

            cur_shape, cur_open, cur_dur = shape, openness, duration

    merged.append((cur_shape, cur_open, cur_dur))

    return merged


def _build_timeline(text, total_duration):
    """
    Builds a list of (start, end, shape, openness) entries spanning
    exactly total_duration seconds.

    The relative durations from _tokenize() are scaled up or down so
    the whole sequence fits the real, measured audio length - so if
    the TTS engine paused longer than the heuristic expects around
    punctuation, or simply spoke faster or slower than the
    letter-count guess assumes, the mouth shapes still land across
    the real clip instead of drifting away from the sound over a
    long sentence.

    Short segments are merged (see MIN_SHAPE_HOLD) after scaling, so
    the minimum hold is measured in real seconds of audio.
    """

    tokens = _resolve_holds(
        list(_tokenize(text))
    )

    if not tokens:
        return []

    predicted_total = sum(
        duration for _, _, duration in tokens
    )

    if predicted_total <= 0:
        return []

    scale = total_duration / predicted_total

    scaled = [
        (shape, openness, duration * scale)
        for shape, openness, duration in tokens
    ]

    scaled = _merge_short_segments(
        scaled,
        MIN_SHAPE_HOLD
    )

    timeline = []
    cursor = 0.0

    for shape, openness, scaled_duration in scaled:

        timeline.append(
            (
                cursor,
                cursor + scaled_duration,
                shape,
                openness
            )
        )

        cursor += scaled_duration

    return timeline


# ==========================
# SPEECH ANIMATOR
# ==========================

class SpeechAnimator:

    def __init__(self):

        self.speaking = False
        self.audio_driven = False

        # ----------------------------------
        # Audio-driven mode
        # ----------------------------------
        # Timing is read from a wall clock (time.monotonic()), not
        # accumulated from dt, so a long sentence can't drift out of
        # sync the way summing per-frame dt can.

        self.timeline = []
        self.timeline_index = 0

        self.envelope = None
        self.envelope_window = 0.02

        self.duration = 0.0
        self.start_time = 0.0

        # ----------------------------------
        # Fallback mode
        # ----------------------------------
        # Used only if the WAV couldn't be measured (see
        # audio_analysis.analyze_wav). Keeps the mouth moving off a
        # per-token timer instead of freezing, at the old accuracy.

        self.fallback_tokens = None
        self.fallback_index = 0
        self.fallback_timer = 0.0
        self.fallback_next_change = 0.0

        self.current_shape = "REST"
        self.current_openness = 0.0


    # ==========================
    # START - AUDIO DRIVEN
    # ==========================

    def start_audio(
        self,
        text,
        duration,
        envelope,
        envelope_window,
        start_time=None
    ):
        """
        Begin audio-driven mouth animation.

        duration is the real, measured length of the WAV about to
        play (seconds). envelope is a list of 0.0-1.0 loudness
        values sampled every envelope_window seconds, or None if it
        couldn't be measured (shapes still play, just without
        loudness scaling). start_time is the time.monotonic() value
        at the moment playback actually began - pass this explicitly
        when it's known (e.g. captured by the audio thread right
        before handing data to aplay) rather than relying on "now",
        since "now" in the caller may be a frame or more later.
        """

        if not text or not duration or duration <= 0:
            self.start_fallback(text)
            return

        timeline = _build_timeline(text, duration)

        if not timeline:
            self.start_fallback(text)
            return

        self.timeline = timeline
        self.timeline_index = 0

        self.envelope = envelope
        self.envelope_window = envelope_window or 0.02

        self.duration = duration
        self.start_time = (
            start_time
            if start_time is not None
            else time.monotonic()
        )

        self.audio_driven = True
        self.speaking = True


    # ==========================
    # START - FALLBACK
    # ==========================

    def start_fallback(self, text):

        if not text:
            return

        self.fallback_tokens = _merge_short_segments(
            _resolve_holds(
                list(_tokenize(text))
            ),
            MIN_SHAPE_HOLD
        )

        self.fallback_index = 0
        self.fallback_timer = 0.0
        self.fallback_next_change = 0.0

        self.current_shape = "REST"
        self.current_openness = 0.0

        self.audio_driven = False
        self.speaking = True


    def start(self, text):
        """
        Kept for compatibility with callers that don't have audio
        timing available - just runs the fallback timer.
        """

        self.start_fallback(text)


    # ==========================
    # STOP
    # ==========================

    def stop(self, state):

        self.speaking = False
        self.audio_driven = False

        # Let the mouth ease shut instead of snapping closed -
        # CharacterState keeps easing target_mouth_open toward
        # mouth_open every frame regardless of self.speaking.
        state.target_mouth_open = 0.0

        # Only idle wander resets when speech ends. The current
        # emotion's own pupil offset (the pose_* fields) is left
        # alone, so e.g. "sad" eyes don't pop back to a neutral
        # look just because the character stopped talking.
        state.target_idle_left_pupil_x = 0
        state.target_idle_left_pupil_y = 0

        state.target_idle_right_pupil_x = 0
        state.target_idle_right_pupil_y = 0


    # ==========================
    # UPDATE
    # ==========================

    def update(self, state, dt):

        if not self.speaking:
            return

        if self.audio_driven:
            self._update_audio(state)
        else:
            self._update_fallback(state, dt)


    def _envelope_at(self, elapsed):
        """
        Loudness (0.0-1.0) at `elapsed` seconds, linearly
        interpolated between envelope samples. Reading the nearest
        sample instead made the openness step every 20 ms, which
        showed up as a fine shimmer on top of the mouth motion.
        """

        if not self.envelope:
            return 1.0

        position = elapsed / self.envelope_window

        last = len(self.envelope) - 1

        if position <= 0:
            return self.envelope[0]

        if position >= last:
            return self.envelope[last]

        lower = int(position)
        frac = position - lower

        return (
            self.envelope[lower] * (1.0 - frac)
            + self.envelope[lower + 1] * frac
        )


    def _update_audio(self, state):

        elapsed = time.monotonic() - self.start_time

        if elapsed >= self.duration:
            self.stop(state)
            return

        lookahead_elapsed = elapsed + AUDIO_LOOKAHEAD

        # Advance the timeline pointer forward only - elapsed only
        # increases while speaking, so this never needs to scan back
        # to the start.
        while (
            self.timeline_index < len(self.timeline) - 1
            and lookahead_elapsed >= self.timeline[self.timeline_index][1]
        ):
            self.timeline_index += 1

        _, _, shape, base_openness = self.timeline[self.timeline_index]

        amplitude = self._envelope_at(elapsed)

        state.mouth_shape = shape
        state.target_mouth_open = base_openness * amplitude


    def _update_fallback(self, state, dt):

        self.fallback_timer += dt

        if self.fallback_timer < self.fallback_next_change:
            return

        self.fallback_timer = 0.0

        if self.fallback_index >= len(self.fallback_tokens):
            self.stop(state)
            return

        shape, openness, duration = self.fallback_tokens[
            self.fallback_index
        ]

        self.fallback_index += 1

        self.current_shape = shape
        self.current_openness = openness

        state.mouth_shape = shape
        state.target_mouth_open = openness

        self.fallback_next_change = duration

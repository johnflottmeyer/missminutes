import sys
import array
import struct


# ==========================
# CONFIG
# ==========================

# Loudness is measured in slices this long.
# 20 ms = 50 slices per second, finer than the 30 FPS display.
ENVELOPE_WINDOW = 0.02

# How many neighboring slices on each side get averaged into each
# loudness value. Raw 20 ms slices pick up the buzz of individual
# syllables and plosives, which made the mouth openness flutter.
# 2 = a 5-slice (100 ms) moving average: still follows words, but
# not every little spike. 0 disables smoothing.
ENVELOPE_SMOOTHING = 2


# ==========================
# SMOOTH
# ==========================

def _smooth(values, radius):
    """
    Centered moving average with the given radius. Uses a running
    sum so it stays O(n) - this runs on every spoken line on a Pi 3B.
    """

    if radius <= 0 or len(values) < 3:
        return values

    count = len(values)

    prefix = [0.0]

    for value in values:
        prefix.append(prefix[-1] + value)

    smoothed = []

    for index in range(count):

        low = max(0, index - radius)
        high = min(count, index + radius + 1)

        smoothed.append(
            (prefix[high] - prefix[low]) / (high - low)
        )

    return smoothed


# ==========================
# ANALYZE WAV
# ==========================

def analyze_wav(wav_bytes, window=ENVELOPE_WINDOW):
    """
    Measure how long a WAV is and how loud it is over time.

    Returns (duration_seconds, envelope, window_seconds).

    envelope is a list of 0.0-1.0 loudness values, one per
    window_seconds slice. If the audio can't be parsed, returns
    (None, None, window) and the caller should fall back to
    text-only timing.

    Uses only the standard library (no numpy) to stay light on a Pi 3B.

    espeak-ng writes a canonical 44 byte header. When it streams to
    a pipe it can't go back and fix the data length, so this ignores
    the length field and just takes everything after the "data" tag.
    """

    try:

        if len(wav_bytes) < 44 or wav_bytes[:4] != b"RIFF":
            return None, None, window

        channels = struct.unpack_from("<H", wav_bytes, 22)[0]
        rate = struct.unpack_from("<I", wav_bytes, 24)[0]
        bits = struct.unpack_from("<H", wav_bytes, 34)[0]

        data_at = wav_bytes.find(b"data", 12, 256)

        if (
            data_at < 0
            or bits != 16
            or channels < 1
            or rate <= 0
        ):
            return None, None, window

        pcm = wav_bytes[data_at + 8:]
        pcm = pcm[: len(pcm) // 2 * 2]

        samples = array.array("h")
        samples.frombytes(pcm)

        if sys.byteorder == "big":
            samples.byteswap()

        if channels > 1:
            samples = samples[::channels]

        if not samples:
            return None, None, window

        duration = len(samples) / float(rate)

        step = max(1, int(rate * window))
        real_window = step / float(rate)

        envelope = []

        for start in range(0, len(samples), step):

            chunk = samples[start:start + step]

            envelope.append(
                sum(map(abs, chunk)) / float(len(chunk))
            )

        envelope = _smooth(
            envelope,
            ENVELOPE_SMOOTHING
        )

        peak = max(envelope)

        if peak <= 0:
            return duration, None, real_window

        reference = peak * 0.8

        envelope = [
            min(1.0, value / reference)
            for value in envelope
        ]

        return duration, envelope, real_window

    except Exception:

        return None, None, window

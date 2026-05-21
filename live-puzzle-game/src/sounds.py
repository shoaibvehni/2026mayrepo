"""Sound effects engine using pygame.mixer - generates all sounds procedurally."""

import io
import wave

import numpy as np
import pygame


def _generate_wav_bytes(samples: np.ndarray, sample_rate: int = 44100) -> bytes:
    """Convert float samples [-1, 1] to WAV bytes."""
    int_samples = np.clip(samples * 32767, -32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int_samples.tobytes())
    buf.seek(0)
    return buf.read()


def _make_sound(samples: np.ndarray, sample_rate: int = 44100) -> pygame.mixer.Sound:
    """Create a pygame Sound from float samples."""
    wav_data = _generate_wav_bytes(samples, sample_rate)
    return pygame.mixer.Sound(io.BytesIO(wav_data))


def _sine(freq: float, duration: float, sr: int = 44100) -> np.ndarray:
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t)


def _noise(duration: float, sr: int = 44100) -> np.ndarray:
    return np.random.uniform(-1, 1, int(sr * duration))


def _envelope(samples: np.ndarray, attack: float = 0.01, release: float = 0.05) -> np.ndarray:
    n = len(samples)
    sr = 44100
    att_n = min(int(attack * sr), n // 2)
    rel_n = min(int(release * sr), n // 2)
    env = np.ones(n)
    if att_n > 0:
        env[:att_n] = np.linspace(0, 1, att_n)
    if rel_n > 0:
        env[-rel_n:] = np.linspace(1, 0, rel_n)
    return samples * env


class SoundEngine:
    """Generates and plays procedural sound effects."""

    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init(44100, -16, 1, 512)

        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._generate_all()

    def _generate_all(self):
        """Generate all sound effects procedurally."""
        sr = 44100

        # --- Grab / Pick up piece ---
        grab = _sine(880, 0.08, sr) * 0.5 + _sine(1320, 0.08, sr) * 0.3
        grab = _envelope(grab, 0.005, 0.03)
        self._sounds["grab"] = _make_sound(grab, sr)

        # --- Drop / Release piece ---
        t = np.linspace(0, 0.12, int(sr * 0.12), endpoint=False)
        drop = np.sin(2 * np.pi * 600 * t * np.exp(-t * 15)) * 0.5
        drop = _envelope(drop, 0.005, 0.04)
        self._sounds["drop"] = _make_sound(drop, sr)

        # --- Correct placement ---
        correct = np.concatenate([
            _envelope(_sine(523, 0.1, sr), 0.005, 0.02),
            _envelope(_sine(659, 0.1, sr), 0.005, 0.02),
            _envelope(_sine(784, 0.15, sr), 0.005, 0.06),
        ]) * 0.4
        self._sounds["correct"] = _make_sound(correct, sr)

        # --- Wrong placement ---
        wrong = _sine(200, 0.15, sr) * 0.3 + _noise(0.15, sr) * 0.05
        wrong = _envelope(wrong, 0.01, 0.06)
        self._sounds["wrong"] = _make_sound(wrong, sr)

        # --- Fist reset ---
        dur = 0.4
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        reset = np.sin(2 * np.pi * 300 * t * np.exp(-t * 3)) * 0.4
        reset += _noise(dur, sr) * 0.08 * np.exp(-t * 5)
        reset = _envelope(reset, 0.01, 0.1)
        self._sounds["reset"] = _make_sound(reset, sr)

        # --- Puzzle complete / Victory ---
        notes = [523, 659, 784, 1047]
        parts = []
        for i, freq in enumerate(notes):
            note = _sine(freq, 0.2, sr) * 0.3
            note += _sine(freq * 2, 0.2, sr) * 0.1
            parts.append(_envelope(note, 0.01, 0.05))
        victory = np.concatenate(parts)
        self._sounds["victory"] = _make_sound(victory, sr)

        # --- Hacking / cyber beep ---
        dur = 0.6
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        hack = np.zeros_like(t)
        for i in range(12):
            freq = np.random.uniform(800, 4000)
            start = int(i * sr * dur / 12)
            end = min(start + int(sr * 0.04), len(t))
            seg_t = np.linspace(0, 0.04, end - start, endpoint=False)
            hack[start:end] += np.sin(2 * np.pi * freq * seg_t) * 0.15
        hack = _envelope(hack, 0.01, 0.05)
        self._sounds["hack_beep"] = _make_sound(hack, sr)

        # --- Space ambient whoosh ---
        dur = 1.0
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        space = _noise(dur, sr) * 0.05
        space += _sine(80, dur, sr) * 0.15
        space += _sine(120, dur, sr) * 0.1
        space *= np.sin(np.pi * t / dur)
        space = _envelope(space, 0.2, 0.3)
        self._sounds["space_whoosh"] = _make_sound(space, sr)

        # --- Movie-style swoosh transition ---
        dur = 0.3
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        swoosh = _noise(dur, sr) * 0.2 * np.exp(-t * 8)
        swoosh += _sine(400, dur, sr) * 0.1 * np.exp(-t * 10)
        swoosh = _envelope(swoosh, 0.005, 0.1)
        self._sounds["swoosh"] = _make_sound(swoosh, sr)

        # --- UI click ---
        click = _sine(1000, 0.03, sr) * 0.3
        click = _envelope(click, 0.002, 0.01)
        self._sounds["click"] = _make_sound(click, sr)

        # --- Chaos warning alarm ---
        parts = []
        for _ in range(4):
            parts.append(_envelope(_sine(1200, 0.08, sr) * 0.25, 0.005, 0.02))
            parts.append(np.zeros(int(sr * 0.04)))
        alarm = np.concatenate(parts)
        self._sounds["alarm"] = _make_sound(alarm, sr)

        # --- Draw stroke sound ---
        dur = 0.05
        draw = _sine(600, dur, sr) * 0.08
        draw = _envelope(draw, 0.005, 0.02)
        self._sounds["draw_tick"] = _make_sound(draw, sr)

        # --- Color change ---
        color_change = np.concatenate([
            _envelope(_sine(800, 0.06, sr), 0.005, 0.02),
            _envelope(_sine(1200, 0.06, sr), 0.005, 0.02),
        ]) * 0.25
        self._sounds["color_change"] = _make_sound(color_change, sr)

        # --- Erase sound ---
        erase = _noise(0.1, sr) * 0.1
        erase = _envelope(erase, 0.01, 0.05)
        self._sounds["erase"] = _make_sound(erase, sr)

        # --- Matrix / data stream ---
        dur = 0.8
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        matrix = np.zeros_like(t)
        for i in range(20):
            freq = 200 + i * 150
            phase = np.random.uniform(0, 2 * np.pi)
            amp = 0.03 * np.exp(-i * 0.15)
            matrix += amp * np.sin(2 * np.pi * freq * t + phase)
        matrix = _envelope(matrix, 0.05, 0.2)
        self._sounds["matrix"] = _make_sound(matrix, sr)

        # --- Countdown tick ---
        tick = _sine(1500, 0.02, sr) * 0.3
        tick = _envelope(tick, 0.002, 0.01)
        self._sounds["tick"] = _make_sound(tick, sr)

    def play(self, name: str, volume: float = 1.0):
        """Play a sound effect by name."""
        sound = self._sounds.get(name)
        if sound is not None:
            sound.set_volume(max(0.0, min(1.0, volume)))
            sound.play()

    def stop_all(self):
        """Stop all playing sounds."""
        pygame.mixer.stop()

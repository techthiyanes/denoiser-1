"""Test transforms."""

from pathlib import Path

import torch
import torchaudio
from torch import Tensor

from denoisers.testing import sine_wave
from denoisers.transforms import (
    BreakTransform,
    ClipTransform,
    FilterTransform,
    FreqMask,
    GaussianNoise,
    NoiseFromFile,
    ReverbFromFile,
    ReverbFromSoundboard,
    SpecTransform,
    TimeMask,
    VolTransform,
)


def test_gaussian_noise() -> None:
    """Test gaussian noise."""
    transform = GaussianNoise(p=1.0)
    audio = sine_wave(800, 1, 16000)
    noisy_audio = transform(audio.clone())

    assert isinstance(noisy_audio, Tensor)
    assert noisy_audio.shape == audio.shape
    assert not torch.isclose(audio, noisy_audio).all()

    noisy_audio = transform(audio.numpy())
    assert isinstance(noisy_audio, Tensor)


def test_filter_transform() -> None:
    """Test filter transform."""
    transform = FilterTransform(p=1.0)
    audio = sine_wave(800, 1, 16000)
    noisy_audio = transform(audio.clone())

    assert isinstance(noisy_audio, Tensor)
    assert audio.shape == noisy_audio.shape
    assert not torch.isclose(audio, noisy_audio).all()

    noisy_audio = transform(audio.numpy())
    assert isinstance(noisy_audio, Tensor)


def test_clip_transform() -> None:
    """Test clip transform."""
    transform = ClipTransform(p=1.0, clip_ceil=0.5, clip_floor=-0.5)
    audio = sine_wave(800, 1, 16000)
    noisy_audio = transform(audio.clone())

    assert isinstance(noisy_audio, Tensor)
    assert audio.shape == noisy_audio.shape
    assert not torch.isclose(audio, noisy_audio).all()

    noisy_audio = transform(audio.numpy())
    assert isinstance(noisy_audio, Tensor)


def test_break_transform() -> None:
    """Test break transform."""
    transform = BreakTransform(p=1.0)
    audio = sine_wave(800, 1, 16000)
    noisy_audio = transform(audio.clone())

    assert isinstance(noisy_audio, Tensor)
    assert audio.shape == noisy_audio.shape
    assert not torch.isclose(audio, noisy_audio).all()

    noisy_audio = transform(audio.numpy())
    assert isinstance(noisy_audio, Tensor)


def test_reverb_from_soundboard() -> None:
    """Test reverb from soundboard."""
    transform = ReverbFromSoundboard(p=1.0)
    audio = sine_wave(800, 1, 16000)
    noisy_audio = transform(audio.clone())

    assert isinstance(noisy_audio, Tensor)
    assert audio.shape == noisy_audio.shape
    assert not torch.isclose(audio, noisy_audio).all()

    noisy_audio = transform(audio.numpy())
    assert isinstance(noisy_audio, Tensor)


def test_spec_transform() -> None:
    """Test spec transform."""
    transform = SpecTransform(p=1.0)
    audio = sine_wave(800, 1, 16000)
    noisy_audio = transform(audio.clone())

    assert isinstance(noisy_audio, Tensor)
    assert audio.shape == noisy_audio.shape
    assert not torch.isclose(audio, noisy_audio).all()

    noisy_audio = transform(audio.numpy())
    assert isinstance(noisy_audio, Tensor)


def test_vol_transform() -> None:
    """Test vol transform."""
    transform = VolTransform(p=1.0, sample_rate=16000)
    audio = sine_wave(800, 1, 16000)
    noisy_audio = transform(audio.clone())

    assert isinstance(noisy_audio, Tensor)
    assert audio.shape == noisy_audio.shape
    assert not torch.isclose(audio, noisy_audio).all()

    noisy_audio = transform(audio.numpy())
    assert isinstance(noisy_audio, Tensor)


def test_noise_from_file(tmpdir) -> None:
    """Test noise from file."""
    save_path = Path(tmpdir) / "noises"
    save_path.mkdir(exist_ok=True, parents=True)

    audio = sine_wave(800, 1, 16000)
    torchaudio.save(str(save_path / "noise.flac"), torch.randn_like(audio), 16000)
    noise, _ = torchaudio.load(str(save_path / "noise.flac"))

    transform = NoiseFromFile(save_path, p=1.0, sample_rate=16000, num_samples=1)
    noisy_audio = transform(audio.numpy())

    torch.testing.assert_close(noisy_audio, audio + noise)
    torch.testing.assert_close(noise, noisy_audio - audio)
    torch.testing.assert_close(audio, noisy_audio - noise)


def test_reverb_from_file() -> None:
    """Test reverb from file."""
    audio = sine_wave(800, 1, 8000)

    transform = ReverbFromFile(
        Path("tests/assets/reverb"),
        p=1.0,
        sample_rate=8000,
        num_samples=1,
    )

    noisy_audio = transform(audio.clone())
    assert isinstance(noisy_audio, Tensor)
    assert audio.shape == noisy_audio.shape
    assert not torch.isclose(audio, noisy_audio).all()

    noisy_audio = transform(audio.numpy())
    assert isinstance(noisy_audio, Tensor)


def test_freq_mask() -> None:
    """Test freq mask."""
    spec = torch.ones(1, 2048, 100)
    noisy_spec = FreqMask(num_masks=2, size=80, p=1.0)(spec)
    assert noisy_spec.shape == spec.shape
    assert noisy_spec.sum() < spec.sum()


def test_time_mask() -> None:
    """Test time mask."""
    spec = torch.ones(1, 2048, 100)
    noisy_spec = TimeMask(num_masks=2, size=20, p=1.0)(spec)
    assert noisy_spec.shape == spec.shape
    assert noisy_spec.sum() < spec.sum()

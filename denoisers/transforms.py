"""Transforms."""
import random
from pathlib import Path
from typing import Tuple, Union

import numpy as np
import torch
import torchaudio
from pedalboard import Reverb  # type: ignore
from torch import Tensor, nn


class GaussianNoise(nn.Module):
    """Gaussian Noise Transform."""

    def __init__(self, p: float = 0.5, db_min: int = 1, db_max: int = 30) -> None:
        super().__init__()
        self.p = p
        self.db_min = db_min
        self.db_max = db_max

    def forward(self, x: Union[Tensor, np.ndarray]) -> Union[Tensor, np.ndarray]:
        """Forward Pass."""
        if isinstance(x, np.ndarray):
            x = torch.from_numpy(x)

        if random.random() <= self.p:
            db = torch.randint(self.db_min, self.db_max, (1,))
            x = torchaudio.functional.add_noise(x, torch.randn_like(x), snr=db)

        return x


class FilterTransform(nn.Module):
    """Filter Transform."""

    def __init__(
        self,
        sample_rate: int = 24000,
        freq_ceil: int = 12000,
        freq_floor: int = 0,
        gain_ceil: int = 20,
        gain_floor: int = -20,
        q: float = 0.707,
        p: float = 0.5,
    ) -> None:
        super().__init__()
        self.sample_rate = sample_rate
        self.freq_ceil = freq_ceil
        self.freq_floor = freq_floor
        self.gain_ceil = gain_ceil
        self.gain_floor = gain_floor
        self.q = q
        self.p = p

    def get_gain(self) -> float:
        """Calculate gain."""
        return (self.gain_floor - self.gain_ceil) * random.random() + self.gain_ceil

    def get_center_freq(self) -> float:
        """Calculate center frequency."""
        return (self.freq_floor - self.freq_ceil) * random.random() + self.freq_ceil

    def forward(self, x: Union[Tensor, np.ndarray]) -> Union[Tensor, np.ndarray]:
        """Forward Pass."""
        if isinstance(x, np.ndarray):
            x = torch.from_numpy(x)

        if random.random() <= self.p:
            gain = self.get_gain()
            center_freq = self.get_center_freq()

            x = torchaudio.functional.equalizer_biquad(
                x,
                sample_rate=self.sample_rate,
                center_freq=center_freq,
                gain=gain,
                Q=self.q,
            )

        return x


class ClipTransform(nn.Module):
    """Clip Transform."""

    def __init__(
        self, clip_ceil: float = 1.0, clip_floor: float = 0.5, p: float = 0.5
    ) -> None:
        super().__init__()
        self.clip_ceil = clip_ceil
        self.clip_floor = clip_floor
        self.p = p

    def get_clip(self) -> float:
        """Calculate clip level."""
        return (self.clip_floor - self.clip_ceil) * random.random() + self.clip_ceil

    def forward(self, x: Union[Tensor, np.ndarray]) -> Tensor:
        """Forward Pass."""
        if isinstance(x, np.ndarray):
            x = torch.from_numpy(x)

        if random.random() <= self.p:
            clip_level = self.get_clip()
            x[torch.abs(x) > clip_level] = clip_level

        return x


class BreakTransform(nn.Module):
    """Break Transform."""

    def __init__(
        self,
        sample_rate: int = 24000,
        break_duration: float = 0.001,
        break_ceil: int = 50,
        break_floor: int = 10,
        p: float = 0.5,
    ) -> None:
        super().__init__()
        self.sample_rate = sample_rate
        self.break_segment = sample_rate * break_duration
        self.break_ceil = break_ceil
        self.break_floor = break_floor
        self.p = p

    def get_mask(self, x: Tensor) -> Tensor:
        """Calculate mask."""
        break_count = (
            self.break_floor - self.break_ceil
        ) * random.random() + self.break_ceil
        break_duration = break_count * self.break_segment
        mask = torch.ones(x.size())
        break_start = int(x.size(0) * random.random())
        break_end = int(min(x.size(0), break_start + break_duration))
        mask[break_start:break_end] = 0
        return mask

    def forward(self, x: Union[Tensor, np.ndarray]) -> Union[Tensor, np.ndarray]:
        """Forward Pass."""
        if isinstance(x, np.ndarray):
            x = torch.from_numpy(x)

        if random.random() <= self.p:
            break_mask = self.get_mask(x)
            x = x * break_mask

        return x


class ReverbFromSoundboard(nn.Module):
    """Reverb Transform."""

    def __init__(self, sample_rate: int = 24000, p: float = 0.5) -> None:
        super().__init__()
        self.sample_rate = sample_rate
        self.reverb = Reverb()
        self.p = p

    @torch.no_grad()
    def forward(self, x: Union[torch.Tensor, np.ndarray]) -> torch.Tensor:
        """Forward Pass."""
        if isinstance(x, torch.Tensor):
            x = x.numpy()

        if random.random() <= self.p:
            self.reverb.room_size = random.random()
            x = self.reverb.process(x, self.sample_rate)

        x = torch.from_numpy(x)

        return x


class SpecTransform(nn.Module):
    """Spectrogram Transform."""

    def __init__(self, p: float = 0.5) -> None:
        super().__init__()
        self.a_hp = torch.tensor([-1.99599, 0.99600])
        self.b_hp = torch.tensor([-2, 1])
        self.p = p

    def _uni_rand(self) -> Tensor:
        return torch.rand(1) - 0.5

    def _rand_resp(self) -> Tuple[Tensor, Tensor, Tensor, Tensor]:
        a1 = 0.75 * self._uni_rand()
        a2 = 0.75 * self._uni_rand()
        b1 = 0.75 * self._uni_rand()
        b2 = 0.75 * self._uni_rand()
        return a1, a2, b1, b2

    def forward(self, x: Union[Tensor, np.ndarray]) -> Union[Tensor, np.ndarray]:
        """Forward Pass."""
        if isinstance(x, np.ndarray):
            x = torch.from_numpy(x)

        if random.random() <= self.p:
            a1, a2, b1, b2 = self._rand_resp()
            x = torchaudio.functional.biquad(
                x, 1, self.b_hp[0], self.b_hp[1], 1, self.a_hp[0], self.a_hp[1]
            )
            x = torchaudio.functional.biquad(x, 1, b1, b2, 1, a1, a2)

        return x


class VolTransform(nn.Module):
    """Volume Transform."""

    def __init__(
        self,
        sample_rate: int = 24000,
        segment_len: float = 0.5,
        vol_ceil: int = 10,
        vol_floor: int = -10,
        p: float = 0.5,
    ) -> None:
        super().__init__()
        self.sample_rate = sample_rate
        self.segment_len = segment_len
        self.segment_samples = int(self.sample_rate * self.segment_len)
        self.vol_ceil = vol_ceil
        self.vol_floor = vol_floor
        self.p = p

    def get_vol(self, sample_length: int) -> Tensor:
        """Get volume."""
        segments = sample_length / (self.segment_len * self.sample_rate)
        step_db = torch.arange(
            self.vol_ceil, self.vol_floor, (self.vol_floor - self.vol_ceil) / segments
        )
        return step_db

    @staticmethod
    def apply_gain(segments: Tensor, db: Tensor) -> Tensor:
        """Apply gain."""
        gain = torch.pow(10.0, (0.05 * db))
        segments = segments * gain
        return segments

    def forward(self, x: Union[Tensor, np.ndarray]) -> Union[Tensor, np.ndarray]:
        """Forward Pass."""
        if isinstance(x, np.ndarray):
            x = torch.from_numpy(x)

        if random.random() <= self.p:
            step_db = self.get_vol(x.size(0))
            for i in range(step_db.size(0)):
                start = i * self.segment_samples
                end = min((i + 1) * self.segment_samples, x.size(0))
                x[start:end] = self.apply_gain(x[start:end], step_db[i])

        return x


class NoiseFromFile(nn.Module):
    """Add background noise from random file."""

    def __init__(
        self,
        root: Path,
        p: float = 1.0,
        sample_rate: int = 24000,
        num_samples: int = 1000,
    ) -> None:
        super().__init__()
        self.root = root
        self.p = p
        self.sample_rate = sample_rate
        noise_paths = random.choices(list(root.glob("**/*.flac")), k=num_samples)
        self.noises = [torchaudio.load(noise)[0] for noise in noise_paths]
        print(f"Loaded {len(self.noises)} noises")

    def forward(self, x: Union[Tensor, np.ndarray]) -> Union[Tensor, np.ndarray]:
        """Forward Pass."""
        if isinstance(x, np.ndarray):
            x = torch.from_numpy(x)

        if random.random() < self.p:
            noise = random.choice(self.noises).to(x.device)
            x = x + noise[:, : x.size(1)]

        return x


class ReverbFromFile(nn.Module):
    """Add reverb to a sample from a rir file."""

    def __init__(
        self,
        root: Path,
        p: float = 0.5,
        sample_rate: int = 24000,
        num_samples: int = 1000,
    ) -> None:
        super().__init__()
        self.root = root
        self.p = p
        self.sample_rate = sample_rate
        response_paths = random.choices(list(root.glob("**/*.wav")), k=num_samples)
        self.responses = [torchaudio.load(r)[0] for r in response_paths]

    def forward(self, x: Union[Tensor, np.ndarray]) -> Union[Tensor, np.ndarray]:
        """Forward Pass."""
        if isinstance(x, np.ndarray):
            x = torch.from_numpy(x)

        if random.random() < self.p:
            rir_raw = random.choice(self.responses)
            rir_raw = rir_raw[random.randint(0, rir_raw.shape[0] - 1)][None]
            rir = rir_raw
            rir = rir / torch.norm(rir, p=2)
            RIR = torch.flip(rir, [1])
            x = torch.nn.functional.pad(x, (RIR.shape[1] - 1, 0))
            x = nn.functional.conv1d(x[None, ...], RIR[None, ...])[0]

        return x


class FreqMask(nn.Module):
    """Frequency Mask."""

    def __init__(self, num_masks: int, size: int, p: float = 0.5) -> None:
        super().__init__()
        self.num_masks = num_masks
        self.size = size
        self.p = p
        self.transform = torchaudio.transforms.FrequencyMasking(
            freq_mask_param=self.size
        )

    def forward(self, x: Tensor) -> Tensor:
        """Forward Pass."""
        if random.random() <= self.p:
            for i in range(self.num_masks):
                x = self.transform(x)
        return x


class TimeMask(nn.Module):
    """Time Mask."""

    def __init__(self, num_masks: int, size: int, p: float = 0.5) -> None:
        super().__init__()
        self.num_masks = num_masks
        self.size = size
        self.p = p
        self.transform = torchaudio.transforms.TimeMasking(
            time_mask_param=self.size, p=1.0
        )

    def forward(self, x: Tensor) -> Tensor:
        """Forward Pass."""
        if random.random() <= self.p:
            for i in range(self.num_masks):
                x = self.transform(x)
        return x

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import time
import numpy as np


@dataclass(slots=True)
class ImageFrame:
    """A BGR image plus acquisition metadata."""
    image: np.ndarray
    camera_id: str
    sequence: int
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.image, np.ndarray):
            raise TypeError("image must be a numpy.ndarray")
        if self.image.ndim not in (2, 3):
            raise ValueError("image must be a 2D or 3D array")

    @property
    def width(self) -> int:
        return int(self.image.shape[1])

    @property
    def height(self) -> int:
        return int(self.image.shape[0])

    @property
    def shape(self) -> tuple[int, ...]:
        return self.image.shape

    def copy(self) -> "ImageFrame":
        return ImageFrame(
            image=self.image.copy(), camera_id=self.camera_id,
            sequence=self.sequence, timestamp=self.timestamp,
            metadata=dict(self.metadata),
        )

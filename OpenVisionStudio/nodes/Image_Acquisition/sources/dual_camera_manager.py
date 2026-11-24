from __future__ import annotations

from dataclasses import dataclass
from .gstreamer_receiver import CameraReceiver


@dataclass(slots=True)
class CameraStatus:
    camera_id: str
    port: int
    connected: bool
    fps: float
    frames_received: int
    last_error: str | None


class DualCameraManager:
    """Own and coordinate two independent GStreamer camera receivers."""

    def __init__(self, camera_0_port: int = 5000, camera_1_port: int = 5001,
                 host: str = "0.0.0.0", demux_latency_ms: int = 50):
        self.camera_0 = CameraReceiver("camera_0", camera_0_port, host, demux_latency_ms)
        self.camera_1 = CameraReceiver("camera_1", camera_1_port, host, demux_latency_ms)
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        started = []
        try:
            self.camera_0.start()
            started.append(self.camera_0)
            self.camera_1.start()
            started.append(self.camera_1)
            self._started = True
        except Exception:
            for receiver in reversed(started):
                receiver.stop()
            raise

    def get_frames(self, copy: bool = True) -> dict[str, object]:
        frame0, seq0, ts0 = self.camera_0.get_latest_frame(copy)
        frame1, seq1, ts1 = self.camera_1.get_latest_frame(copy)
        return {
            "camera_0": {"image": frame0, "sequence": seq0, "timestamp_monotonic": ts0},
            "camera_1": {"image": frame1, "sequence": seq1, "timestamp_monotonic": ts1},
        }

    def get_status(self) -> dict[str, CameraStatus]:
        result = {}
        for receiver in (self.camera_0, self.camera_1):
            stats = receiver.stats
            result[receiver.camera_id] = CameraStatus(
                camera_id=receiver.camera_id,
                port=receiver.port,
                connected=receiver.is_connected,
                fps=stats.fps,
                frames_received=stats.frames_received,
                last_error=stats.last_error,
            )
        return result

    def stop(self) -> None:
        self.camera_0.stop()
        self.camera_1.stop()
        self._started = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()

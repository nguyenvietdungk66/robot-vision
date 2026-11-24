from __future__ import annotations

from typing import Any
from core.node_system.base_node import BaseNode
from core.node_system.ports import Port, PortDirection, PortType
from core.data.image_frame import ImageFrame
from .sources.dual_camera_manager import DualCameraManager


class ImageAcquisitionNode(BaseNode):
    """Live dual-camera source node with two independent image outputs.

    Outputs:
        camera_0: ImageFrame from UDP port 5000
        camera_1: ImageFrame from UDP port 5001
    """
    node_type = "Image_Acquisition"

    def __init__(self, camera_0_port: int = 5000, camera_1_port: int = 5001,
                 host: str = "0.0.0.0", demux_latency_ms: int = 50,
                 name: str | None = None, node_id: str | None = None):
        super().__init__(name=name or self.node_type, node_id=node_id)
        self.manager = DualCameraManager(
            camera_0_port=camera_0_port,
            camera_1_port=camera_1_port,
            host=host,
            demux_latency_ms=demux_latency_ms,
        )
        self._started = False
        self.add_output(Port("camera_0", PortDirection.OUTPUT, PortType.IMAGE,
                             "BGR image from left/first camera"))
        self.add_output(Port("camera_1", PortDirection.OUTPUT, PortType.IMAGE,
                             "BGR image from right/second camera"))

    def start(self) -> None:
        if not self._started:
            self.manager.start()
            self._started = True

    def process(self, inputs: dict[str, Any] | None = None) -> dict[str, ImageFrame | None]:
        if not self.enabled:
            return {"camera_0": None, "camera_1": None}
        if not self._started:
            self.start()
        frames = self.manager.get_frames(copy=True)
        outputs: dict[str, ImageFrame | None] = {}
        for key in ("camera_0", "camera_1"):
            item = frames[key]
            image = item["image"]
            outputs[key] = None if image is None else ImageFrame(
                image=image,
                camera_id=key,
                sequence=item["sequence"],
                metadata={"source": "gstreamer_udp", "port":
                          self.manager.camera_0.port if key == "camera_0" else self.manager.camera_1.port,
                          "timestamp_monotonic": item["timestamp_monotonic"]},
            )
        return outputs

    def get_status(self):
        return self.manager.get_status()

    def stop(self) -> None:
        self.manager.stop()
        self._started = False

    def reset(self) -> None:
        self.stop()

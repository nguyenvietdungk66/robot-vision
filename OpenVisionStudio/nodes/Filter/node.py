from __future__ import annotations
from typing import Any
from core.node_system.base_node import BaseNode
from core.node_system.ports import Port, PortDirection, PortType
from core.data.image_frame import ImageFrame
from nodes.Filter.registry import FILTERS


class FilterNode(BaseNode):
    node_type = "Filter"

    def __init__(self, algorithm: str = "Gaussian Blur", parameters: dict[str, Any] | None = None,
                 name: str | None = None, node_id: str | None = None):
        super().__init__(name=name or self.node_type, node_id=node_id)
        if algorithm not in FILTERS:
            raise ValueError(f"Unknown filter: {algorithm}")
        self.algorithm = algorithm
        self.parameters = dict(parameters or {})
        self.add_input(Port("image", PortDirection.INPUT, PortType.IMAGE, "Input image"))
        self.add_output(Port("image", PortDirection.OUTPUT, PortType.IMAGE, "Filtered image"))

    def process(self, inputs=None):
        frame = (inputs or {}).get("image")
        if frame is None:
            return {"image": None}
        if not isinstance(frame, ImageFrame):
            raise TypeError("FilterNode expects an ImageFrame")
        result = FILTERS[self.algorithm](frame.image, **self.parameters)
        return {"image": ImageFrame(result, frame.camera_id, frame.sequence,
                                    metadata={**frame.metadata, "filter": self.algorithm})}

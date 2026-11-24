from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import uuid4
from typing import Any
from .ports import Port, PortDirection


class BaseNode(ABC):
    """Runtime contract shared by all processing nodes (GUI-independent)."""

    node_type = "BaseNode"

    def __init__(self, name: str | None = None, node_id: str | None = None):
        self.node_id = node_id or str(uuid4())
        self.name = name or self.node_type
        self.inputs: dict[str, Port] = {}
        self.outputs: dict[str, Port] = {}
        self.enabled = True

    def add_input(self, port: Port) -> None:
        if port.direction != PortDirection.INPUT:
            raise ValueError("Input port must have INPUT direction")
        self.inputs[port.name] = port

    def add_output(self, port: Port) -> None:
        if port.direction != PortDirection.OUTPUT:
            raise ValueError("Output port must have OUTPUT direction")
        self.outputs[port.name] = port

    @abstractmethod
    def process(self, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute one node step and return values keyed by output port."""
        raise NotImplementedError

    def reset(self) -> None:
        """Optional state reset hook."""

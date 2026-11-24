from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class PortDirection(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


class PortType(str, Enum):
    IMAGE = "image"
    ANY = "any"


@dataclass(slots=True)
class Port:
    name: str
    direction: PortDirection
    data_type: PortType = PortType.ANY
    description: str = ""


@dataclass(slots=True, frozen=True)
class Connection:
    source_node_id: str
    source_port: str
    target_node_id: str
    target_port: str

    def __post_init__(self) -> None:
        if not all((self.source_node_id, self.source_port,
                    self.target_node_id, self.target_port)):
            raise ValueError("Connection endpoints must be non-empty")

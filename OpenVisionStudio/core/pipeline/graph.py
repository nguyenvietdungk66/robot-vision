from __future__ import annotations

from dataclasses import dataclass, field
from core.node_system.base_node import BaseNode
from core.node_system.ports import Connection, PortType


@dataclass
class PipelineGraph:
    nodes: dict[str, BaseNode] = field(default_factory=dict)
    connections: list[Connection] = field(default_factory=list)

    def add_node(self, node: BaseNode) -> None:
        if node.node_id in self.nodes:
            raise ValueError(f"Duplicate node id: {node.node_id}")
        self.nodes[node.node_id] = node

    def remove_node(self, node_id: str) -> None:
        if node_id not in self.nodes:
            return
        del self.nodes[node_id]
        self.connections = [c for c in self.connections
                            if c.source_node_id != node_id and c.target_node_id != node_id]

    def connect(self, source_id: str, source_port: str,
                target_id: str, target_port: str) -> Connection:
        try:
            source = self.nodes[source_id]
            target = self.nodes[target_id]
            out_port = source.outputs[source_port]
            in_port = target.inputs[target_port]
        except KeyError as exc:
            raise ValueError(f"Unknown node or port: {exc}") from exc
        if out_port.data_type not in (in_port.data_type, PortType.ANY) and in_port.data_type != PortType.ANY:
            raise TypeError(f"Incompatible ports: {out_port.data_type} -> {in_port.data_type}")
        if any(c.target_node_id == target_id and c.target_port == target_port for c in self.connections):
            raise ValueError("Input port already has a connection")
        connection = Connection(source_id, source_port, target_id, target_port)
        self.connections.append(connection)
        try:
            self.topological_order()
        except ValueError:
            self.connections.remove(connection)
            raise
        return connection

    def topological_order(self) -> list[BaseNode]:
        indegree = {node_id: 0 for node_id in self.nodes}
        children = {node_id: [] for node_id in self.nodes}
        for c in self.connections:
            if c.source_node_id not in self.nodes or c.target_node_id not in self.nodes:
                raise ValueError("Connection references a missing node")
            indegree[c.target_node_id] += 1
            children[c.source_node_id].append(c.target_node_id)
        ready = [node_id for node_id, degree in indegree.items() if degree == 0]
        ordered = []
        while ready:
            current = ready.pop(0)
            ordered.append(self.nodes[current])
            for child in children[current]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
        if len(ordered) != len(self.nodes):
            raise ValueError("Pipeline contains a cycle")
        return ordered

    def inputs_for(self, node: BaseNode, values: dict[str, dict[str, object]]) -> dict[str, object]:
        result = {}
        for c in self.connections:
            if c.target_node_id == node.node_id:
                result[c.target_port] = values.get(c.source_node_id, {}).get(c.source_port)
        return result

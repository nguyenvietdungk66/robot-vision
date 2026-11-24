from __future__ import annotations

from core.pipeline.graph import PipelineGraph


class PipelineExecutor:
    """Synchronous frame-tick executor. Call tick from a worker, not the GUI thread."""
    def __init__(self, graph: PipelineGraph):
        self.graph = graph
        self.last_values: dict[str, dict[str, object]] = {}
        self._started: set[str] = set()

    def start(self) -> None:
        for node in self.graph.topological_order():
            start = getattr(node, "start", None)
            if callable(start) and node.node_id not in self._started:
                start()
                self._started.add(node.node_id)

    def tick(self) -> dict[str, dict[str, object]]:
        values: dict[str, dict[str, object]] = {}
        for node in self.graph.topological_order():
            if not node.enabled:
                values[node.node_id] = {}
                continue
            node_inputs = self.graph.inputs_for(node, values)
            values[node.node_id] = node.process(node_inputs)
        self.last_values = values
        return values

    def stop(self) -> None:
        for node in reversed(self.graph.topological_order()):
            stop = getattr(node, "stop", None)
            if callable(stop):
                stop()
        self._started.clear()

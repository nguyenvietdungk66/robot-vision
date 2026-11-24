import unittest
import numpy as np
from core.node_system.base_node import BaseNode
from core.node_system.ports import Port, PortDirection, PortType
from core.pipeline.graph import PipelineGraph
from core.pipeline.executor import PipelineExecutor
from core.data.image_frame import ImageFrame
from nodes.Filter.node import FilterNode


class SourceNode(BaseNode):
    node_type = "TestSource"
    def __init__(self):
        super().__init__()
        self.add_output(Port("image", PortDirection.OUTPUT, PortType.IMAGE))
    def process(self, inputs=None):
        return {"image": ImageFrame(np.zeros((16, 16, 3), np.uint8), "test", 1)}


class PipelineTests(unittest.TestCase):
    def test_source_to_filter_execution(self):
        graph = PipelineGraph()
        source, target = SourceNode(), FilterNode("Gaussian Blur", {"kernel_size": 3})
        graph.add_node(source)
        graph.add_node(target)
        graph.connect(source.node_id, "image", target.node_id, "image")
        result = PipelineExecutor(graph).tick()
        output = result[target.node_id]["image"]
        self.assertIsInstance(output, ImageFrame)
        self.assertEqual(output.shape, (16, 16, 3))
        self.assertEqual(output.metadata["filter"], "Gaussian Blur")

    def test_cycle_is_rejected(self):
        graph = PipelineGraph()
        a, b = FilterNode(), FilterNode()
        graph.add_node(a)
        graph.add_node(b)
        graph.connect(a.node_id, "image", b.node_id, "image")
        with self.assertRaises(ValueError):
            graph.connect(b.node_id, "image", a.node_id, "image")

    def test_single_input_connection(self):
        graph = PipelineGraph()
        a, b, c = SourceNode(), FilterNode(), SourceNode()
        for node in (a, b, c): graph.add_node(node)
        graph.connect(a.node_id, "image", b.node_id, "image")
        with self.assertRaises(ValueError):
            graph.connect(c.node_id, "image", b.node_id, "image")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QMessageBox, QSplitter)
from PySide6.QtGui import QImage, QPixmap

from core.pipeline.graph import PipelineGraph
from core.pipeline.executor import PipelineExecutor
from nodes.Image_Acquisition import ImageAcquisitionNode
from nodes.Filter.node import FilterNode
from app.node_editor.editor import NodeEditorScene, NodeEditorView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenVision Studio")
        self.resize(1500, 900)
        self.graph = PipelineGraph()
        self.executor = PipelineExecutor(self.graph)

        central = QWidget()
        root = QVBoxLayout(central)
        toolbar = QHBoxLayout()
        self.add_acq_btn = QPushButton("+ Image Acquisition")
        self.add_filter_btn = QPushButton("+ Filter")
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.status = QLabel("Ready — click an output port, then an input port to connect nodes")
        for widget in (self.add_acq_btn, self.add_filter_btn, self.start_btn, self.stop_btn, self.status):
            toolbar.addWidget(widget)
        root.addLayout(toolbar)

        self.scene = NodeEditorScene(self)
        self.scene.graph = self.graph
        self.scene.connection_callback = self.connect_nodes
        self.editor = NodeEditorView(self.scene)
        self.preview0 = QLabel("Camera 0")
        self.preview1 = QLabel("Camera 1")
        for label in (self.preview0, self.preview1):
            label.setMinimumSize(320, 180)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("background:#0b1220;color:#cbd5e1;border:1px solid #334155")
        previews = QWidget()
        preview_layout = QHBoxLayout(previews)
        preview_layout.addWidget(self.preview0)
        preview_layout.addWidget(self.preview1)
        splitter = QSplitter()
        splitter.setOrientation(Qt.Vertical)
        splitter.addWidget(self.editor)
        splitter.addWidget(previews)
        splitter.setSizes([650, 220])
        root.addWidget(splitter)
        self.setCentralWidget(central)

        self.add_acq_btn.clicked.connect(self.add_acquisition)
        self.add_filter_btn.clicked.connect(self.add_filter)
        self.start_btn.clicked.connect(self.start_pipeline)
        self.stop_btn.clicked.connect(self.stop_pipeline)
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.process_tick)

    def add_acquisition(self):
        node = ImageAcquisitionNode()
        self.graph.add_node(node)
        self.scene.add_runtime_node(node)
        self.scene.refresh_edges()
        self.status.setText("Image_Acquisition added — outputs: camera_0, camera_1")

    def add_filter(self):
        node = FilterNode()
        self.graph.add_node(node)
        self.scene.add_runtime_node(node)
        self.scene.refresh_edges()
        self.status.setText("Filter added — connect an image output to its image input")

    def connect_nodes(self, source, source_port, target, target_port):
        self.graph.connect(source.node_id, source_port, target.node_id, target_port)
        self.status.setText(f"Connected {source.name}.{source_port} → {target.name}.{target_port}")

    def start_pipeline(self):
        try:
            self.executor.start()
            self.timer.start()
            self.status.setText("Pipeline running")
        except Exception as exc:
            QMessageBox.critical(self, "Pipeline start failed", str(exc))

    def process_tick(self):
        try:
            values = self.executor.tick()
            for node in self.graph.nodes.values():
                outputs = values.get(node.node_id, {})
                if node.node_type == "Image_Acquisition":
                    self._show_frame(self.preview0, outputs.get("camera_0"))
                    self._show_frame(self.preview1, outputs.get("camera_1"))
        except Exception as exc:
            self.timer.stop()
            self.status.setText(f"Pipeline error: {exc}")
            QMessageBox.critical(self, "Pipeline error", str(exc))

    @staticmethod
    def _show_frame(label, frame):
        if frame is None:
            return
        image = frame.image
        height, width = image.shape[:2]
        qimage = QImage(image.data, width, height, image.strides[0], QImage.Format_BGR888).copy()
        label.setPixmap(QPixmap.fromImage(qimage).scaled(
            label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def stop_pipeline(self):
        self.timer.stop()
        self.executor.stop()
        self.status.setText("Pipeline stopped")

    def closeEvent(self, event):
        self.stop_pipeline()
        super().closeEvent(event)

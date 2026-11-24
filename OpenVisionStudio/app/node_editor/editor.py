from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QBrush, QPen, QPainter, QColor
from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsItem,
                               QGraphicsRectItem, QGraphicsLineItem, QMenu)


class PortItem(QGraphicsRectItem):
    def __init__(self, owner, name, direction, index):
        super().__init__(-6, -6, 12, 12, owner)
        self.owner, self.name, self.direction = owner, name, direction
        self.setPos(0 if direction == "input" else owner.WIDTH, 48 + index * 24)
        self.setBrush(QBrush(QColor("#38bdf8" if direction == "input" else "#34d399")))
        self.setPen(QPen(QColor("#0f172a"), 1))
        self.setToolTip(f"{direction}: {name}")


class NodeItem(QGraphicsRectItem):
    WIDTH, HEIGHT = 190, 110

    def __init__(self, node, scene):
        super().__init__(0, 0, self.WIDTH, self.HEIGHT)
        self.node, self.editor_scene = node, scene
        self.setBrush(QBrush(QColor("#202b3b")))
        self.setPen(QPen(QColor("#64748b"), 1.5))
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(1)
        self.port_items = {}
        for index, name in enumerate(node.inputs):
            self.port_items[("input", name)] = PortItem(self, name, "input", index)
        for index, name in enumerate(node.outputs):
            self.port_items[("output", name)] = PortItem(self, name, "output", index)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#e2e8f0")))
        painter.drawText(QRectF(12, 12, self.WIDTH - 24, 24), Qt.AlignLeft, self.node.name)
        painter.setPen(QPen(QColor("#94a3b8")))
        painter.drawText(QRectF(12, 38, self.WIDTH - 24, 20), Qt.AlignLeft,
                         self.node.node_type)
        for (direction, name), port in self.port_items.items():
            y = port.y() - 7
            if direction == "input":
                painter.drawText(QPointF(14, y + 17), name)
            else:
                painter.drawText(QPointF(self.WIDTH - 75, y + 17), name)

    def mousePressEvent(self, event):
        local = event.position() if hasattr(event, "position") else event.pos()
        if local.x() < 12 or local.x() > self.WIDTH - 12:
            direction = "input" if local.x() < 12 else "output"
            ports = [p for (d, _), p in self.port_items.items() if d == direction]
            if ports:
                nearest = min(ports, key=lambda p: abs(p.y() - local.y()))
                if abs(nearest.y() - local.y()) < 16:
                    self.editor_scene.port_clicked.emit(self, direction, nearest.name)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def itemChange(self, change, value):
        result = super().itemChange(change, value)
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.editor_scene.refresh_edges()
        return result

    def port_scene_pos(self, direction, name):
        port = self.port_items[(direction, name)]
        return port.mapToScene(QPointF(0, 0))


class NodeEditorScene(QGraphicsScene):
    port_clicked = Signal(object, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 1800, 1100)
        self.node_items = {}
        self.edge_items = []
        self.pending_output = None
        self.port_clicked.connect(self._handle_port_click)
        self.connection_callback = None

    def add_runtime_node(self, node, position=None):
        item = NodeItem(node, self)
        self.addItem(item)
        item.setPos(QPointF(*(position or (100 + len(self.node_items) * 230, 120))))
        self.node_items[node.node_id] = item
        return item

    def _handle_port_click(self, item, direction, port_name):
        if direction == "output":
            self.pending_output = (item, port_name)
            return
        if self.pending_output and self.pending_output[0] is not item:
            source_item, source_port = self.pending_output
            if self.connection_callback:
                try:
                    self.connection_callback(source_item.node, source_port, item.node, port_name)
                    self.pending_output = None
                    self.refresh_edges()
                except Exception as exc:
                    print(f"Connection rejected: {exc}", flush=True)

    def refresh_edges(self):
        for edge in self.edge_items:
            self.removeItem(edge)
        self.edge_items.clear()
        graph = getattr(self, "graph", None)
        if graph is None:
            return
        for connection in graph.connections:
            source = self.node_items.get(connection.source_node_id)
            target = self.node_items.get(connection.target_node_id)
            if source is None or target is None:
                continue
            p1 = source.port_scene_pos("output", connection.source_port)
            p2 = target.port_scene_pos("input", connection.target_port)
            edge = QGraphicsLineItem(p1.x(), p1.y(), p2.x(), p2.y())
            edge.setPen(QPen(QColor("#34d399"), 2.5))
            edge.setZValue(0)
            self.addItem(edge)
            self.edge_items.append(edge)


class NodeEditorView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor("#111827")))
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

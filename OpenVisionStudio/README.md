# OpenVision Studio

A PySide6 node-based machine-vision application. The existing dual-camera GStreamer backend is retained.

## Environment

Use the Python interpreter where `gstreamer-bundle`, PyGObject, OpenCV, NumPy and PySide6 are installed:

```powershell
python -m pip install -r requirements.txt
python main.py
```

The GStreamer receiver additionally requires the Jetson Nano senders to be running and UDP ports 5000 and 5001 to be reachable.

## Current node editor increment

- Add `Image_Acquisition` and `Filter` nodes from the toolbar.
- Click an output port (right side, green), then an input port (left side, blue) to connect them.
- Drag nodes to arrange the graph; mouse wheel zooms the canvas.
- Start begins acquisition and periodic graph evaluation; Stop releases camera pipelines.
- The two acquisition frames are previewed below the canvas.
- The graph executor evaluates nodes in topological order and rejects cycles and multiple connections to a single input.

The `Image_Acquisition` node exposes `camera_0` and `camera_1` as `ImageFrame` outputs. A Filter node accepts an `ImageFrame` and supports Gaussian Blur, Bilateral Filter and Non-Local Means.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Important limitations in this increment

- Pipeline evaluation currently runs on the GUI timer thread. This is a functional first integration, not the final real-time threading architecture; move graph execution to a worker thread before adding expensive processing nodes.
- Node positions and graph connections are not yet persisted to project files.
- The current editor supports adding and connecting nodes, but not deletion, rerouting or editing node parameters through a property panel.
- Camera preview is shown for the acquisition node; downstream Filter outputs are executed but do not yet have dedicated preview widgets.
- The two camera streams are independent and are not guaranteed to be hardware synchronized.

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst

Gst.init(None)


@dataclass(slots=True)
class ReceiverStats:
    fps: float = 0.0
    frames_received: int = 0
    last_frame_monotonic: float | None = None
    last_error: str | None = None


class CameraReceiver:
    """Receive one MPEG-TS/H.264 UDP stream and expose its latest BGR frame."""

    def __init__(self, camera_id: str, port: int, host: str = "0.0.0.0",
                 demux_latency_ms: int = 50, appsink_buffers: int = 1):
        self.camera_id = camera_id
        self.port = int(port)
        self.host = host
        self.demux_latency_ms = int(demux_latency_ms)
        self.appsink_buffers = int(appsink_buffers)

        self.pipeline = None
        self.appsink = None
        self.queue = None
        self.bus = None
        self.running = False
        self.thread: threading.Thread | None = None

        self._lock = threading.Lock()
        self._latest_frame: np.ndarray | None = None
        self._sequence = 0
        self.stats = ReceiverStats()
        self._fps_count = 0
        self._fps_started = time.perf_counter()
        self._error_lock = threading.Lock()

    def _log(self, message: str) -> None:
        print(f"[{self.camera_id}] {message}", flush=True)

    def _on_pad_added(self, demux, pad) -> None:
        caps = pad.get_current_caps() or pad.query_caps(None)
        if caps is None or caps.is_empty():
            self._log(f"Pad {pad.get_name()} has no caps")
            return
        media_type = caps.get_structure(0).get_name()
        self._log(f"Demux pad {pad.get_name()}: {caps.to_string()}")
        if media_type != "video/x-h264":
            return
        sink_pad = self.queue.get_static_pad("sink")
        if sink_pad.is_linked():
            self._log("Video queue is already linked; ignoring additional video pad")
            return
        result = pad.link(sink_pad)
        if result != Gst.PadLinkReturn.OK:
            self._set_error(f"Could not link H.264 pad: {result}")
        else:
            self._log("H.264 pad linked")

    def _set_error(self, message: str) -> None:
        with self._error_lock:
            self.stats.last_error = message
        self._log(message)

    def _make(self, factory: str, name: str):
        element = Gst.ElementFactory.make(factory, name)
        if element is None:
            raise RuntimeError(f"Missing GStreamer element: {factory}")
        return element

    def _create_pipeline(self) -> None:
        self.pipeline = Gst.Pipeline.new(f"pipeline_{self.port}")
        if self.pipeline is None:
            raise RuntimeError("Could not create GStreamer pipeline")

        source = self._make("udpsrc", f"udp_source_{self.port}")
        demux = self._make("tsdemux", f"ts_demux_{self.port}")
        self.queue = self._make("queue", f"h264_queue_{self.port}")
        parser = self._make("h264parse", f"h264_parser_{self.port}")
        decoder = self._make("avdec_h264", f"h264_decoder_{self.port}")
        converter = self._make("videoconvert", f"bgr_converter_{self.port}")
        capsfilter = self._make("capsfilter", f"bgr_caps_{self.port}")
        self.appsink = self._make("appsink", f"frame_sink_{self.port}")

        source.set_property("port", self.port)
        source.set_property("address", self.host)
        source.set_property("buffer-size", 65536)
        source.set_property("caps", Gst.Caps.from_string(
            "video/mpegts,systemstream=(boolean)true"))
        demux.set_property("latency", self.demux_latency_ms)

        # Keep compressed H.264 data intact; drop stale decoded frames at appsink.
        self.queue.set_property("max-size-buffers", 0)
        self.queue.set_property("max-size-bytes", 0)
        self.queue.set_property("max-size-time", 500_000_000)

        capsfilter.set_property("caps", Gst.Caps.from_string(
            "video/x-raw,format=BGR"))
        self.appsink.set_property("emit-signals", False)
        self.appsink.set_property("max-buffers", self.appsink_buffers)
        self.appsink.set_property("drop", True)
        self.appsink.set_property("sync", False)
        if self.appsink.find_property("wait-on-eos"):
            self.appsink.set_property("wait-on-eos", False)

        elements = [source, demux, self.queue, parser, decoder,
                    converter, capsfilter, self.appsink]
        for element in elements:
            self.pipeline.add(element)

        if not source.link(demux):
            raise RuntimeError("Could not link udpsrc to tsdemux")
        chain = [self.queue, parser, decoder, converter, capsfilter, self.appsink]
        for left, right in zip(chain, chain[1:]):
            if not left.link(right):
                raise RuntimeError(f"Could not link {left.get_name()} to {right.get_name()}")
        demux.connect("pad-added", self._on_pad_added)
        self.bus = self.pipeline.get_bus()

    def start(self) -> None:
        if self.running:
            return
        self._create_pipeline()
        result = self.pipeline.set_state(Gst.State.PLAYING)
        if result == Gst.StateChangeReturn.FAILURE:
            self.pipeline.set_state(Gst.State.NULL)
            raise RuntimeError(f"Could not start camera receiver on UDP {self.port}")
        self.running = True
        self.thread = threading.Thread(target=self._receive_loop,
                                       name=f"receiver-{self.port}", daemon=True)
        self.thread.start()
        self._log(f"Started; listening on UDP {self.port}")

    def _poll_bus(self) -> None:
        while self.bus is not None:
            message = self.bus.pop()
            if message is None:
                break
            if message.type == Gst.MessageType.ERROR:
                error, debug = message.parse_error()
                self._set_error(f"GStreamer error: {error}; {debug}")
                self.running = False
            elif message.type == Gst.MessageType.WARNING:
                warning, debug = message.parse_warning()
                self._log(f"GStreamer warning: {warning}; {debug}")
            elif message.type == Gst.MessageType.EOS:
                self._log("End of stream")
                self.running = False

    def _receive_loop(self) -> None:
        while self.running:
            # This action signal is used because this Windows PyGObject build
            # does not expose GstAppSink.try_pull_sample as a Python method.
            sample = self.appsink.emit("try-pull-sample", 100 * Gst.MSECOND)
            self._poll_bus()
            if not self.running:
                break
            if sample is None:
                continue

            caps = sample.get_caps()
            structure = caps.get_structure(0)
            width = int(structure.get_value("width"))
            height = int(structure.get_value("height"))
            buffer = sample.get_buffer()
            ok, map_info = buffer.map(Gst.MapFlags.READ)
            if not ok:
                self._set_error("Could not map decoded video buffer")
                continue
            try:
                # BGR frames from videoconvert are packed; stride can be padded.
                info = caps.get_video_info() if hasattr(caps, "get_video_info") else None
                raw = np.frombuffer(map_info.data, dtype=np.uint8)
                expected = width * height * 3
                if raw.size < expected:
                    self._set_error(f"Unexpected BGR buffer size {raw.size}; expected at least {expected}")
                    continue
                frame = raw[:expected].reshape((height, width, 3)).copy()
            finally:
                buffer.unmap(map_info)

            now = time.perf_counter()
            with self._lock:
                self._latest_frame = frame
                self._sequence += 1
                self.stats.frames_received += 1
                self.stats.last_frame_monotonic = now
            self._fps_count += 1
            elapsed = now - self._fps_started
            if elapsed >= 1.0:
                self.stats.fps = self._fps_count / elapsed
                self._fps_count = 0
                self._fps_started = now

    def get_latest_frame(self, copy: bool = True) -> tuple[np.ndarray | None, int, float | None]:
        with self._lock:
            if self._latest_frame is None:
                return None, self._sequence, self.stats.last_frame_monotonic
            frame = self._latest_frame.copy() if copy else self._latest_frame
            return frame, self._sequence, self.stats.last_frame_monotonic

    @property
    def is_connected(self) -> bool:
        last = self.stats.last_frame_monotonic
        return bool(self.running and last is not None and
                    (time.perf_counter() - last) < 2.0)

    def stop(self) -> None:
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self.pipeline is not None:
            self.pipeline.set_state(Gst.State.NULL)
        self.pipeline = None
        self.appsink = None
        self._log("Stopped")

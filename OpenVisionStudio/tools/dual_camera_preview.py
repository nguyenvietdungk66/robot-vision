"""Diagnostic preview for the Image_Acquisition runtime node."""
from __future__ import annotations

import cv2
import numpy as np
from nodes.Image_Acquisition import ImageAcquisitionNode


def main() -> None:
    node = ImageAcquisitionNode()
    try:
        node.start()
        print("Dual-camera preview started. Press Q to quit.", flush=True)
        while True:
            outputs = node.process()
            for key, title in (("camera_0", "Camera 0"), ("camera_1", "Camera 1")):
                frame_obj = outputs[key]
                if frame_obj is None:
                    canvas = np.zeros((720, 1280, 3), dtype=np.uint8)
                    cv2.putText(canvas, "WAITING FOR CAMERA", (300, 360),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                else:
                    canvas = frame_obj.image
                    status = node.get_status()[key]
                    cv2.putText(canvas, f"FPS: {status.fps:.1f}", (20, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow(title, canvas)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        node.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

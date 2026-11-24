import cv2


def apply(image, kernel_size: int = 5, sigma: float = 0.0):
    kernel_size = max(1, int(kernel_size))
    if kernel_size % 2 == 0:
        kernel_size += 1
    return cv2.GaussianBlur(image, (kernel_size, kernel_size), float(sigma))

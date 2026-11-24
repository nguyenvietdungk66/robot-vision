import cv2


def apply(image, diameter: int = 9, sigma_color: float = 75.0, sigma_space: float = 75.0):
    return cv2.bilateralFilter(image, int(diameter), float(sigma_color), float(sigma_space))
